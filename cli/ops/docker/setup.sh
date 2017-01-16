#!/bin/bash


# setup SSH authentication for getting the code from bitbucket
mkdir -p /root/.ssh
mv /root/deployment-key /root/.ssh/deployment-key
chmod -R 700 /root/.ssh/deployment-key
touch /root/.ssh/known_hosts
ssh -o StrictHostKeyChecking=no hg@bitbucket.org uptime
eval "$(ssh-agent)"
ssh-add /root/.ssh/deployment-key

# make sure we never install recommended packages
cat > /etc/apt/apt.conf.d/01norecommend << EOF
APT::Install-Recommends "0";
APT::Install-Suggests "0";
EOF

# Make a Python3 virtualenv
pip3 install virtualenv
virtualenv --python=python3.5 venv
source venv/bin/activate

# install spynl.main
pip install -e hg+ssh://hg@bitbucket.org/spynl/spynl#egg=spynl

spynl dev.translations --repos spynl
spynl dev.get_schemas --version SCHEMA_VERSION 

# record build time and build number
CURRTIME=`date -u "+%Y-%m-%dT%H:%M:%S+0000"`
BUILDNR=PLACEHOLDER
sed -e 's#^\(spynl.build_time =\).*$#\1 '$CURRTIME'#' /production.ini > /production.ini.tmp && mv /production.ini.tmp /production.ini
sed -e 's#^\(spynl.build_number =\).*$#\1 '$BUILDNR'#' /production.ini > /production.ini.tmp && mv /production.ini.tmp /production.ini


# This is how to install further repos
# build_image.sh can also replace this with specific install-repo calls
#spynl dev.install --repos spynl.something --revision default 

# install gunicorn & paste 
pip install gunicorn
pip install paste pastedeploy

# TODO make a user who runs Spynl instead of root?
#useradd -m spynluser
#echo "spynluser:spynlpass" | chpasswd
#sudo chown -R spynluser /var/www/myapp
echo "root:rootpass" | chpasswd

# no need to keep this key in image layers from here on (TODO: still remains in lower layers!)
rm /root/.ssh/deployment-key
