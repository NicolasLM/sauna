FROM alpine:edge

MAINTAINER Nicolas Le Manchet <nicolas@lemanchet.fr>

RUN set -x \
    && addgroup -S sauna \
    && adduser -D -S -h /app -G sauna sauna \
    && apk update \
    && apk add python3 py3-psutil py3-yaml py3-docopt py3-requests \
    && pip3 install redis pymdstat jsonpath-rw

WORKDIR /app

COPY setup.py /app/setup.py
COPY sauna /app/sauna
COPY README.rst /app/README.rst
COPY docker-entrypoint.sh /app/docker-entrypoint.sh

RUN set -x \
  && chmod 755 /app/docker-entrypoint.sh \
  && pip3 install /app \
  && chown sauna:sauna /app

USER sauna

ENTRYPOINT ["/app/docker-entrypoint.sh"]
