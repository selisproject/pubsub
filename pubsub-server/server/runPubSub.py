#!python-env/bin/python

import threading
import argparse
import ssl
from app import app
from app import server
from app import monitoring
from app import processor
from app import rest

#versionNumber = YYMMDDHHmm
versionNumber = "1905141000"

def main():
    parser = argparse.ArgumentParser(description="The SELIS Publish/Subscriber Server", )
    parser.add_argument("--metricsAuthHashFile", metavar="FILE_NAME", default=None, dest="metricsAuthHashFile", help="File which contains the authHash to be used by monitoring subscribers")
    parser.add_argument("--metricsInterval", default=5, dest="metricsInterval", help="How frequency the monitoring report is sent to the listeners")
    parser.add_argument("--production", dest="production", action="store_true", help="Sets the IP address of the production PubSub")
    parser.add_argument("--with-authorization", dest="withAuthorization", action='store_true', help="Turns on the authorization mechanism of PubSub")
    parser.add_argument("--port", dest="port", default=20000, help="Port of the PubSub")
    parser.add_argument("--hostname", dest="hostname", default="localhost", help="Port of the REST API")
    parser.add_argument("--workers", dest="workersNumber", default=5, help="Set the number of workers which process the message")
    parser.add_argument("--instances", dest="instances", default=1, help="# of instances")
    parser.add_argument("--instanceId", dest="instanceId", default=0, help="instanceID")
    parser.add_argument("--certificate", dest="cert", default=None, help="X.509 TLS certificate")
    parser.add_argument("--private-key", dest="key", default=None, help="RSA TLS private key")
    parser.add_argument("--keycloak-url", dest="keycloak_url", default=None, help="URL of the Keycloak API")
    parser.add_argument("--keycloak-user", dest="keycloak_user", default=None, help="Keycloak client username")
    parser.add_argument("--keycloak-password", dest="keycloak_password", default=None, help="Keycloak client password")
    parser.add_argument("--keycloak-realm", dest="keycloak_realm", default=None, help="Keycloak realm")
    args = parser.parse_args()


    if args.production is not None and args.production:
        args.hostname = "147.102.4.108"
    server.hostname = args.hostname

    if int(args.instanceId) >= int(args.instances):
        print "Incorrect instanceId, can not be greater than the number of instances"
        exit(1)

    if args.keycloak_url is None:
        print "Keycloak API URL not specified"
        exit(1)

    # verify that TLS certificate and private key exists and can be used to create SSL context
    if args.cert is not None and args.key is not None:
        try:
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(certfile=args.cert, keyfile=args.key)
            # get the hostname from the certificate
            #from OpenSSL import crypto
            #cert = crypto.load_certificate(crypto.FILETYPE_PEM, open(args.cert).read())
            #server.hostname = cert.get_subject().CN
        except IOError as msg:
            print "Invalid TLS certificate or private key: " + str(msg[1])
            exit(1)

    print "The SELIS Publish/Subscriber Server, version: " + versionNumber
    print "Pub/Sub behind TLS on: " + server.hostname
    print "InstanceId: %d, processing workers: %d" % (int(args.instanceId), int(args.workersNumber))
    restPort = int(args.port) + 3 * int(args.instanceId)
    print "REST API: %s:%d" % (args.hostname, restPort)

    threads = []
    t = threading.Thread(target=monitoring.runMonitoringThread, args=[args.metricsAuthHashFile, args.metricsInterval])
    t.setDaemon(True)
    threads.append(t)

    processor.skipAuthorization = not args.withAuthorization
    processor.numberOfWorkers = int(args.workersNumber)
    if processor.numberOfWorkers > 0:
        for i in range(processor.numberOfWorkers):
            t = threading.Thread(target=processor.runMessageProcessor, args=[not args.withAuthorization])
            t.setDaemon(True)
            threads.append(t)

    rest.keycloak_params = {"url": args.keycloak_url, "realm": args.keycloak_realm,
                            "user": args.keycloak_user, "password": args.keycloak_password}

    socketPort = int(args.port) + 3 * int(args.instanceId) + 1
    t = threading.Thread(target=server.runSocketServer, args=["0.0.0.0", socketPort, args.cert, args.key])
    threads.append(t)

    websocketPort = int(args.port) + 3 * int(args.instanceId) + 2
    t = threading.Thread(target=server.runWebsocketServer, args=["0.0.0.0", websocketPort, args.cert, args.key])
    threads.append(t)

    t = threading.Thread(target=rest.appRun, args=["0.0.0.0", restPort, args.cert, args.key, False, args.instances, args.instanceId])
    threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()


main()
