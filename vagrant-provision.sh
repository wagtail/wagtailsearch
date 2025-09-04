#!/usr/bin/env bash

PROJECT_NAME=wagtailsearch

: ${PROJECT_DIR:=/vagrant}
: ${DEV_USER:=vagrant}

VIRTUALENV_DIR=/home/$DEV_USER/.virtualenvs/$PROJECT_NAME
PYTHON=$VIRTUALENV_DIR/bin/python
PIP=$VIRTUALENV_DIR/bin/pip
BASHRC=/home/vagrant/.bashrc

apt update -y
apt install -y vim git curl gettext build-essential ca-certificates gnupg
apt install -y python3 python3-dev python3-pip python3-venv python-is-python3
apt install -y postgresql libpq-dev

# Create pgsql superuser
PG_USER_EXISTS=$(
    su - postgres -c \
    "psql postgres -tAc \"SELECT 'yes' FROM pg_roles WHERE rolname='vagrant' LIMIT 1\""
)

if [[ "$PG_USER_EXISTS" != "yes" ]];
then
    su - postgres -c "createuser -s vagrant"
fi

su - $DEV_USER -c "python -m venv $VIRTUALENV_DIR"
su - $DEV_USER -c "$PIP install $PROJECT_DIR[testing]"

BASHRC_LINE_VENV="source $VIRTUALENV_DIR/bin/activate"
cat $BASHRC | grep -v "^$BASHRC_LINE_VENV" > "${BASHRC}.tmp" && mv ${BASHRC}.tmp $BASHRC
echo $BASHRC_LINE_VENV >> $BASHRC
