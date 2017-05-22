#!/bin/bash

# This script adapts /production.ini from environmental variables,
# potentially configures NewRelic and starts gunicorn via supervisord.

printf "======================= \nRUNNING SPYNL APPLICATION ...\n========================= \n\n" >> /logs/spynl.log

# this should be pre-filled by a script
SPYNL_DEV_DOMAIN=

source /venv/bin/activate

# let repos have their say before running
spynl ops.prepare_docker_run 1>> /logs/spynl.log 2>> /logs/spynl.log

# Spynl number of workers
if [[ "$WEB_CONCURRENCY" == "" ]]; then
    WEB_CONCURRENCY='2'
fi
sed -e 's#^\(workers =\).*$#\1 '$WEB_CONCURRENCY'#' /production.ini > /production.ini.tmp && mv /production.ini.tmp /production.ini

# set SPYNL_FUNCTION in production.ini
sed -e 's#^\(spynl.ops.function =\).*$#\1 '$SPYNL_FUNCTION'#' /production.ini > /production.ini.tmp && mv /production.ini.tmp /production.ini

# should we pretty-print?
if [[ "$SPYNL_ENVIRONMENT" == "" || "$SPYNL_ENVIRONMENT" == "test" ]]; then
    sed -e 's#^\(spynl.pretty =\).*$#\1 1#' /production.ini > /production.ini.tmp && mv /production.ini.tmp /production.ini
fi

# adapt spynl.domain
if [[ "$SPYNL_ENVIRONMENT" != "" ]]; then
    if [[ "$SPYNL_ENVIRONMENT" != "production" ]]; then
        # add SPYNL_ENVIRONMENT before existing spynl.domain setting
        sed -e "s/^\(spynl.domain =\)\([[:space:]]\)\(.*$\)/\1 $SPYNL_ENVIRONMENT.\3/" /production.ini > /production.ini.tmp && mv /production.ini.tmp /production.ini
    fi
else
    # use SPYNL_DEV_DOMAIN for spynl.domain
    sed -e 's#^\(spynl.domain =\).*$#\1 '$SPYNL_DEV_DOMAIN'#' /production.ini > /production.ini.tmp && mv /production.ini.tmp /production.ini
    SPYNL_ENVIRONMENT='UnknownEnvironment'
fi

# set SPYNL_ENVIRONMENT in production.ini
sed -e 's#^\(spynl.ops.environment =\).*$#\1 '$SPYNL_ENVIRONMENT'#' /production.ini > /production.ini.tmp && mv /production.ini.tmp /production.ini

# this can be handy when looking at /logs/spynl.log from outside a container
printf "======================= \nOUTPUTTING production.ini ...\n========================= \n\n" >> /logs/spynl.log
cat production.ini >> /logs/spynl.log
printf "======================= \nEND OF production.ini ...\n========================= \n\n" >> /logs/spynl.log

if [[ "$NEWRELIC" == "true" ]]; then
    pip install raven
    pip install newrelic
    # get NewRelic key from production.ini
    NEWRELIC_KEY=""
    while read line; do
    if [[ "$line" =~ ^spynl.newrelic_key.* ]]; then
        NEWRELIC_KEY=`echo $line | cut -d'=' -f 2`
    fi
    done < /production.ini
    if [ "$NEWRELIC_KEY" == "" ]; then
        echo "NEWRELIC is set to true but no spynl.newrelic_key found! Exiting ..."
        exit 2
    fi
    newrelic-admin generate-config $NEWRELIC_KEY /newrelic.ini
    #NEW_RELIC_CONFIG_FILE=/newrelic.ini
    sed -e 's#app_name = Python Application#app_name = SPYNL ['$SPYNL_ENVIRONMENT'-'$SPYNL_FUNCTION']#' /newrelic.ini > /newrelic.ini.tmp && mv /newrelic.ini.tmp /newrelic.ini
    COMMAND="command=/venv/bin/newrelic-admin run-program /venv/bin/gunicorn --paste /production.ini --error-logfile /logs/gerr.log"
else
    COMMAND="command=/venv/bin/gunicorn --paste /production.ini --error-logfile /logs/gerr.log"
fi

# configure the command supervisord should run
echo "$COMMAND" >> /etc/supervisord.conf

# Start Spynl via supervisor
supervisord --nodaemon -c /etc/supervisord.conf
