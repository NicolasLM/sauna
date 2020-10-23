FROM alpine:edge

MAINTAINER Nicolas Le Manchet <nicolas@lemanchet.fr>

RUN set -x \
    && addgroup -S sauna \
    && adduser -u 4343 -D -S -h /app -G sauna sauna \
    && apk update \
    && apk add python3 py3-pip py3-wheel py3-psutil py3-yaml py3-docopt py3-requests py3-redis \
    && pip install pymdstat jsonpath-rw

WORKDIR /app

COPY setup.py /app/setup.py
COPY sauna /app/sauna
COPY README.rst /app/README.rst
COPY docker-entrypoint.sh /app/docker-entrypoint.sh

RUN set -x \
  && chmod 755 /app/docker-entrypoint.sh \
  && pip install /app \
  && chown sauna:sauna /app

USER sauna

ENTRYPOINT ["/app/docker-entrypoint.sh"]
