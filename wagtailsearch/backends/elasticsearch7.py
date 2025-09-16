from collections import OrderedDict
from copy import deepcopy
from urllib.parse import urlparse

from django.utils.crypto import get_random_string
from elasticsearch import VERSION as ELASTICSEARCH_VERSION
from elasticsearch import Elasticsearch
from elasticsearch import NotFoundError as ElasticsearchNotFoundError
from elasticsearch.helpers import bulk

from wagtailsearch.backends.base import (
    BaseSearchBackend,
    BaseSearchResults,
    FilterFieldError,
    get_model_root,
)
from wagtailsearch.backends.elasticsearch_common import (
    BaseElasticsearchIndex,
    BaseElasticsearchMapping,
    BaseElasticsearchSearchQueryCompiler,
    Field,
)
from wagtailsearch.index import class_is_indexed
from wagtailsearch.query import MatchAll, PlainText
from wagtailsearch.utils import deep_update


class Elasticsearch7Mapping(BaseElasticsearchMapping):
    pass


class Elasticsearch70Index(BaseElasticsearchIndex):
    """Index class implementing the Elasticsearch <7.15 API"""

    def put(self):
        self.connection.indices.create(self.name, self.backend.settings)

    def delete(self):
        try:
            self.connection.indices.delete(self.name)
        except self.NotFoundError:
            pass

    def refresh(self):
        self.connection.indices.refresh(self.name)

    def add_model(self, model):
        # Get mapping
        mapping = self.mapping_class(model)

        # Put mapping
        self.connection.indices.put_mapping(index=self.name, body=mapping.get_mapping())

    def add_item(self, item):
        # Make sure the object can be indexed
        if not class_is_indexed(item.__class__):
            return
        # Get mapping
        mapping = self.mapping_class(item.__class__)

        # Add document to index
        self.connection.index(
            self.name, mapping.get_document(item), id=mapping.get_document_id(item)
        )

    def _run_bulk(self, actions):
        bulk(self.connection, actions, index=self.name)


class Elasticsearch715Index(BaseElasticsearchIndex):
    """Index class overriding select methods to implement the Elasticsearch >=7.15 API"""

    def put(self):
        self.connection.indices.create(index=self.name, **self.backend.settings)

    def delete(self):
        try:
            self.connection.indices.delete(index=self.name)
        except self.NotFoundError:
            pass

    def refresh(self):
        self.connection.indices.refresh(index=self.name)

    def add_model(self, model):
        # Get mapping
        mapping = self.mapping_class(model)

        # Put mapping
        self.connection.indices.put_mapping(index=self.name, body=mapping.get_mapping())

    def add_item(self, item):
        # Make sure the object can be indexed
        if not class_is_indexed(item.__class__):
            return

        # Get mapping
        mapping = self.mapping_class(item.__class__)

        # Add document to index
        self.connection.index(
            index=self.name,
            document=mapping.get_document(item),
            id=mapping.get_document_id(item),
        )

    def _run_bulk(self, actions):
        bulk(self.connection, actions, index=self.name)


class Elasticsearch7SearchQueryCompiler(BaseElasticsearchSearchQueryCompiler):
    mapping_class = Elasticsearch7Mapping


class Elasticsearch70SearchResults(BaseSearchResults):
    """Search results class implementing the Elasticsearch <7.15 API"""

    fields_param_name = "stored_fields"
    supports_facet = True

    def facet(self, field_name):
        # Get field
        field = self.query_compiler._get_filterable_field(field_name)
        if field is None:
            raise FilterFieldError(
                'Cannot facet search results with field "'
                + field_name
                + "\". Please add index.FilterField('"
                + field_name
                + "') to "
                + self.query_compiler.queryset.model.__name__
                + ".search_fields.",
                field_name=field_name,
            )

        # Build body
        body = self._get_es_body()
        column_name = self.query_compiler.mapping.get_field_column_name(field)

        body["aggregations"] = {
            field_name: {
                "terms": {
                    "field": column_name,
                    "missing": 0,
                }
            }
        }

        # Send to Elasticsearch
        response = self._backend_do_search(
            body,
            index=self.backend.get_index_for_model(
                self.query_compiler.queryset.model
            ).name,
            size=0,
        )

        return OrderedDict(
            [
                (bucket["key"] if bucket["key"] != 0 else None, bucket["doc_count"])
                for bucket in response["aggregations"][field_name]["buckets"]
            ]
        )

    def _get_es_body(self, for_count=False):
        body = {"query": self.query_compiler.get_query()}

        if not for_count:
            sort = self.query_compiler.get_sort()

            if sort is not None:
                body["sort"] = sort

        return body

    def _get_results_from_hits(self, hits):
        """
        Yields Django model instances from a page of hits returned by Elasticsearch
        """
        # Get pks from results
        pks = [hit["fields"]["pk"][0] for hit in hits]
        scores = {str(hit["fields"]["pk"][0]): hit["_score"] for hit in hits}

        # Initialise results dictionary
        results = {str(pk): None for pk in pks}

        # Find objects in database and add them to dict
        for obj in self.query_compiler.queryset.filter(pk__in=pks):
            results[str(obj.pk)] = obj

            if self._score_field:
                setattr(obj, self._score_field, scores.get(str(obj.pk)))

        # Yield results in order given by Elasticsearch
        for pk in pks:
            result = results[str(pk)]
            if result:
                yield result

    def _backend_do_search(self, body, **kwargs):
        # Send the search query to the backend.
        return self.backend.connection.search(body=body, **kwargs)

    def _do_search(self):
        PAGE_SIZE = 100

        if self.stop is not None:
            limit = self.stop - self.start
        else:
            limit = None

        use_scroll = limit is None or limit > PAGE_SIZE

        body = self._get_es_body()
        params = {
            "index": self.backend.get_index_for_model(
                self.query_compiler.queryset.model
            ).name,
            "_source": False,
            self.fields_param_name: "pk",
        }

        if use_scroll:
            params.update(
                {
                    "scroll": "2m",
                    "size": PAGE_SIZE,
                }
            )

            # The scroll API doesn't support offset, manually skip the first results
            skip = self.start

            # Send to Elasticsearch
            page = self._backend_do_search(body, **params)

            while True:
                hits = page["hits"]["hits"]

                if len(hits) == 0:
                    break

                # Get results
                if skip < len(hits):
                    for result in self._get_results_from_hits(hits):
                        if limit is not None and limit == 0:
                            break

                        if skip == 0:
                            yield result

                            if limit is not None:
                                limit -= 1
                        else:
                            skip -= 1

                    if limit is not None and limit == 0:
                        break
                else:
                    # Skip whole page
                    skip -= len(hits)

                # Fetch next page of results
                if "_scroll_id" not in page:
                    break

                page = self.backend.connection.scroll(
                    scroll_id=page["_scroll_id"], scroll="2m"
                )

            # Clear the scroll
            if "_scroll_id" in page:
                self.backend.connection.clear_scroll(scroll_id=page["_scroll_id"])
        else:
            params.update(
                {
                    "from_": self.start,
                    "size": limit or PAGE_SIZE,
                }
            )

            # Send to Elasticsearch
            hits = self._backend_do_search(body, **params)["hits"]["hits"]

            # Get results
            for result in self._get_results_from_hits(hits):
                yield result

    def _do_count(self):
        # Get count
        hit_count = self.backend.connection.count(
            index=self.backend.get_index_for_model(
                self.query_compiler.queryset.model
            ).name,
            body=self._get_es_body(for_count=True),
        )["count"]

        # Add limits
        hit_count -= self.start
        if self.stop is not None:
            hit_count = min(hit_count, self.stop - self.start)

        return max(hit_count, 0)


class Elasticsearch715SearchResults(Elasticsearch70SearchResults):
    """Search results class overriding the search method to implement the Elasticsearch >=7.15 API"""

    def _backend_do_search(self, body, **kwargs):
        # As of Elasticsearch 7.15, the 'body' parameter is deprecated; instead, the top-level
        # keys of the body dict are now kwargs in their own right
        return self.backend.connection.search(**body, **kwargs)


class ElasticsearchAutocompleteQueryCompilerImpl:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Convert field names into index column names
        # Note: this overrides Elasticsearch7SearchQueryCompiler by using autocomplete fields instead of searchable fields
        if self.fields:
            fields = []
            autocomplete_fields = {
                f.field_name: f
                for f in self.queryset.model.get_autocomplete_search_fields()
            }
            for field_name in self.fields:
                if field_name in autocomplete_fields:
                    field_name = self.mapping.get_field_column_name(
                        autocomplete_fields[field_name]
                    )

                fields.append(field_name)

            self.remapped_fields = fields
        else:
            self.remapped_fields = None

    def get_inner_query(self):
        fields = self.remapped_fields or [self.mapping.edgengrams_field_name]
        fields = [Field(field) for field in fields]
        if len(fields) == 0:
            # No fields. Return a query that'll match nothing
            return {"bool": {"mustNot": {"match_all": {}}}}
        elif isinstance(self.query, PlainText):
            return self._compile_plaintext_query(self.query, fields)
        elif isinstance(self.query, MatchAll):
            return {"match_all": {}}
        else:
            raise NotImplementedError(
                f"`{self.query.__class__.__name__}` is not supported for autocomplete queries."
            )


class Elasticsearch7AutocompleteQueryCompiler(
    ElasticsearchAutocompleteQueryCompilerImpl, Elasticsearch7SearchQueryCompiler
):
    pass


class ElasticsearchIndexRebuilder:
    def __init__(self, index):
        self.index = index

    def reset_index(self):
        self.index.reset()

    def start(self):
        # Reset the index
        self.reset_index()

        return self.index

    def finish(self):
        self.index.refresh()


class ElasticsearchAtomicIndexRebuilder(ElasticsearchIndexRebuilder):
    def __init__(self, index):
        self.alias = index
        self.index = index.backend.index_class(
            index.backend, self.alias.name + "_" + get_random_string(7).lower()
        )

    def reset_index(self):
        # Delete old index using the alias
        # This should delete both the alias and the index
        self.alias.delete()

        # Create new index
        self.index.put()

        # Create a new alias
        self.index.put_alias(self.alias.name)

    def start(self):
        # Create the new index
        self.index.put()

        return self.index

    def finish(self):
        self.index.refresh()

        if self.alias.is_alias():
            # Update existing alias, then delete the old index

            # Find index that alias currently points to, we'll delete it after
            # updating the alias
            old_index = self.alias.aliased_indices()

            # Update alias to point to new index
            self.index.put_alias(self.alias.name)

            # Delete old index
            # aliased_indices() can return multiple indices. Delete them all
            for index in old_index:
                if index.name != self.index.name:
                    index.delete()

        else:
            # self.alias doesn't currently refer to an alias in Elasticsearch.
            # This means that either nothing exists in ES with that name or
            # there is currently an index with the that name

            # Run delete on the alias, just in case it is currently an index.
            # This happens on the first rebuild after switching ATOMIC_REBUILD on
            self.alias.delete()

            # Create the alias
            self.index.put_alias(self.alias.name)


class Elasticsearch70SearchBackend(BaseSearchBackend):
    mapping_class = Elasticsearch7Mapping
    index_class = Elasticsearch70Index
    query_compiler_class = Elasticsearch7SearchQueryCompiler
    autocomplete_query_compiler_class = Elasticsearch7AutocompleteQueryCompiler
    results_class = Elasticsearch70SearchResults
    basic_rebuilder_class = ElasticsearchIndexRebuilder
    atomic_rebuilder_class = ElasticsearchAtomicIndexRebuilder
    connection_class = Elasticsearch
    NotFoundError = ElasticsearchNotFoundError
    catch_indexing_errors = True
    timeout_kwarg_name = "timeout"
    default_index_name = "wagtail"

    settings = {
        "settings": {
            "analysis": {
                "analyzer": {
                    "ngram_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["asciifolding", "lowercase", "ngram"],
                    },
                    "edgengram_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["asciifolding", "lowercase", "edgengram"],
                    },
                },
                "tokenizer": {
                    "ngram_tokenizer": {
                        "type": "ngram",
                        "min_gram": 3,
                        "max_gram": 15,
                    },
                    "edgengram_tokenizer": {
                        "type": "edge_ngram",
                        "min_gram": 2,
                        "max_gram": 15,
                        "side": "front",
                    },
                },
                "filter": {
                    "ngram": {"type": "ngram", "min_gram": 3, "max_gram": 15},
                    "edgengram": {"type": "edge_ngram", "min_gram": 1, "max_gram": 15},
                },
            },
            "index": {
                "max_ngram_diff": 12,
            },
        }
    }

    def _get_host_config_from_url(self, url):
        """Given a parsed URL, return the host configuration to be added to self.hosts"""
        use_ssl = url.scheme == "https"
        port = url.port or (443 if use_ssl else 80)

        http_auth = None
        if url.username is not None and url.password is not None:
            http_auth = (url.username, url.password)

        return {
            "host": url.hostname,
            "port": port,
            "url_prefix": url.path,
            "use_ssl": use_ssl,
            "verify_certs": use_ssl,
            "http_auth": http_auth,
        }

    def _get_options_from_host_urls(self, urls):
        """Given a list of parsed URLs, return a dict of additional options to be passed into the
        Elasticsearch constructor; necessary for options that aren't valid as part of the 'hosts' config
        """
        return {}

    def __init__(self, params):
        super().__init__(params)

        # Get settings
        self.hosts = params.pop("HOSTS", None)
        self.timeout = params.pop("TIMEOUT", 10)

        if params.pop("ATOMIC_REBUILD", False):
            self.rebuilder_class = self.atomic_rebuilder_class
        else:
            self.rebuilder_class = self.basic_rebuilder_class

        self.settings = deepcopy(
            self.settings
        )  # Make the class settings attribute as instance settings attribute
        self.settings = deep_update(self.settings, params.pop("INDEX_SETTINGS", {}))

        # Get Elasticsearch interface
        # Any remaining params are passed into the Elasticsearch constructor
        options = params.pop("OPTIONS", {})

        # If HOSTS is not set, convert URLS setting to HOSTS
        if self.hosts is None:
            es_urls = params.pop("URLS", ["http://localhost:9200"])
            # if es_urls is not a list, convert it to a list
            if isinstance(es_urls, str):
                es_urls = [es_urls]

            parsed_urls = [urlparse(url) for url in es_urls]

            self.hosts = [self._get_host_config_from_url(url) for url in parsed_urls]
            options.update(self._get_options_from_host_urls(parsed_urls))

        options[self.timeout_kwarg_name] = self.timeout

        self.connection = self.connection_class(hosts=self.hosts, **options)

        # Keep a lookup of previously instantiated instance objects, so that successive calls to get_index_for_model return the same instance
        self._indexes_by_name = {}

    def get_index_for_model(self, model):
        # Split models up into separate indices based on their root model.
        # For example, all page-derived models get put together in one index,
        # while images and documents each have their own index.
        root_model = get_model_root(model)
        index_name = f"{self.index_name}__{root_model._meta.app_label.lower()}_{root_model.__name__.lower()}"
        if index_name not in self._indexes_by_name:
            self._indexes_by_name[index_name] = self.index_class(self, index_name)

        return self._indexes_by_name[index_name]


class Elasticsearch715SearchBackend(Elasticsearch70SearchBackend):
    index_class = Elasticsearch715Index
    results_class = Elasticsearch715SearchResults


if ELASTICSEARCH_VERSION >= (7, 15):
    SearchBackend = Elasticsearch715SearchBackend
    Elasticsearch7SearchBackend = Elasticsearch715SearchBackend
else:
    SearchBackend = Elasticsearch70SearchBackend
    Elasticsearch7SearchBackend = Elasticsearch70SearchBackend
