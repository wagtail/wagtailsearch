#!/usr/bin/env bash

PROJECT_NAME=wagtailsearch

: ${PROJECT_DIR:=/vagrant}
: ${DEV_USER:=vagrant}

VIRTUALENV_DIR=/home/$DEV_USER/.virtualenvs/$PROJECT_NAME
PYTHON=$VIRTUALENV_DIR/bin/python
PIP=$VIRTUALENV_DIR/bin/pip
BASHRC=/home/$DEV_USER/.bashrc

apt update -y
apt install -y vim git curl gettext build-essential ca-certificates gnupg pkg-config
apt install -y python3 python3-dev python3-pip python3-venv python-is-python3
apt install -y postgresql libpq-dev
apt install -y mysql-server libmysqlclient-dev

# Create pgsql superuser
PG_USER_EXISTS=$(
    su - postgres -c \
    "psql postgres -tAc \"SELECT 'yes' FROM pg_roles WHERE rolname='vagrant' LIMIT 1\""
)

if [[ "$PG_USER_EXISTS" != "yes" ]];
then
    su - postgres -c "createuser -s vagrant"
fi

# Create mysql superuser
mysql -e "CREATE USER 'vagrant'@'localhost' IDENTIFIED BY 'vagrant'"
mysql -e "GRANT ALL ON test_wagtailsearch.* TO 'vagrant'@'localhost'"

su - $DEV_USER -c "python -m venv $VIRTUALENV_DIR"
su - $DEV_USER -c "$PIP install psycopg mysqlclient"
su - $DEV_USER -c "$PIP install -e $PROJECT_DIR[testing]"

BASHRC_LINE_VENV="source $VIRTUALENV_DIR/bin/activate"
cat $BASHRC | grep -v "^$BASHRC_LINE_VENV" > "${BASHRC}.tmp" && mv ${BASHRC}.tmp $BASHRC
echo $BASHRC_LINE_VENV >> $BASHRC


# Elasticsearch
ES_VERSION=8.19.3
ES_DOWNLOAD_FILE=elasticsearch-$ES_VERSION-linux-`uname -p`.tar.gz
ES_DOWNLOAD_URL=https://artifacts.elastic.co/downloads/elasticsearch/$ES_DOWNLOAD_FILE
ES_ROOT=/home/$DEV_USER/elasticsearch-$ES_VERSION

su - $DEV_USER -c "wget $ES_DOWNLOAD_URL -P /home/$DEV_USER"
su - $DEV_USER -c "cd /home/$DEV_USER && tar xzf $ES_DOWNLOAD_FILE"
su - $DEV_USER -c "$ES_ROOT/bin/elasticsearch-users useradd wagtail -p wagtail -r superuser"
su - $DEV_USER -c "$PIP install 'elasticsearch>=8.0.0,<9.0.0'"
