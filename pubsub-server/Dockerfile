FROM alpine:3.6

MAINTAINER Bohdan Trach <bohdan.trach@tu-dresden.de>

RUN apk update
RUN apk upgrade
# pip cryptography package needs python- and openssl-dev packages
RUN apk add openssh py-virtualenv ca-certificates bash git build-base python3-dev libffi-dev python-dev openssl-dev
RUN addgroup -S selis
RUN adduser -D -G selis -s /bin/bash selis
RUN echo 'selis:selis' | chpasswd

RUN sed -i 's/PermitRootLogin without-password/PermitRootLogin yes/' /etc/ssh/sshd_config
RUN sed -i 's/Port 22/Port 10022/g' /etc/ssh/sshd_config
RUN mkdir /var/run/sshd

COPY server deploy
WORKDIR deploy
RUN virtualenv python-env
RUN python-env/bin/pip install --upgrade pip setuptools wheel
RUN python-env/bin/pip install -r requirements.txt

ARG HOSTNAME=localhost
ARG CERTIFICATE=./certs/pubsub.crt
ARG PRIVATE_KEY=./certs/pubsub.key
ARG PORT=20000
ARG INSTANCES=1
ARG INSTANCEID=0
ARG KEYCLOAK_URL=keycloak
ARG KEYCLOAK_USER=pubsub_client
ARG KEYCLOAK_PASSWORD=pubsub_secret
ARG KEYCLOAK_REALM=selisrealm


ENV HOSTNAME=${HOSTNAME}
ENV CERTIFICATE=${CERTIFICATE}
ENV PRIVATE_KEY=${PRIVATE_KEY}
ENV PORT ${PORT}
ENV INSTANCES ${INSTANCES}
ENV INSTANCEID ${INSTANCEID}
ENV KEYCLOAK_URL ${KEYCLOAK_URL}
ENV KEYCLOAK_USER=${KEYCLOAK_USER}
ENV KEYCLOAK_PASSWORD=${KEYCLOAK_PASSWORD}
ENV KEYCLOAK_REALM=${KEYCLOAK_REALM}

EXPOSE ${PORT} 20001 20002
CMD python-env/bin/python -u ./runPubSub.py --hostname=${HOSTNAME} --port=${PORT} --instances=${INSTANCES} --instanceId=${INSTANCEID} --certificate=${CERTIFICATE} --private-key=${PRIVATE_KEY} --with-authorization --keycloak-url=${KEYCLOAK_URL} --keycloak-realm=${KEYCLOAK_REALM} --keycloak-user=${KEYCLOAK_USER} --keycloak-password=${KEYCLOAK_PASSWORD}

# the -u flag is important when running python: Otherwise, log output is truncated (u stands for unbuffered)
