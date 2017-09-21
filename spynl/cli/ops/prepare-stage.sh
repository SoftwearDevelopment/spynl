#!/bin/bash

# * make a venv with spynl and spynl plugins installed
# * create repo-state.txt if needed (pass -m)
# * full usage: ./prepare-stage.sh -u <SCM-URLS> [-r <REVISION>] [-f <FALLBACK-REVISION>] [-m]

SCM_URLS=
REVISION_PARAM=
FBREVISION_PARAM=
MAKE_REPO_STATE=0

while getopts "u:r:f:s:m" opt; do
  case $opt in
    u)
      SCM_URLS=$OPTARG
      ;;
    r)
      if [[ "$OPTARG" != "" ]]; then
        if [[ $OPTARG == -* ]]; then
          ((OPTIND--))
        else
          REVISION_PARAM="--revision $OPTARG"
        fi
      fi
      ;;
    f)
      if [[ "$OPTARG" != "" ]]; then
        if [[ $OPTARG == -* ]]; then
          ((OPTIND--))
        else
          FBREVISION="--fallbackrevision $OPTARG"
        fi
      fi
      ;;
    m)
      MAKE_REPO_STATE=1
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      ;;
  esac
done

if [ "$SCM_URLS" == "" ]; then
    echo "NO SCM URLS GIVEN. EXITING ..."
    exit 2
fi

echo "====== Preparing Stage ======"
echo "SCM_URLS: $SCM_URLS"
echo "REVISION_PARAM: $REVISION_PARAM"
echo "FBREVISION_PARAM: $FBREVISION_PARAM"
echo "MAKE_REPO_STATE: $MAKE_REPO_STATE"
echo "============================="


pip3 install virtualenv
virtualenv-3.5 venv
source venv/bin/activate

pip3 install --upgrade setuptools pip
pip3 install invoke==0.14.0 six

pip install -e .

for url in ${SCM_URLS//,/ }
do
    spynl dev.install --scm-url $url $REVISION_PARAM $FBREVISION_PARAM
done

spynl dev.translate
spynl dev.versions

if [[ "$MAKE_REPO_STATE" == "1" ]]; then
    spynl ops.mk_repo_state
fi
