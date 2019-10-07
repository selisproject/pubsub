import json
import socket, ssl
import sys
import StringIO
import storage
import uuid
from thread import *
from SimpleWebSocketServer import SimpleWebSocketServer, SimpleSSLWebSocketServer, WebSocket
import monitoring

import log
log = log.getLogger(__name__)

global hostname
global socketServerPort
global websocketServerPort

def useTLS(certificate, private_key):
    return certificate is not None and private_key is not None

def runSocketServer(host, port, certificate, private_key):
    global socketServerPort
    socketServerPort = port
    tls = useTLS(certificate, private_key)
    print(("Secure" if tls else "") + "Socket Server listening on: " + str(host) + ":" + str(port))
    context = None
    bindsocket = None
    if tls:
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile=certificate, keyfile=private_key)
        bindsocket = socket.socket()
    else:
        bindsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        bindsocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        bindsocket.bind((host, port))
    except socket.error as msg:
        log.error("Bind failed. Error Code: " + str(msg[0]) + " Message " + msg[1])
        sys.exit()
    bindsocket.listen(10)

    while True:
        conn, addr = bindsocket.accept()
        log.info("Connected with " + addr[0] + ":" + str(addr[1]))
        connstream = None
        if tls:
            try:
                connstream = context.wrap_socket(conn, server_side=True)
            except ssl.SSLError as msg:
                log.error("SSLError. Error Code: " + str(msg[0]) + " Message " + msg[1])
                continue
        start_new_thread(handleSocketConnection, (connstream if tls else conn,))
    bindsocket.close()

def handleSocketConnection(connection):
    buff = StringIO.StringIO(2048)
    while True:
        try:
            data = connection.recv(2048)
            buff.write(data)
        except socket.error as msg:
            connection.close()
            return

        if data == "":
            connection.close()
            return

        if "\n" in data:
            string = buff.getvalue().splitlines()[-1]
            request = json.loads(string)
            if not handleSocketConnectionMessage(request, connection):
                connection.send(json.dumps("authHash or subscriptionId is empty or missing. Rejecting!") + "\n")
                connection.close()
                return
            buff = StringIO.StringIO(2048)
    connection.close()


def runWebsocketServer(host, port, certificate, private_key):
    global websocketServerPort
    websocketServerPort = port

    print("WebSocket Server listening on: " + str(host) + ":" + str(port))
    server = None
    if useTLS(certificate, private_key):
        server = SimpleSSLWebSocketServer(host, port, WebsocketConnectionHandler, certificate, private_key, version=ssl.PROTOCOL_TLSv1)
    else:
        server = SimpleWebSocketServer(host, port, WebsocketConnectionHandler)
    server.serveforever()


class WebsocketConnectionHandler(WebSocket):
    def handleMessage(self):
        data = self.data
        if data == "":
            self.close()
            return

        request = json.loads(data)
        if not handleSocketConnectionMessage(request, self):
            self.send(json.dumps("authHash or subscriptionId is empty or missing. Rejecting!") + "\n")
            self.close()
            return

    def handleConnected(self):
        self.closed = False
        log.info("Connected with {}".format(self.address))

    def handleClose(self):
        self.closed = True
        log.info("Disconnected from {}".format(self.address))


def handleSocketConnectionMessage(request, connection):
    if "authHash" not in request.keys() or request["authHash"] == "":
        log.info("authHash is empty or missing. Rejecting message!")
        return False
    authHash = request["authHash"]

    if "subscriptionId" not in request.keys() or request["subscriptionId"] == "":
        subscriptionId = None
    else:
        subscriptionId = request["subscriptionId"]

    storage.addConnection(authHash, connection, subscriptionId)
    return True


def sendMessage(authHash, subscriptionId, content):
    for connection in storage.getConnections(authHash, subscriptionId):
        try:
            # websocket connection uses sendMessage() while the normal socket connection uses send()
            if hasattr(connection, 'sendMessage'):
                connection.sendMessage(content)
            else:
                connection.send(content)

            if authHash != monitoring.metricsAuthHash:
                monitoring.increasePubsForwarded()
        except socket.error as msg:
            log.debug("Pipe broken %s - removing client's connection for %s/%s", msg, authHash, subscriptionId)
            storage.removeConnection(connection, authHash, subscriptionId)
