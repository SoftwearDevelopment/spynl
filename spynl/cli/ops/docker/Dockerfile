FROM ubuntu:16.04
MAINTAINER Nicolas Höning <nicolas@softwear.nl>

RUN apt-get update -qq && apt-get install -y --no-install-recommends python3.5 python3-pip python-pip supervisor libffi-dev libssl-dev sudo && apt-get autoremove -y && apt-get clean -y && mkdir /logs

COPY supervisord.conf /etc/supervisord.conf
COPY production.ini /production.ini
COPY deployment-key /root/deployment-key
COPY setup.sh setup.sh
RUN apt-get update -q && apt-get install -y git mercurial && ./setup.sh && apt-get autoremove -y && apt-get clean -y
COPY run.sh run.sh

EXPOSE 6543

CMD ["/run.sh"]
