FROM debian:stable

MAINTAINER Nicolas Le Manchet <nicolas@lemanchet.fr>

# Build a deb package for sauna
# Heavily inspired by
# https://www.spkdev.net/2015/03/03/quickly-build-a-debian-package-with-docker.html

ENV DEBIAN_FRONTEND noninteractive
ENV DEBIAN_PRIORITY critical
ENV DEBCONF_NOWARNINGS yes

RUN apt-get update && apt-get -y upgrade
RUN apt-get -y --no-install-recommends install devscripts equivs

WORKDIR /root
ADD . /root
RUN mk-build-deps -t "apt-get -y --no-install-recommends" -i "debian/control"
RUN dpkg-buildpackage -b

VOLUME /output

CMD cp ../*.deb /output
