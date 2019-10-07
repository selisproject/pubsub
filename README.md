# The SELIS Publish/Subscribe system
## About
This repository contains the minimalistic version of the SELIS Publish-Subscribe server. 
This minimalistic version (we will refer to it as the SELIS Pub/Sub light) consists of: 
* a single instance server exposing both the REST API and the socket-based subscriber interface.
* client libraries for Java and GO languages.
The SELIS Pub/Sub light permits content-based routing of messages with support for permission enforcement. 

We recommend to use this version only for the development and testing of the SELIS components and DSS applications. 

The production version supports:
* running securely inside the Intel SGX enclave,
* multi-node deployment to achieve scalability and high-availability
* monitoring system

**For the production version please make an inquiry.**

## Server
To access the open source version of the SELIS Publish/Subscribe server, please go to: [server sources](pubsub-server/).
## Client libraries
To access the open source version of the SELIS Publish/Subscribe client libraries, please go to: [client libraries sources](pubsub-clients/).
## Contact
selis-project@groups.tu-dresden.de
