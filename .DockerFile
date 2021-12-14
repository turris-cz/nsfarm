FROM debian:stable

ENV HOME=/root

RUN \
  apt-get update && \
  apt-get -y upgrade && \
  apt-get -y install --no-install-recommends \
    black isort \
    && \
  apt-get clean

CMD [ "bash" ]
