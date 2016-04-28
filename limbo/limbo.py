#!/usr/bin/env python
from __future__ import print_function
import copy
import functools
from glob import glob
import importlib
import logging
import os
import re
import sqlite3
import sys
import time
import traceback
import json

from slackrtm import SlackClient
from slackrtm.server import SlackConnectionError, SlackLoginError

from beepboop import resourcer
from beepboop import bot_manager

from .server import LimboServer
from .fakeserver import FakeServer

from .handlers import handle_event, bb_handlers, run_hook
from .utils import (decode,
                    encode,
                    relevant_environ,
                    strip_extension)
from .settings import CONFIG


CURDIR = os.path.abspath(os.path.dirname(__file__))
DIR = functools.partial(os.path.join, CURDIR)

logger = logging.getLogger(__name__)


class InvalidPluginDir(Exception):
    def __init__(self, plugindir):
        message = "Unable to find plugin dir {0}".format(plugindir)
        super(InvalidPluginDir, self).__init__(message)


class Slackbot(object):
    def __init__(self, bot_token=None, ServerClass=LimboServer, Client=SlackClient, config=CONFIG):
        self.resource = None
        self.server = None
        if bot_token:
            # using resource if no token
            self.token = bot_token

        self.ServerClass = ServerClass
        self.Client = Client
        self.config = config

        self._init_log(config)
        logger.debug("config: {0}".format(config))
        config_plugins = config.get("plugins")
        plugins_to_load = config_plugins.split(",") if config_plugins else []

        # disable custom plugindir for now. In the future, input that through
        # config instead. Replace None with something else later
        self.hooks = self._init_plugins(None, plugins_to_load)

    def _init_log(self, config):
        loglevel = config.get("loglevel", logging.INFO)
        logformat = config.get("logformat", '%(asctime)s:%(levelname)s:%(name)s:%(message)s')
        if config.get("logfile"):
            logging.basicConfig(filename=config.get("logfile"), format=logformat, level=loglevel)
        else:
            logging.basicConfig(format=logformat, level=loglevel)

    def _init_plugins(self, plugindir, plugins_to_load=None):
        if plugindir and not os.path.isdir(plugindir):
            raise InvalidPluginDir(plugindir)

        if not plugindir:
            plugindir = DIR("plugins")

        logger.debug("plugindir: {0}".format(plugindir))

        if os.path.isdir(plugindir):
            pluginfiles = glob(os.path.join(plugindir, "[!_]*.py"))
            plugins = strip_extension(os.path.basename(p) for p in pluginfiles)
        else:
            # we might be in an egg; try to get the files that way
            logger.debug("trying pkg_resources")
            import pkg_resources
            try:
                plugins = strip_extension(
                        pkg_resources.resource_listdir(__name__, "plugins"))
            except OSError:
                raise InvalidPluginDir(plugindir)

        hooks = {}

        oldpath = copy.deepcopy(sys.path)
        sys.path.insert(0, plugindir)

        for plugin in plugins:
            if plugins_to_load and plugin not in plugins_to_load:
                logger.debug("skipping plugin {0}, not in plugins_to_load {1}".format(plugin, plugins_to_load))
                continue

            logger.debug("plugin: {0}".format(plugin))
            try:
                mod = importlib.import_module(plugin)
                modname = mod.__name__
                for hook in re.findall("on_(\w+)", " ".join(dir(mod))):
                    hookfun = getattr(mod, "on_" + hook)
                    logger.debug("plugin: attaching %s hook for %s", hook, modname)
                    hooks.setdefault(hook, []).append(hookfun)

                if mod.__doc__:
                    # firstline = mod.__doc__.split('\n')[0]
                    part_attachment = json.loads(mod.__doc__)
                    hooks.setdefault('help', {})[modname] = part_attachment
                    hooks.setdefault('extendedhelp', {})[modname] = mod.__doc__

            # bare except, because the modules could raise any number of errors
            # on import, and we want them not to kill our server
            except:
                logger.warning("import failed on module {0}, module not loaded".format(plugin))
                logger.warning("{0}".format(sys.exc_info()[0]))
                logger.warning("{0}".format(traceback.format_exc()))

        sys.path = oldpath
        return hooks

    def start(self, resource):
        self.resource = resource
        logger.debug("Started Bot for ResourceID: {}".format(
            self.resource['resourceID'])
        )
        if self.resource:
            slack = self.Client(self.resource['resource']['SlackBotAccessToken'])
        else:
            slack = self.Client(self.token)

        # Currently not supporting a database, might do later
        self.server = self.ServerClass(slack, self.config, self.hooks, None)
        self.server.slack.rtm_connect()
        self.loop()

    def stop(self, resource):
        logger.debug("Stopped Bot for ResourceID: {}".format(
            self.resource['resourceID'])
        )
        self.server.slack = None
        # close connection to slack.

    def loop(self, test_loop=None):
        """Run the main loop
        server is a limbo Server object
        test_loop, if present, is a number of times to run the loop
        """
        try:
            loops_without_activity = 0
            while test_loop is None or test_loop > 0:
                start = time.time()
                loops_without_activity += 1

                events = self.server.slack.rtm_read()
                for event in events:
                    loops_without_activity = 0
                    logger.debug("got {0}".format(event.get("type", event)))
                    response = handle_event(event, self.server)
                    if response:
                        if isinstance(event['channel'], dict):
                            channel_id = event['channel']['id']
                        else:
                            channel_id = event['channel']
                        self.server.slack.rtm_send_message(channel_id, response)

                # Run the loop hook. This doesn't send messages it receives,
                # because it doesn't know where to send them. Use
                # server.slack.post_message to send messages from a loop hook
                run_hook(self.server.hooks, "loop", self.server)

                # The Slack RTM API docs say:
                #
                # > When there is no other activity clients should send a ping
                # > every few seconds
                #
                # So, if we've gone >5 seconds without any activity, send a ping.
                # If the connection has broken, this will reveal it so slack can
                # quit
                if loops_without_activity > 5:
                    self.server.slack.server.ping()
                    loops_without_activity = 0

                end = time.time()
                runtime = start - end
                time.sleep(max(1 - runtime, 0))

                if test_loop:
                    test_loop -= 1
        except KeyboardInterrupt:
            if os.environ.get("LIMBO_DEBUG"):
                import pdb; pdb.set_trace()
            raise


def init_server(args, config, Server=LimboServer, Client=SlackClient):
    """Init_server should be deprecated"""
    # note, key error should be added at main.
    init_log(config)
    logger.debug("config: {0}".format(config))
    db = init_db(args.database_name)

    config_plugins = config.get("plugins")
    plugins_to_load = config_plugins.split(",") if config_plugins else []

    hooks = init_plugins(args.pluginpath, plugins_to_load)
    try:
        slack = Client(config["token"])
    except KeyError:
        logger.error("""Unable to find a slack token. The environment variables
limbo sees are:
{0}

and the current config is:
{1}

Try setting your bot's slack token with:

export SLACK_TOKEN=<your-slack-bot-token>
""".format(relevant_environ(), config))
        raise
    server = Server(slack, config, hooks, db)
    return server


def main(args):
    if args.test:
        # FakeServer is not working at the moment.
        init_log(CONFIG)
        return repl(FakeServer(), args)
    elif args.command is not None:
        init_log(CONFIG)
        cmd = decode(args.command)
        print(run_cmd(cmd, FakeServer(), args.hook, args.pluginpath, CONFIG.get("plugins")))
        return

    def spawn_bot(bot_token=None):
        if bot_token:
            return Slackbot(bot_token)
        return Slackbot()

    try:
        # initialize bot runner.
        print(os.environ.keys())
        if CONFIG.get('beepboop'):
            botManager = bot_manager.BotManager(spawn_bot)
            bp = resourcer.Resourcer(botManager)
            bp.handlers(bb_handlers)
            bp.start()
        else:
            bot = spawn_bot(bot_token=CONFIG['token'])
            bot.start()
    except SlackConnectionError:
        logger.warn("Unable to connect to Slack. Bad network?")
        raise
    except SlackLoginError:
        logger.warn("Login Failed, invalid token <{0}>?".format(CONFIG["token"]))
        raise
    except KeyError:
        logger.error("""Unable to find a slack token. The environment variables
limbo sees are:
{0}

and the current config is:
{1}

Try setting your bot's slack token with:

export SLACK_TOKEN=<your-slack-bot-token>
""".format(relevant_environ(), config))
        raise


def run_cmd(cmd, server, hook, pluginpath, plugins_to_load):
    """run a command. cmd should be a unicode string (str in python3, unicode in python2).
       returns a string appropriate for printing (str in py2 and py3)"""

    server.hooks = init_plugins(pluginpath, plugins_to_load)
    event = {'type': hook, 'text': cmd, "user": "2", 'ts': time.time(), 'team': None, 'channel': 'repl_channel'}
    return encode(handle_event(event, server))

# raw_input in 2.6 is input in python 3. Set `input` to the correct function
try:
    input = raw_input
except NameError:
    pass


def repl(server, args):
    try:
        while 1:
            cmd = decode(input("limbo> "))
            if cmd.lower() == "quit" or cmd.lower() == "exit":
                return

            print(run_cmd(cmd, server, args.hook, args.pluginpath, None))
    except (EOFError, KeyboardInterrupt):
        print()
        pass


def init_db(database_file):
    return sqlite3.connect(database_file)
