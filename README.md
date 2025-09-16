# Wagtailsearch

Full-text search for Wagtail

[![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD--3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![PyPI version](https://badge.fury.io/py/wagtailsearch.svg)](https://badge.fury.io/py/wagtailsearch)
[![Search CI](https://github.com/wagtail/wagtailsearch/actions/workflows/test.yml/badge.svg)](https://github.com/wagtail/wagtailsearch/actions/workflows/test.yml)

## Links

- [Documentation](https://github.com/wagtail/wagtailsearch/blob/main/README.md)
- [Changelog](https://github.com/wagtail/wagtailsearch/blob/main/CHANGELOG.md)
- [Contributing](https://github.com/wagtail/wagtailsearch/blob/main/CONTRIBUTING.md)
- [Discussions](https://github.com/wagtail/wagtailsearch/discussions)
- [Security](https://github.com/wagtail/wagtailsearch/security)

## Supported versions

- Python ...
- Django ...
- Wagtail ...

## Installation

- `python -m pip install wagtailsearch`
- ...

## Contributing

### Install

To make changes to this project, first clone this repository:

```sh
git clone https://github.com/wagtail/wagtailsearch.git
cd wagtailsearch
```

With your preferred virtualenv activated, install testing dependencies:

#### Using pip

```sh
python -m pip install --upgrade pip>=21.3
python -m pip install -e '.[testing]' -U
```

#### Using flit

```sh
python -m pip install flit
flit install
```

### pre-commit

Note that this project uses [pre-commit](https://github.com/pre-commit/pre-commit).
It is included in the project testing requirements. To set up locally:

```shell
# go to the project directory
$ cd wagtailsearch
# initialize pre-commit
$ pre-commit install

# Optional, run all checks once for this, then the checks will run only on the changed files
$ git ls-files --others --cached --exclude-standard | xargs pre-commit run --files
```

### How to run tests

A Vagrant provisioning script is provided to install the dependencies for various backends. To install:

```shell
vagrant up
vagrant ssh
```

To test under sqlite:

```shell
source ~/.virtualenvs/wagtailsearch/bin/activate
cd /vagrant/
python testmanage.py test
```

To test under PostgreSQL:

```shell
source ~/.virtualenvs/wagtailsearch/bin/activate
cd /vagrant/
DATABASE_URL="postgres:///wagtailsearch" python ./testmanage.py test
```

To test under MySQL:

```shell
source ~/.virtualenvs/wagtailsearch/bin/activate
cd /vagrant/
DATABASE_URL="mysql://vagrant:vagrant@localhost/wagtailsearch" python ./testmanage.py test
```

To test under Elasticsearch 7:

```shell
/home/vagrant/elasticsearch-7.17.29/bin/elasticsearch
# then in another shell session:
source ~/.virtualenvs/wagtailsearches7/bin/activate
# or to test against the pre-7.15 client library:
#  source ~/.virtualenvs/wagtailsearches70/bin/activate
cd /vagrant/
ELASTICSEARCH_URL="http://wagtail:wagtail@localhost:9200" ELASTICSEARCH_VERSION=7 python testmanage.py test
```

To test under Elasticsearch 8:

```shell
/home/vagrant/elasticsearch-8.19.3/bin/elasticsearch
# then in another shell session:
source ~/.virtualenvs/wagtailsearches8/bin/activate
cd /vagrant/
ELASTICSEARCH_URL="https://wagtail:wagtail@localhost:9200" ELASTICSEARCH_VERSION=8 ELASTICSEARCH_CA_CERTS=~/elasticsearch-8.19.3/config/certs/http_ca.crt python testmanage.py test
```

To test under Opensearch 2:

```shell
/home/vagrant/opensearch-2.19.3/bin/opensearch
# then in another shell session:
source ~/.virtualenvs/wagtailsearchopensearch2/bin/activate
cd /vagrant/
OPENSEARCH_URL="http://localhost:9200" OPENSEARCH_VERSION=2 python testmanage.py test
```

To test under Opensearch 3:

```shell
/home/vagrant/opensearch-3.2.0/bin/opensearch
# then in another shell session:
source ~/.virtualenvs/wagtailsearchopensearch3/bin/activate
cd /vagrant/
OPENSEARCH_URL="http://localhost:9200" OPENSEARCH_VERSION=3 python testmanage.py test
```

To test under all environments and produce a coverage report:
```shell
cd /vagrant/
make coverage
```
