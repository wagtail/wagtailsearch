from wagtailsearch.backends import get_search_backend


class SearchableQuerySetMixin:
    """Extends a QuerySet class with search functionality."""

    def search(
        self,
        query,
        fields=None,
        operator=None,
        order_by_relevance=True,
        order=None,
        backend="default",
    ):
        """
        This runs a search query on all the items in the QuerySet
        """
        search_backend = get_search_backend(backend)
        queryset = self
        if order:
            queryset = queryset.order_by(order)
            order_by_relevance = False

        return search_backend.search(
            query,
            queryset,
            fields=fields,
            operator=operator,
            order_by_relevance=order_by_relevance,
        )

    def autocomplete(
        self,
        query,
        fields=None,
        operator=None,
        order_by_relevance=True,
        order=None,
        backend="default",
    ):
        """
        This runs an autocomplete query on all the items in the QuerySet
        """
        search_backend = get_search_backend(backend)
        queryset = self
        if order:
            queryset = queryset.order_by(order)
            order_by_relevance = False

        return search_backend.autocomplete(
            query,
            queryset,
            fields=fields,
            operator=operator,
            order_by_relevance=order_by_relevance,
        )
