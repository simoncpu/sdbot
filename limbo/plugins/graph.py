"""{
    "title": "graph <metrics> for <name>",
    "text": "Here you can graph any of the available metrics for a device. `metrics` need to be separated by spaces like this `cpuStats CPUs usr` and the expression is case sensitive.",
    "mrkdwn_in": ["text"],
    "color": "#4E82C5"
}"""

import os
import os.path
import json
import re
from datetime import timedelta
from datetime import datetime

import pygal
from serverdensity.wrapper import Metrics
from serverdensity.wrapper import Device

from limbo.plugins.common.basewrapper import BaseWrapper

COLOR = "#4E82C5"
COMMANDS = ['graph']


class Wrapper(BaseWrapper):
    def __init__(self, msg, server):
        super(Wrapper, self).__init__()
        self.metrics = Metrics(self.token)
        self.device = Device(self.token)

    def results_of(self, metrics, name, period):
        result = self.get_metrics(metrics, name, period)
        return result

    def get_metrics(self, metrics, name, period):
        devices = self.device.list()
        _id = self.find_id(name, [], devices)
        if not _id:
            return 'I couldn\'t find your device.'

        metrics_names = metrics.split(' ')
        _, filter = self.metric_filter(metrics_names)

        now = datetime.now()
        past = now - timedelta(minutes=240)

        metrics_data = self.metrics.get(_id, past, now, filter)
        device, names = self.get_data(metrics_data)
        if not device.get('data'):
            return 'Could not find any data for these metrics'

        data = device['data']

        dates = []
        values = []

        for i, point in enumerate(data):
            if not i % 10:
                dates.append(now.fromtimestamp(point['x']))
            values.append(point['y'])

        line_chart = pygal.Line(
            width=400,
            height=200,
            x_label_rotation=20,
            label_font_size=8)
        line_chart.title = metrics
        line_chart.x_labels = map(str, dates)
        line_chart.add('', values)
        path = os.path.join(os.getcwd(), 'plugins', 'temp', 'chart.png')
        line_chart.render_to_png(path)



def on_message(msg, server):
    text = msg.get("text", "")
    match = re.findall(r"sdbot graph ((\s?\w+){1,3} for)?\s?(\b\w+\b)\s?(.*)", text)
    if not match:
        return
    metrics, _, name, period = match[0]

    api = Wrapper(msg, server)
    results = api.results_of(metrics, name, period)
    if isinstance(results, list):
        kwargs = {
            'attachments': json.dumps(results),
            'text': 'This is the {} I found for you'.format(command)
        }

        server.slack.post_message(
            msg['channel'],
            '',
            as_user=server.slack.server.username,
            **kwargs)
    else:
        return results
