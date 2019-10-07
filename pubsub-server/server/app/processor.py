import json
import auth, server, monitoring, storage
import time
import log
from log import Lazy
log = log.getLogger(__name__)

global skipAuthorization
skipAuthorization = True
global numberOfWorkers
numberOfWorkers = 0

def runMessageProcessor(skipAuth):
    global skipAuthorization
    skipAuthorization = skipAuth
    log.info("Processing Worker started with auth filtering: %s", not skipAuthorization)

    while True:
        message = storage.getMessage()
        log.debug(Lazy(lambda: "Processing message: %s" % message))
        processMessage(message)
        storage.ackMessage(message)


def processMessage(message):
    # Step 1: go through all registered subscriptions and leave only those which match the message
    subscriptions = matchSubscriptions(message.mapValue)

    # Step 2: go through all matched subscribers, and check if they are permitted to receive the given message
    subscriptions = matchPermissions(subscriptions, message.mapValue)

    # save metrics if the monitoring is turned on
    if monitoring.metricsAuthHash:
        monitoring.increasePubsMatched(sum([len(x) for x in subscriptions.values()]))

    # Step 3: send the message to all matched subscribers
    for authHash, subs in subscriptions.items():
        for subscriptionId in subs:
            content = json.dumps(message.value())
            log.debug("Forwarding message: %s to %s/%s", content, authHash, subscriptionId)
            server.sendMessage(authHash, subscriptionId, content + "\n")


# returns the map of the clients and their socket_connections to which the message should be forwarded
# {
#   "C1AuthHash": [subId1, subId2, subId3],
#   "C2AuthHash": [subId1],
#   ...
# }
def matchSubscriptions(message):
    destinations = {}
    for authHash, subscriptions in storage.getSubscriptions().items():
        for subscriptionId, constraints in subscriptions.items():
            if matchConstraints(constraints, message) is True:
                log.debug(Lazy(lambda: "Filter level 1: message %s matches subscription %s/%s" % (json.dumps(message), authHash, subscriptionId)))
                if authHash not in destinations: destinations[authHash] = []
                destinations[authHash].append(subscriptionId)
    log.debug(Lazy(lambda: "Filter level 1: message %s subscriptions: %s" % (message, destinations)))
    return destinations


#
# returns the map of the clients and their socket connections to which the message should be forwarded
# {
#   "C1AuthHash": [subId1, subId2, subId3],
#   "C2AuthHash": [subId1],
#   ...
# }
def matchPermissions(matchedSubscriptions, message):
    if skipAuthorization:
        return matchedSubscriptions

    authorized = {}
    for authHash, subscriptions in matchedSubscriptions.items():
        permissions = auth.getPermissions(authHash)
        # permissions are the whitelist of what messages user can receive. it contains list of permission
        # where single permission is contains the set of message constraints

        matchSuccess = False
        for permission in permissions:
            # permission is in the same format as subscription constraints, hence we can use the same mechanism
            # for filtering
            if matchConstraint(permission, message):
                log.debug(Lazy(lambda: "Filter level 2: message %s matches subscription %s" % (json.dumps(message), authHash)))
                # it is enough, that one permission matches, to allow subscriber to receive the message
                matchSuccess = True
                break

        if matchSuccess:
            authorized[authHash] = subscriptions

    return authorized


# returns the value converted to the valid type (int/float/bool/str)
# if there is not "type" key in the map, the value is returned without casting
def convertType(mapEntry):
    value_type = ""
    if "type" in mapEntry:
        value_type = mapEntry["type"]
    val = mapEntry["val"]

    if value_type == "int": val = int(val)
    elif value_type == "float": val = float(val)
    elif value_type == "boolean": val = bool(val)
    elif value_type == "string": val = str(val)

    return val


# returns True/False if the message match all the constrains defined in the subscription
def matchConstraints(constraints, message):
    matchSuccess = True
    for constraint in constraints:
        matchSuccess = matchConstraint(constraint, message)
        if matchSuccess is False:
            break
    return matchSuccess


# returns True/False if the message match the given constraint
def matchConstraint(constraint, message):
    key = constraint["key"]
    if key not in message.keys():
        log.debug("key %s not found in publication", key)
        return False

    valueSubscription = convertType(constraint)
    valuePublication = convertType(message[key])
    operator = constraint["op"]

    matchSuccess = False
    if operator == "eq":
        # special case for wildcard - the subscription value of * means accept everything
        if valueSubscription == "*" or valueSubscription == valuePublication:
            matchSuccess = True
    elif operator == "ne":
        if valueSubscription != valuePublication: matchSuccess = True
    elif operator == "lt":
        if valueSubscription > valuePublication: matchSuccess = True
    elif operator == "le":
        if valueSubscription >= valuePublication: matchSuccess = True
    elif operator == "gt":
        if valueSubscription < valuePublication: matchSuccess = True
    elif operator == "ge":
        if valueSubscription <= valuePublication: matchSuccess = True
    else:
        log.debug("invalid operator: %s", operator)

    if matchSuccess:
        log.debug(Lazy(lambda: "constraint holds %s: (%s %s %s) is true" % (key, str(valuePublication), str(operator), str(valueSubscription))))
        return True

    log.debug(Lazy(lambda: "constraint does not hold %s: (%s %s %s) is false" % (key, str(valuePublication), str(operator), str(valueSubscription))))
    return False
