import logging.config

logging.config.fileConfig("logging.conf")

log = logging.getLogger("pubsub")


def getLogger(name):
    return log


def info(func):
    log.info(Lazy(func))


def debug(func):
    log.debug(Lazy(func))


class Lazy(object):
    def __init__(self,func):
        self.func=func
        
    def __str__(self):
        return self.func()