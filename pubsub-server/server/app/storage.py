import Queue
import monitoring
from threading import Lock
import log
log = log.getLogger(__name__)

q = Queue.Queue()

def addMessage(message):
    q.put(message)
    monitoring.increasePubsReceived()


def getMessage():
    return q.get()


def ackMessage(message):
    q.task_done()


def getNumberOfMessages():
    return q.qsize()

class PubSubMessage:
    def __init__(self, rawValue):
        self.rawValue = rawValue
        self.rawPublication = False
        self.mapValue = {}
        if 'publication' in rawValue:
            self.rawPublication = False
            for keyValuePair in rawValue["publication"]:
                self.mapValue[keyValuePair["key"]] = {"type": keyValuePair["type"], "val": keyValuePair["val"]}
        else:
            self.rawPublication = True
            for key, value in rawValue.iteritems():
                self.mapValue[key] = {"val": value}

    def value(self):
        if self.rawPublication is False:
            return self.rawValue["publication"]
        else:
            return self.rawValue


# stores the mapping of the client's subscriptions
# {
#   "C1authHash": {"subC1S1": [{"key": "PKI", "value": "price", "op": "EQ"}, ...], "subC1S2": [...]},
#   "C2authHash": {"subC2S1": [{"key": "PKI", "value": "price", "op": "EQ"}, ...]},
#   ...
# }
global subscriptions
subscriptionsLock = Lock()
subscriptions = {}

# Stores the mapping of client's socket connections
# clients1d stores the connections for the subscriptions of all matching messages
# {
#   "C1authHash": [socket_connection, ...],
#   "C2authHash": [socket_connection, ...],
#   ...
# }
global clients1d
clients1dLock = Lock()
clients1d = {}

# clients2s stores the connections for the subscriptions for specific filtering
# {
#   "C1authHash": {"subC1S1": [socket_connection, ...], "subC1S2": [socket_connection, ...]},
#   "C2authHash": {"subC2S1": [socket_connection, ...]},
#   ...
# }
global clients2d
clients2dLock = Lock()
clients2d = {}

# metricsClients stores the connections of the clients interested in the metrics
# {
#   "C1authHash": [socket_connection, ],
#   ...
# }
global metricsClients
metricsClientsLock = Lock()
metricsClients = {}

# if subscriptionId is None, then this connection will receive all messages which matched any of the subscriptions of
# this client
def addConnection(authHash, connection, subscriptionId=None):
    # check if the authHash is allowed to get the monitoring metrics
    # if so register the connection to receive the metrics
    if monitoring.metricsEnabled and authHash == monitoring.metricsAuthHash:
        with metricsClientsLock:
            if authHash not in metricsClients: metricsClients[authHash] = []
            metricsClients[authHash] += [connection]
        log.info("Added monitoring subscription: %s", authHash)
    elif subscriptionId is None:
        with clients1dLock:
            if authHash not in clients1d: clients1d[authHash] = []
            clients1d[authHash] += [connection]
        log.info("Added match-all subscription: %s", authHash)
    else:
        with clients2dLock:
            if authHash not in clients2d: clients2d[authHash] = {}
            if subscriptionId not in clients2d[authHash]:
                clients2d[authHash][subscriptionId] = [connection]
            else:
                clients2d[authHash][subscriptionId] += [connection]
        log.info("Added subscription: %s/%s", authHash, subscriptionId)


def getConnections(authHash, subscriptionId=None):
    allConnections = []
    if authHash in clients1d:
        with clients1dLock:
            if authHash in clients1d: allConnections += clients1d[authHash]
    if subscriptionId is not None and authHash in clients2d and subscriptionId in clients2d[authHash]:
        with clients2dLock:
            if subscriptionId is not None and authHash in clients2d and subscriptionId in clients2d[authHash]: allConnections += clients2d[authHash][subscriptionId]
    if authHash in metricsClients:
        with metricsClientsLock:
            if authHash in metricsClients: allConnections += metricsClients[authHash]

    return allConnections


# If there is no more connections for the subscription, the subscription will be removed
# If there is no subscriptions for the authHash, the client's authHash is removed
def removeConnection(connection, authHash, subscriptionId):
    noConnections = False
    with clients2dLock:
        if authHash in clients2d and subscriptionId in clients2d[authHash]:
            # remove this specific connection
            if connection in clients2d[authHash][subscriptionId]:
                clients2d[authHash][subscriptionId].remove(connection)
                log.debug("Removed connection from the subscription %s/%s", authHash, subscriptionId)
            # if there is no more connection remove whole subscription
            if len(clients2d[authHash][subscriptionId]) == 0:
                clients2d[authHash].pop(subscriptionId, None)
                noConnections = True
            # if there is no more subscriptions, remove while client
            if len(clients2d[authHash]) == 0:
                clients2d.pop(authHash, None)
    # if there is no more connections for the subscription then remove the subscription from the memory
    if noConnections:
        with subscriptionsLock:
            if authHash in subscriptions and subscriptionId in subscriptions[authHash]:
                subscriptions[authHash].pop(subscriptionId, None)
            if len(subscriptions[authHash]) == 0:
                subscriptions.pop(authHash, None)
        log.debug("Removed subscription %s/%s", authHash, subscriptionId)

    # it is possible that the connection does not belong to the subscriptionId
    # but it was registered to receive all matched messages
    if authHash in clients1d and connection in clients1d[authHash]:
        with clients1dLock:
            if authHash in clients1d and connection in clients1d[authHash]:
                clients1d[authHash].remove(connection)


def addSubscription(authHash, subscriptionId, constraints):
    clientSubscriptions = getSubscriptions(authHash)
    with subscriptionsLock:
        clientSubscriptions[subscriptionId] = constraints
    log.info("Added new subscription %s/%s: %s", authHash, subscriptionId, constraints)


def getSubscriptions(authHash=None):
    if authHash is None:
        return subscriptions
    if authHash not in subscriptions:
        with subscriptionsLock:
            if authHash not in subscriptions: subscriptions[authHash] = {}
    return subscriptions[authHash]


def removeSubscription(authHash, subscriptionId):
    if authHash in clients2d and subscriptionId in clients2d[authHash]:
        with clients2dLock:
            if authHash in clients2d and subscriptionId in clients2d[authHash]:
                clients2d[authHash].pop(subscriptionId, None)
                # if there is no more subscriptions, remove while client
                if len(clients2d[authHash]) == 0: clients2d.pop(authHash, None)
        with subscriptionsLock:
            if authHash in subscriptions:
                subscriptions[authHash].pop(subscriptionId, None)
                if len(subscriptions[authHash]) == 0: subscriptions.pop(authHash, None)

        log.debug("Removed subscription %s/%s", authHash, subscriptionId)


# removes all subscriptions and connections of the client authenticated with authHash
def removeSubscriptions(authHash):
    if authHash in clients2d:
        with clients2dLock:
            if authHash in clients2d: clients2d.pop(authHash, None)
    if authHash in subscriptions:
        with subscriptionsLock:
            if authHash in subscriptions: subscriptions.pop(authHash, None)
    log.debug("Removed client %s", authHash)
