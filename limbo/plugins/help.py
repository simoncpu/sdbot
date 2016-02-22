"""{
    "title": "help",
    "text": "We'll give you all the help you need!",
    "mrkdwn_in": ["text"],
    "color": "#71CADC"
}"""

import re
import logging
import json

logger = logging.getLogger(__name__)

def on_message(msg, server):
    text = msg.get("text", "")
    logger.debug(text)
    match = re.findall(r"^sdbot help ( .*)?", text)
    if not match:
        match = re.findall(r'^sdbot\s?$', text)
    if not match:
        return

    helptopic = match[0][1].strip()
    if helptopic:
        return server.hooks["extendedhelp"].get(helptopic,
                "No help found for {0}".format(helptopic))
    else:
        # if no plugin has a docstring, there's no help key
        helpdict = server.hooks.get("help", {})
        attachments = sorted([attach for attach in helpdict.values()])
        kwargs = {
            'attachments': json.dumps(attachments),
            'text': 'I know lots of commands, try one out!'
        }

        server.slack.post_message(
            msg['channel'],
            '',
            as_user=server.slack.server.username,
            **kwargs)

def on_channel_joined(msg, server):
    return "Thanks for inviting me to the channel. See what I can do for you by writing `sdbot help`"
