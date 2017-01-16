#!/bin/bash

# Creating a new mercurial remote branch in the current repository.
# Pass name of branch as first argument

BRANCH=$1
if [ "$BRANCH" == "" ]; then
  echo "No BRANCH argument given!"
  exit
fi

if hg branches | grep -i '^$BRANCH[[:space:]]' > /tmp/branches.txt; then
    echo "[spynl dev.new_branch] Aborting: branch with the name $BRANCH already exists."
    exit 2
fi

hg branch $BRANCH
hg commit -m "Created new branch: $BRANCH"
hg push --new-branch

# For the record, this is how to get rid of a branch
#hg update $BRANCH
#hg commit --close-branch
