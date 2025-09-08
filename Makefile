coverage:
	coverage erase
	~/.virtualenvs/wagtailsearch/bin/coverage run -p testmanage.py test
	DATABASE_URL="postgres:///wagtailsearch" ~/.virtualenvs/wagtailsearch/bin/coverage run -p testmanage.py test
	DATABASE_URL="mysql://vagrant:vagrant@localhost/wagtailsearch" ~/.virtualenvs/wagtailsearch/bin/coverage run -p testmanage.py test

	/home/vagrant/elasticsearch-7.17.29/bin/elasticsearch -q &
	sleep 10
	ELASTICSEARCH_URL="http://wagtail:wagtail@localhost:9200" ELASTICSEARCH_VERSION=7 ~/.virtualenvs/wagtailsearches7/bin/coverage run -p testmanage.py test
	killall java

	/home/vagrant/elasticsearch-8.19.3/bin/elasticsearch -q &
	sleep 20
	ELASTICSEARCH_URL="https://wagtail:wagtail@localhost:9200" ELASTICSEARCH_VERSION=8 ELASTICSEARCH_CA_CERTS=~/elasticsearch-8.19.3/config/certs/http_ca.crt ~/.virtualenvs/wagtailsearches8/bin/coverage run -p testmanage.py test
	killall java

	coverage combine
	coverage html
