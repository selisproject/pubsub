The SELIS Publish-Subscribe (light open source version)
===================
This repository contains the minimalistic version of the SELIS Publish-Subscribe server. 
This minimalistic version (we will refer to it as the SELIS Pub/Sub light) consists of 
a single instance server exposing both the REST API and the socket-based subscriber interface.
It permits content-based routing of messages. 
The permission enforcement is supported but requires configuration of the Keycloak server.

This version can be used only for the development and testing of the SELIS components and DSS applications. 

The production version supports:
* running securely inside the Intel SGX enclave,
* multi-node deployment to achieve scalability and high-availability
* monitoring system

**For the production version please make an inquiry.**

## Installation
This tutorial will lead you through the creation of the Docker image containing the SELIS Pub/Sub light.
From this moment, we assume you have installed the latest Docker: 
https://docs.docker.com/install/

In order to build the SELIS Pub/Sub light from sources, download the repository:
```
git clone https://selis-gw.cslab.ece.ntua.gr/gitlab/selis/pubsub-server
```
then, build the image:
```
sudo docker build -t pubsub pubsub-server/.
```

Alternatively, you can simply use the pre-built Docker images located at the Docker hub repository:
```
docker pull tudselis/pubsub:dev-1903131057
```

## Run
To start the SELIS Pub/Sub light you must first obtain the image as described in the `Installation` section of this document.
Then, simply start a new container by executing the following command:
```
docker run -d --name=$HOSTNAME -p 20000:20000 -p 20001:20001 -p 20002:20002 -e "HOSTNAME=$HOSTNAME" -e "CERTIFICATE=/certificates/certificate_chain.pem" -e "PRIVATE_KEY=/certificates/private_key.pem" -v "/path/to/credentials/:/certificates/:ro" pubsub
```
where:
* `$HOSTNAME` is the hostname of the machine on which you run the SELIS Pub/Sub light
* `/path/to/credentials` is the absolute path to the directory where the TLS private key (private_key.pem) and the TLS certificate (certificate_chain.pem) are.
* `pubsub` is the name of the Docker image (it will be `tudselis/pubsub:dev-...` when pulled from the Docker hub)

For the localhost deployment, you can use the `gencerts.sh` script to generate test TLS credentials.

## Usage
The SELIS Pub/Sub light exposes the REST API on the port 20000. To check the connectivity with the server, you can send a simple request:
```
curl --cacert root.crt -X GET https://$HOSTNAME:20000
```
where:
* `root.crt` is the root CA certificate required to verify the SELIS Pub/Sub light's TLS certificate

To publish a new message:
```
curl -H "Content-Type: application/json" -d '{"publication":[ {"key" :"lat","val" : 20 , "type" : "int" }, { "key" : "lon", "val":10 ,"type":"int"}]}' http://$HOSTNAME:20000/publish
```

Please check the SELIS Pub/Sub clients repository to learn how to quickly publish and subscribe messages:
```
git clone https://selis-gw.cslab.ece.ntua.gr/gitlab/selis/pubsub-clients
```
We recommend to start from the JAVA exampe located in the `java/example` directory of the pubsub-clients repository.

License
-------
MIT

Contact
-------
selis@cslab.ece.ntua.gr 