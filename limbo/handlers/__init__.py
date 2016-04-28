import json
import logging
import sys
import traceback

logger = logging.getLogger(__name__)


def handle_bot_message(event, server):
    try:
        bot = server.slack.server.bots[event["bot_id"]]
    except KeyError:
        logger.debug("bot_message event {0} has no bot".format(event))
        return

    return "\n".join(run_hook(server.hooks, "bot_message", event, server))


def handle_message(event, server):
    subtype = event.get("subtype", "")
    if subtype == "message_changed":
        return

    if subtype == "bot_message":
        return handle_bot_message(event, server)

    try:
        msguser = server.slack.server.users[event["user"]]
    except KeyError:
        logger.debug("event {0} has no user".format(event))
        return

    return "\n".join(run_hook(server.hooks, "message", event, server))


def handle_channel_joined(event, server):
    temp = "".join(run_hook(server.hooks, "channel_joined", event, server))
    return temp


def handle_event(event, server):
    handler = event_handlers.get(event.get("type"))
    if handler:
        return handler(event, server)


event_handlers = {
    'message': handle_message,
    'channel_joined': handle_channel_joined
}


def run_hook(hooks, hook, *args):
    responses = []
    for hook in hooks.get(hook, []):
        try:
            h = hook(*args)
            if h:
                responses.append(h)
        except:
            logger.warning("Failed to run plugin {0}, module not loaded".format(hook))
            logger.warning("{0}".format(sys.exc_info()[0]))
            logger.warning("{0}".format(traceback.format_exc()))
    return responses


# Below is handlers specific to beepboop resources
def bb_on_message(ws, message):
    logger.debug('Beepboop msg type: {}, msg: {}'.format(
        message['type'], message))


def bb_on_auth_result(ws, message):
    logger.debug('Beepboop auth: {}'.format(json.dumps(message)))


def bb_on_error(ws, error):
    logger.debug('Beepboop error: {}'.format(str(error)))


def bb_on_close(ws):
    logger.debug('Beepboop closed')


def bb_on_open(ws):
    logger.debug('Beepboop opened')

bb_handlers = {
    'on_open': bb_on_open,
    'on_message': bb_on_message,
    'on_error': bb_on_error,
    'on_close': bb_on_close,
    'on_auth_result': bb_on_auth_result
}
