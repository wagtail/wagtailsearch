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


# Elasticsearch 7
ES7_VERSION=7.17.29
ES7_DOWNLOAD_FILE=elasticsearch-$ES7_VERSION-linux-`uname -p`.tar.gz
ES7_DOWNLOAD_URL=https://artifacts.elastic.co/downloads/elasticsearch/$ES7_DOWNLOAD_FILE
ES7_ROOT=/home/$DEV_USER/elasticsearch-$ES7_VERSION
ES7_VIRTUALENV_DIR=/home/$DEV_USER/.virtualenvs/wagtailsearches7
ES7_PIP=$ES7_VIRTUALENV_DIR/bin/pip

su - $DEV_USER -c "wget $ES7_DOWNLOAD_URL -P /home/$DEV_USER"
su - $DEV_USER -c "cd /home/$DEV_USER && tar xzf $ES7_DOWNLOAD_FILE"
su - $DEV_USER -c "$ES7_ROOT/bin/elasticsearch-users useradd wagtail -p wagtail -r superuser"

su - $DEV_USER -c "python -m venv $ES7_VIRTUALENV_DIR"
su - $DEV_USER -c "$ES7_PIP install 'elasticsearch>=7.0.0,<8.0.0'"
su - $DEV_USER -c "$ES7_PIP install -e $PROJECT_DIR[testing]"


# Elasticsearch 8
ES8_VERSION=8.19.3
ES8_DOWNLOAD_FILE=elasticsearch-$ES8_VERSION-linux-`uname -p`.tar.gz
ES8_DOWNLOAD_URL=https://artifacts.elastic.co/downloads/elasticsearch/$ES8_DOWNLOAD_FILE
ES8_ROOT=/home/$DEV_USER/elasticsearch-$ES8_VERSION
ES8_VIRTUALENV_DIR=/home/$DEV_USER/.virtualenvs/wagtailsearches8
ES8_PIP=$ES8_VIRTUALENV_DIR/bin/pip

su - $DEV_USER -c "wget $ES8_DOWNLOAD_URL -P /home/$DEV_USER"
su - $DEV_USER -c "cd /home/$DEV_USER && tar xzf $ES8_DOWNLOAD_FILE"
su - $DEV_USER -c "$ES8_ROOT/bin/elasticsearch-users useradd wagtail -p wagtail -r superuser"

su - $DEV_USER -c "python -m venv $ES8_VIRTUALENV_DIR"
su - $DEV_USER -c "$ES8_PIP install 'elasticsearch>=8.0.0,<9.0.0'"
su - $DEV_USER -c "$ES8_PIP install -e $PROJECT_DIR[testing]"
