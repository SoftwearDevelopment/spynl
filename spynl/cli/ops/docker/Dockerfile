FROM ubuntu:16.04
MAINTAINER Nicolas Höning <nicolas@softwear.nl>

RUN apt-get update -qq && apt-get install -y --no-install-recommends mercurial python3.5 python3-pip python-pip supervisor sudo && apt-get autoremove -y && apt-get clean -y && mkdir /logs

COPY supervisord.conf /etc/supervisord.conf
COPY production.ini /production.ini 
COPY deployment-key /root/deployment-key
COPY setup.sh setup.sh
RUN apt-get update -q && apt-get install -y git && ./setup.sh && apt-get remove -y git && apt-get autoremove -y && apt-get clean -y
COPY run.sh run.sh

EXPOSE 6543

ENTRYPOINT ["/run.sh"]
