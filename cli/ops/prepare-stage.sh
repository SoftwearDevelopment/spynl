#!/bin/bash

# * make a venv with spynl installed
# * create repostate.txt if needed [$6 == '--mkrepostate']

REPOS=$1
if [ "$REPOS" == "" ]; then
    echo "REPOS NOT GIVEN. EXITING ..."
    exit 2
fi
REVISION=$2
if [ "$REVISION" == "" ]; then
    echo "REVISION NOT GIVEN FOR REPO $REPO. EXITING ..."
    exit 2
fi
FBREVISION=$3
if [[ "$FBREVISION" == "" ]]; then
    echo "FALLBACK REVISION NOT GIVEN. EXITING ..."
    exit 2
fi
SPYNLREVISION=$4
if [[ "$SPYNLREVISION" == "" ]]; then
    echo "SPYNL REVISION NOT GIVEN. EXITING ..."
    exit 2
fi
CONFIG_REPO=$5
if [[ "$CONFIG_REPO" == "" ]]; then
    echo "CONFIG REPO NOT GIVEN. EXITING ..."
    exit 2
fi

pip3 install virtualenv
virtualenv-3.5 venv
source venv/bin/activate

pip3 install invoke==0.14.0
pip3 install --upgrade setuptools

pip install -e hg+ssh://hg@bitbucket.org/spynl/spynl@${REVISION}#egg=spynl
spynl dev.install --repos spynl --revision $REVISION --fallbackrevision $FBREVISION
spynl dev.translations --repos spynl

if [ "$6" == "--mkrepostate" ]; then
    spynl ops.tag_repo_states --repos ${REPOS} --revision ${REVISION} --fallbackrevision ${FBREVISION} --revertchanges
fi
