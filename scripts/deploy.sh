#!/usr/bin/env bash
##
# This script will deploy autoplex into a linux server, or update it if it's already installed
# run as root
#

# CHANGE THIS if you want to install in a different directory
INSTALL_DIR=/opt/autoplex

# CHANGE THIS to anything other than 'y' if
#    you do not want to use infisical for your secret manangement
USE_INFISICAL=y

# CHANGE THIS to anything other than 'y' if you want to use your own redis installation
#    if you do not install redis, make sure to set
INSTALL_LOCAL_REDIS=y

if [ ! -d "${INSTALL_DIR}" ]
then
  mkdir -p "${INSTALL_DIR}"
fi

cd $INSTALL_DIR || exit

# Stop the running service
if systemctl is-active --quiet autoplex
then
  systemctl stop autoplex.service
fi

# Stop the running service
if systemctl is-active --quiet celery
then
  systemctl stop celery.service
fi

# Install or update dependencies
echo "Updating installed packages"
apt update && apt upgrade -y

# install python if it's not installed
if ! dpkg -s python3.11 python3.11-venv python3-pip python-is-python3 > /dev/null 2>&1
then
  echo "Installing Python"
  apt install python3.11 python3.11-venv python3-pip python-is-python3 -y
fi

# install postgresql if it's not installed
if ! dpkg -s postgresql postgresql-contrib > /dev/null 2>&1
then
  echo "Installing PostgreSQL"
  apt install -y postgresql postgresql-contrib
fi

# install redis if the var INSTALL_LOCAL_REDIS is set and it's not already installed
if [ "${INSTALL_LOCAL_REDIS}" == "y" ]
then
  if ! dpkg -s redis > /dev/null 2>&1
  then
    apt install lsb-release curl gpg -y
    curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
    chmod 644 /usr/share/keyrings/redis-archive-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
    apt update
    apt install redis -y
  fi
fi

if ! which uv
then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  source "$HOME/.profile"
else
  uv self update
fi


echo "Fetching / installing web site from github"
# fetch the tgfp code
wget https://github.com/johnsturgeon/autoplex/archive/main.zip
unzip main.zip
rm main.zip

rm -rf ${INSTALL_DIR}/app

# grab the important bits
mv autoplex-main/app ${INSTALL_DIR}/app
mv autoplex-main/pyproject.toml ${INSTALL_DIR}/app
mv autoplex-main/.infisical.json ${INSTALL_DIR}/app
mv autoplex-main/uv.lock ${INSTALL_DIR}/app
mv autoplex-main/helpers/autoplex.service /etc/systemd/system
mv autoplex-main/helpers/celery.service /etc/systemd/system
rm -rf autoplex-main

cd "${INSTALL_DIR}/app" || exit

if [ "${USE_INFISICAL}" == "y" ]
then
  if ! which infisical
  then
    curl -1sLf 'https://dl.cloudsmith.io/public/infisical/infisical-cli/setup.deb.sh' | bash
    apt-get update && apt-get install -y infisical
  fi
  if ! infisical run echo "hi"
  then
    echo "Logging you into infisical"
    infisical login
  fi
  # Create the .env file
  infisical export --format=dotenv-export --env prod > .env
else
  echo "You need to make sure to create a .env"
  echo "------- Please reference the ${INSTALL_DIR}/app/sample.env file -------- "
fi

# now use `uv` to create the environment
uv sync

systemctl daemon-reload
systemctl enable autoplex.service
systemctl enable celery.service
systemctl start autoplex.service
systemctl start celery.service

