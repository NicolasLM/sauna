#!/bin/sh

if test -f "sauna.yml"; then
    echo 'Using existing configuration file /app/sauna.yml'
elif test ! -z "$SAUNA_CONFIG"; then
    echo "Using environment var SAUNA_CONFIG"
    echo $SAUNA_CONFIG | base64 -d > sauna.yml
else
    echo "Cannot find configuration file sauna.yml, either:"
    echo "  - use a volume to put configuration in /app/sauna.yml"
    echo "  - use an environment var SAUNA_CONFIG"
    echo ""
    echo "Tip: you can generate the SAUNA_CONFIG data with"
    echo "base64 -w 0 sauna.yml"
    exit 1
fi

echo ""
echo "List of active checks:"
/app/bin/sauna list-active-checks
echo ""
echo ""

export SAUNA_LEVEL=${SAUNA_LEVEL:=warning}

exec /app/bin/sauna --level "$SAUNA_LEVEL"
