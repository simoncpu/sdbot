from ..utils import getif

def init_config():
    config = {}
    getif(config, "token", "SLACK_TOKEN")
    getif(config, "loglevel", "LIMBO_LOGLEVEL")
    getif(config, "logfile", "LIMBO_LOGFILE")
    getif(config, "logformat", "LIMBO_LOGFORMAT")
    getif(config, "plugins", "LIMBO_PLUGINS")
    getif(config, "heroku", "LIMBO_ON_HEROKU")
    getif(config, "beepboop", "BEEPBOOP_TOKEN")
    return config

CONFIG = init_config()
