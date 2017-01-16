#!/bin/bash
# Merge the $BRANCH branch into default

if [ "$1" == "" ]; then
    echo "Please provide a source branch name as first parameter."
    exit
fi
SOURCE_BRANCH=$1

if [ "$2" == "" ]; then
    echo "Please provide a target branch name as second parameter."
    exit
fi
TARGET_BRANCH=$2


echo "Merging branch ${SOURCE_BRANCH} into branch ${TARGET_BRANCH} in repo $(pwd) ..."

hg pull
if hg branches | egrep "^${SOURCE_BRANCH}[[:space:]]" > /dev/null; then
    if hg branches | egrep "^${TARGET_BRANCH}[[:space:]]" > /dev/null; then
        hg update ${TARGET_BRANCH}
        hg merge ${SOURCE_BRANCH}
        hg commit -m "merged $SOURCE_BRANCH"
        hg push
    else
        echo "This repo does not have a branch named '${TARGET_BRANCH}'".
    fi
else
    echo "This repo does not have a branch named '${SOURCE_BRANCH}'".
fi

