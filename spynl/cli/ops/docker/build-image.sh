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

if [ ! -f "repo-state.txt" ]; then
    echo "[build_spynl_docker_image] No file repo-state.txt found. Exiting ..."
    exit
fi

git checkout -- setup.sh

# --- check for Deployment Key (needed within image for building)
if [ ! -f ~/.ssh/deployment-key ]; then
    echo "[build_spynl_docker_image] I need a valid ssh key to clone code (I look for '~/.ssh/deployment-key') to proceed!"
    exit
else
    echo "[build_spynl_docker_image] Deployment key found."
    cp ~/.ssh/deployment-key .
fi

# --- Loop over repos, get the commit ID and set it in setup.sh
cp setup.sh setup.sh.bckp
INSTALL_CMD=""
readarray REPOSTATE < repo-state.txt  # needs bash4
for line in "${REPOSTATE[@]}"; do
    SCM_URL=`echo $line | cut -d ' ' -sf 1`
    COMMITID=`echo $line | cut -d ' ' -sf 2`
    echo "[build_spynl_docker_image] For repo $SCM_URL, I found commit ID $COMMITID."
    if [ "$SCM_URL" == "https://github.com/SoftwearDevelopment/spynl.git" ]; then
        sed -e "s|spynl.git#egg=spynl|spynl.git@"$COMMITID"#egg=spynl|" setup.sh > setup.sh.tmp && mv setup.sh.tmp setup.sh
        cp ../../../main/version.py tmp_version.py  # then we don't need to import spynl dependencies
        SPYNL_VERSION=$(python3 -c 'from tmp_version import __version__; print(__version__)')
        rm tmp_version.py
    else
        INSTALL_CMD="$INSTALL_CMD\nspynl dev.install --scm-url $SCM_URL --revision $COMMITID"
    fi
done
echo "[build_spynl_docker_image] INSTALL CMD: $INSTALL_CMD"
sed -e "s|#spynl dev.install --scm-url <some-url>|$INSTALL_CMD|" setup.sh > setup.sh.tmp && mv setup.sh.tmp setup.sh


# --- insert build number to spynl's .ini (via setup.sh)
echo "Inserting $BUILDNR as BUILDNR var in setup.sh ..."
sed -e 's#^\(BUILDNR=\).*$#\1'$BUILDNR'#' setup.sh > setup.sh.tmp && mv setup.sh.tmp setup.sh

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
