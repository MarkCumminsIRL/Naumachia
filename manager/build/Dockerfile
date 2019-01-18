FROM alpine:latest

RUN echo "http://dl-cdn.alpinelinux.org/alpine/edge/community/" >> /etc/apk/repositories && \
    echo "http://dl-cdn.alpinelinux.org/alpine/edge/testing/" >> /etc/apk/repositories && \
    apk add --update python3 py3-pip iproute2 docker-compose && \
    rm -rf /tmp/* /var/tmp/* /var/cache/apk/* /var/cache/distfiles/*

COPY ./requirements.txt /requirements.txt
RUN pip3 install -r /requirements.txt

CMD [ "python3", "/app/manager.py" ]
