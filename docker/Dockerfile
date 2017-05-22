FROM ubuntu:16.04

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libgmp3-dev \
    python3.5 \
    python3-dev \
    python3-pip \
    supervisor \
    locales \
    git

RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

RUN mkdir /logs
RUN mkdir /spynl
WORKDIR /spynl

ADD requirements.txt requirements.txt
RUN pip3 install --upgrade pip setuptools && \
    pip3 install -r requirements.txt

COPY production.ini.template production.ini.template
COPY supervisord.conf supervisord.conf
COPY run run.sh

ARG BUILD_TIME
ENV SPYNL_BUILD_TIME=${BUILD_TIME:-"Missing time"}

ARG BUILD_NR
ENV SPYNL_BUILD_NR=${BUILD_NR:-"Missing buildnr"}

ARG VERSION=master
RUN pip3 install git+https://github.com/SoftwearDevelopment/spynl@${VERSION}#egg=spynl[server] && \
    spynl dev translate

EXPOSE 6543
CMD ["./run.sh"]
