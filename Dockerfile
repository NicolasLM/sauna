FROM alpine:3.3

MAINTAINER Nicolas Le Manchet <nicolas@lemanchet.fr>

RUN set -x \
    && addgroup -S sauna \
    && adduser -D -S -h /var/cache/sauna -G sauna sauna \
    && apk add --no-cache python3 python3-dev gcc linux-headers musl-dev

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN set -x \
  && pyvenv /app \
  && /app/bin/pip install -r requirements.txt

COPY setup.py /app/setup.py
COPY sauna /app/sauna
COPY README.rst /app/README.rst
COPY docker-entrypoint.sh /app/docker-entrypoint.sh

RUN set -x \
  && chmod 755 /app/docker-entrypoint.sh \
  && /app/bin/python /app/setup.py install \
  && chown sauna:sauna /app

USER sauna

ENTRYPOINT ["/app/docker-entrypoint.sh"]
