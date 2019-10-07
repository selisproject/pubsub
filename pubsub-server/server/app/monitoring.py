import json
import time
import os.path
from threading import Lock

import storage
import server

import log
log = log.getLogger(__name__)

global metricsEnabled
metricsEnabled = False
global metricsAuthHash
metricsAuthHash = None
global metricsInterval
metricsInterval = 5

# TODO: Is there a better solution than acquiring a lock for metrics?
# E.g. atomic integral datatypes which support atomic get-and-set?
metricsLock = Lock()
metricsPubsReceived = 0
metricsPubsMatched = 0
metricsPubsForwarded = 0

def increasePubsReceived():
    if metricsEnabled:
        with metricsLock:
            global metricsPubsReceived
            metricsPubsReceived = metricsPubsReceived + 1


def increasePubsMatched(matched=1):
    if metricsEnabled:
        with metricsLock:
            global metricsPubsMatched
            metricsPubsMatched = metricsPubsMatched + matched


def increasePubsForwarded():
    if metricsEnabled:
        with metricsLock:
            global metricsPubsForwarded
            metricsPubsForwarded = metricsPubsForwarded + 1


def generateMonitoringReport():
    global metricsPubsReceived
    global metricsPubsMatched
    global metricsPubsForwarded

    report = {}
    report["timestamp"] = int(round(time.time() * 1000))
    report["state"] = {}
    report["ops"] = {}
    report["performance"] = {}
    report["state"]["subscribers"] = len(storage.subscriptions)
    report["state"]["subscriptions"] = sum([len(x) for x in storage.subscriptions.values()])
    report["state"]["subscriberConnections"] = sum([len(x) for x in storage.clients1d.values()]) + sum(
        [sum([len(y) for y in x.values()]) for x in storage.clients2d.values()])
    report["state"]["queuedMessages"] = storage.getNumberOfMessages()
    with metricsLock:
        report["ops"]["publicationsReceived"] = metricsPubsReceived
        report["ops"]["publicationsMatched"] = metricsPubsMatched
        report["ops"]["publicationsForwarded"] = metricsPubsForwarded
        report["performance"]["publicationsReceivedPerSecond"] = metricsPubsReceived / metricsInterval
        report["performance"]["publicationsMatchedPerSecond"] = metricsPubsMatched / metricsInterval
        report["performance"]["publicationsForwardedPerSecond"] = metricsPubsForwarded / metricsInterval
        if metricsPubsReceived > 0:
            report["performance"]["receivedProcessedRatio"] = float(float(metricsPubsMatched) / float(metricsPubsReceived))
        metricsPubsReceived = 0
        metricsPubsMatched = 0
        metricsPubsForwarded = 0

    return report


def runMonitoringThread(metricsAuthHashArg, metricsSendInterval):
    global metricsEnabled
    global metricsAuthHash
    global metricsInterval
    metricsInterval = max(1, int(metricsSendInterval)) # do not allow to get metric more frequent than 1s

    authHashFileName = metricsAuthHashArg
    if authHashFileName is None:
        defaultmetricsAuthHashFile = "monitoring.conf"
        # only use default file if it exists
        if os.path.isfile(defaultmetricsAuthHashFile):
            authHashFileName = defaultmetricsAuthHashFile

    if authHashFileName is not None:
        # errors while opening will terminate the process
        with open(authHashFileName) as f:
            log.info("Monitoring Service started, update every %ds", metricsInterval)
            metricsEnabled = True
            metricsAuthHash = f.readline().strip()

    while metricsEnabled:
        # The metrics are not generated exactly within the given time (since the report generation takes some time itself,
        # together with interrupts, context switches, etc.), but it should be close enough for our use case
        time.sleep(metricsInterval)
        metricsReportJson = unicode(json.dumps(generateMonitoringReport()), "utf-8")
        log.debug(metricsReportJson)

        server.sendMessage(metricsAuthHash, None, metricsReportJson)