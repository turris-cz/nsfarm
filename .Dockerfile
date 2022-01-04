FROM debian:stable

ENV HOME=/root

RUN \
  apt-get update && \
  apt-get -y upgrade && \
  apt-get -y install --no-install-recommends \
    python3-pip \
    && \
  apt-get clean

RUN \
  pip3 install \
    black \
	isort \
	pylint \
	mypy

COPY ./requirements.txt ./
RUN \
  pip3 install -r requirements.txt && \
  rm -f requirements.txt

CMD [ "bash" ]
