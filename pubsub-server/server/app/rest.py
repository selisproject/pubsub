from flask import jsonify, request, make_response, Response
from app import app
import auth
import json
import uuid
import server, storage, processor
import hashlib
import log
import ssl
import traceback
import urllib
import urllib2
from log import Lazy
log = log.getLogger(__name__)

global serverInstanceId
global serverInstances
global keycloak_params


def appRun(host, port, certificate, private_key, debug=False, instances=1, instanceId=0):
    global serverInstanceId
    global serverInstances
    serverInstanceId = int(instanceId)
    serverInstances = int(instances)
    if certificate is not None and private_key is not None:
        # start the REST api listener
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        context.load_cert_chain(certificate, private_key)
        app.run(host=host, port=int(port), ssl_context=context)
    else:
        app.run(host=host, port=int(port))

def notEmpty(request, key):
    return key in request.json and request.json[key] != ""


def getOrFail(request, key):
    if key not in request.json:
        return make_response(jsonify({"error": "invalid input", "description": "missing " + str(key) + " parameter"}), 500)
    return request.json[key]

# if default_value is not provided, this method will generate error to the client
def getValueFromRequest(request, key, default_value=None):
    if key not in request.json:
        if default_value is not None:
            return default_value
        return make_response(jsonify({"error": "invalid input", "description": "missing " + str(key) + " parameter"}), 500)
    return request.json[key]

def getClientCredentials():
    url = keycloak_params['url'] + '/auth/realms/' + keycloak_params['realm'] + '/protocol/openid-connect/token'
    data = { 'grant_type' : 'client_credentials',
             'client_id' : keycloak_params['user'],
             'client_secret' : keycloak_params['password']
    }
    r = urllib2.Request(url, data=urllib.urlencode(data))
    response = urllib2.urlopen(r, data=urllib.urlencode(data))
    return json.loads(response.read())['access_token']

def getUMATicketResponse(authhash):
    url = keycloak_params['url'] + '/auth/realms/' + keycloak_params['realm'] + '/protocol/openid-connect/token'
    data = { 'grant_type' : 'urn:ietf:params:oauth:grant-type:uma-ticket',
             'audience' : keycloak_params['user'],
    }
    r = urllib2.Request(url, data=urllib.urlencode(data),
                        headers={'Authorization': 'Bearer ' + authhash})
    response = urllib2.urlopen(r, data=urllib.urlencode(data))
    rtk = response.read()
    jrtk = json.loads(rtk)
    return jrtk['access_token']

def introspectUMAResponse(token, ctx):
    ret = []
    url = keycloak_params['url'] + '/auth/realms/' + keycloak_params['realm'] + '/protocol/openid-connect/token/introspect'
    data = { 'client_id' : keycloak_params['user'],
             'client_secret' : keycloak_params['password'],
             'token_type_hint' : 'requesting_party_token',
             'token' : token,
    }
    r = urllib2.Request(url, data=urllib.urlencode(data))
    response = urllib2.urlopen(r, data=urllib.urlencode(data), context=ctx)
    rtk = response.read()
    jrtk = json.loads(rtk)
    perms = jrtk['permissions']
    for rule in perms:
        rule['rsname'] = rule['rsname'].replace("'", '"')
        rule_obj = json.loads(rule['rsname'])
        log.info(rule_obj)
        ret.append(rule_obj)
    return ret

def getKeycloakPermissions(authhash):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        uma = getUMATicketResponse(authhash)
        ret = introspectUMAResponse(uma, ctx)
        return (True, ret)
    except Exception as e:
        log.info('Authentication failed: ' + authhash + ' ' + str(e))
        traceback.print_exc()
        return (False, [])

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({"error": "Not found"}), 404)


@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({"error": "bad request"}), 400)


@app.route("/")
@app.route("/index")
def index():
    return "The SELIS Publish/Subscribe Server is up and running"


@app.route("/shutdown")
def shutdown():
    log.info("Shutting down the SELIS Publish/Subscribe Server")


@app.route("/subscribe", methods=["POST"])
def subscribe():
    if notEmpty(request, "subscriptionId"):
        # this should be depreciated. subscriptionId should be assigned by the Pub/Sub and used later on by the client
        subscriptionId = getOrFail(request, "subscriptionId")
    else:
        # we assume that the user is not forced to give the subscriptionId and we will generate one. He will reference
        # it in the future when connecting with sockets
        # like this we eliminate conflicts of the same subscriptionId (client could give the same id twice)
        subscriptionId = str(uuid.uuid4())

    authHash = getOrFail(request, "authHash")
    rawData = getOrFail(request, "data")

    # verify the authHash, populate restrictions
    ok, perms = getKeycloakPermissions(authHash)
    if ok:
        auth.addPermissions(authHash, perms)
    else:
        return Response(response="Permission denied", status=401)

    # subscription partitioning
    if int(hashlib.sha1(subscriptionId).hexdigest(), 16) % serverInstances == serverInstanceId:
        storage.addSubscription(authHash, subscriptionId, rawData)
    
    return Response(response=json.dumps({"host": server.hostname, "port": server.socketServerPort, "wsport": server.websocketServerPort, "subscriptionId": subscriptionId}),
        status=200, mimetype="application/json")


@app.route("/unsubscribe", methods=["POST"])
def unsubscribe():
    authHash = getOrFail(request, "authHash")
    subscriptionId = getValueFromRequest(request, "subscriptionId", "")
    log.info("Unsubscribing %s/%s", authHash, subscriptionId)

    if subscriptionId is not "":
        storage.removeSubscription(authHash, subscriptionId)
    else:
        storage.removeSubscriptions(authHash)

    return "{}"


@app.route("/publish", methods=["POST"])
def publish():
    try:
        message = storage.PubSubMessage(request.json)
    except:
        return make_response(jsonify({"error": "bad request"}), 400)

    log.debug(Lazy(lambda: "Received new Message in publish/: %s" % message.value()))

    if processor.numberOfWorkers > 0:
        storage.addMessage(message)
    else:
        processor.processMessage(message)

    return "{}"


