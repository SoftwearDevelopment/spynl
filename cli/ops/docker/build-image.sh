#!/bin/bash

# * Get the code for the given revision.
# * Build the Spynl Docker image, tag with its __version__ identifier
#
# This script assumes it was started in the docker-image directory.
# The revision identifier needs to be passed in, build number is optional.

BUILDNR=$1
if [ "$BUILDNR" == "" ]; then
  echo "[build_spynl_docker_image] No BUILDNR argument given - using 'UNKNOWN'"
  BUILDNR='UNKNOWN'
fi
echo "[build_spynl_docker_image] Building new SPYNL image for build number $BUILDNR ..."

SPYNL_DEV_DOMAIN=$2
if [ "$SPYNL_DEV_DOMAIN" == "" ]; then
  echo "[build_spynl_docker_image] No SPYNL_DEV_DOMAIN argument given - leaving empty, cookies might not work"
fi

if [ ! -f "repostate.txt" ]; then
    echo "[build_spynl_docker_image] No file repostate.txt found. Exiting ..."
    exit
fi

#echo "[build_spynl_docker_image] Ensure Docker is installed ..."
# TODO: needed? should we include the contents of that script here? Then update first.
#../ensure_docker.sh

hg --q revert setup.sh

# --- check for Bitbucket Deployment Key (needed within image for building)
if [ ! -f ~/.ssh/deployment-key ]; then
    echo "[build_spynl_docker_image] I need a valid ssh key to access the softwear account (I look for '~/.ssh/deployment-key') to proceed!"
    exit
else
    echo "[build_spynl_docker_image] Deployment key found."
    cp ~/.ssh/deployment-key .
fi

# --- Loop over repos, get the commit ID and set it in setup.sh
cp setup.sh setup.sh.bckp
INSTALL_CMD=""
readarray REPOSTATE < repostate.txt  # needs bash4
for line in "${REPOSTATE[@]}"; do
    REPO=`echo $line | cut -d ' ' -sf 1`
    COMMITID=`echo $line | cut -d ' ' -sf 2`
    echo "[build_spynl_docker_image] For repo $REPO, I found commit ID $COMMITID."
    if [ "$REPO" == "spynl" ]; then
        sed -e "s|pip install -e hg+ssh://hg@bitbucket.org/spynl/spynl#egg=spynl|pip install -e hg+ssh://hg@bitbucket.org/spynl/spynl@$COMMITID#egg=spynl|" setup.sh > setup.sh.tmp && mv setup.sh.tmp setup.sh
        cp $VIRTUAL_ENV/src/spynl/spynl/main/version.py tmp_version.py  # then we don't need to import spynl dependencies
        SPYNL_VERSION=$(python3 -c 'from tmp_version import __version__; print(__version__)')
        rm tmp_version.py
    else
        INSTALL_CMD="$INSTALL_CMD\nspynl dev.install --repos $REPO --revision $COMMITID"
    fi
done
echo "[build_spynl_docker_image] INSTALL CMD: $INSTALL_CMD"
sed -e "s|#spynl dev.install --repos spynl.something --revision default|$INSTALL_CMD|" setup.sh > setup.sh.tmp && mv setup.sh.tmp setup.sh
 

# --- insert build number to spynl's .ini (via setup.sh)
echo "Inserting $BUILDNR as BUILDNR var in setup.sh ..."
sed -e 's#^\(BUILDNR=\).*$#\1'$BUILDNR'#' setup.sh > setup.sh.tmp && mv setup.sh.tmp setup.sh

# --- insert the dev domain in run.sh so dev containers will set cookies correctly
echo "Inserting $SPYNL_DEV_DOMAIN as SPYNL_DEV_DOMAIN var in run.sh ..."
sed -e 's#^\(SPYNL_DEV_DOMAIN=\).*$#\1'$SPYNL_DEV_DOMAIN'#' run.sh > run.sh.tmp && mv run.sh.tmp run.sh

# --- insert schema version from .ini into setup
SVERSION=""
while read line; do
  if [[ "$line" =~ ^spynl.schema.version.* ]]; then
    SVERSION=`echo $line | cut -d'=' -f 2`
  fi
done < production.ini
SVERSION=`echo $SVERSION | sed -e 's/^[[:space:]]*//g' -e 's/[[:space:]]*\$//g'`
echo "[build_spynl_docker_image] Schema version: $SVERSION."
if [[ "$SVERSION" != "" ]]; then
  sed -e "s|SCHEMA_VERSION|$SVERSION|" setup.sh > setup.sh.tmp && mv setup.sh.tmp setup.sh
fi

chmod +x setup.sh
chmod +x run.sh

# --- use Spynl version as tag

rm -rf built.spynl.version
echo $SPYNL_VERSION >> built.spynl.version  # leave this behind for convenience
echo "[build_spynl_docker_image] Building Docker Image spynl:v$SPYNL_VERSION ... (check docker.build.log for logs)"
if [ -e docker.build.log ]; then
    rm docker.build.log
fi

if docker build -t spynl:v$SPYNL_VERSION . > docker.build.log; then
   echo "[build_spynl_docker_image] docker build returned successfully."
   rm deployment-key
   cp setup.sh.bckp setup.sh
else
   echo "[build_spynl_docker_image] docker build returned an error. Exiting ... "
   rm deployment-key
   cp setup.sh.bckp setup.sh
   exit 1
fi

echo "[build_spynl_docker_image] Done."
