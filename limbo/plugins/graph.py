"""{
    "title": "graph <metrics> for <name>",
    "text": "Here you can graph any of the available metrics for a device. `metrics` need to be separated by spaces like this `cpuStats CPUs usr` and the expression is case sensitive.",
    "mrkdwn_in": ["text"],
    "color": "#E8A824"
}"""

import os
import json
import re
import io
import time
from datetime import timedelta
from datetime import datetime

from serverdensity.wrapper import Metrics
from serverdensity.wrapper import Device

from matplotlib.ticker import MultipleLocator
from matplotlib.dates import AutoDateLocator
from matplotlib.dates import AutoDateFormatter
from matplotlib import pyplot as plt
import numpy as np

from slacker import Slacker

from limbo.plugins.common.basewrapper import BaseWrapper

COLOR = "#E8A824"
COMMANDS = ['graph']


class Wrapper(BaseWrapper):
    def __init__(self, msg, server):
        super(Wrapper, self).__init__()
        self.metrics = Metrics(self.token)
        self.device = Device(self.token)
        self.server = server
        self.msg = msg

    def results_of(self, metrics, name, period):
        result = self.get_metrics(metrics, name, period)
        return result

    def create_graph(self, device):

        # 400 and 200 pixels.
        ticks = 4
        width = 8
        height = 3.55

        dpi = 100
        bgcolor = '#f3f6f6'

        font = {
            'size': 10,
            'family': 'Arial'
        }
        plt.rc('font', **font)

        # size of figure and setting background color
        fig = plt.gcf()
        fig.set_size_inches(width, height)
        fig.set_facecolor(bgcolor)

        # axis color, no ticks and bottom line in grey color.
        ax = plt.axes(axisbg=bgcolor, frameon=True)
        ax.xaxis.set_ticks_position('none')
        ax.spines['bottom'].set_color('#aabcc2')
        ax.yaxis.set_ticks_position('none')

        # removing all but bottom spines
        for key, sp in ax.spines.items():
            if key != 'bottom':
                sp.set_visible(False)

        # setting amounts of ticks on y axis
        yloc = plt.MaxNLocator(ticks)
        ax.yaxis.set_major_locator(yloc)


        x_no_ticks = 8
        # Deciding how many ticks we want on the graph
        locator = AutoDateLocator(maxticks=x_no_ticks)
        formatter = AutoDateFormatter(locator)
        # Formatter always chooses the most granular since we have granular dates
        # either change format or round dates depending on how granular
        # we want them to be for different date ranges.
        formatter.scaled[1/(24.*60.)] = '%d/%m %H:%M'

        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)

        # turns off small ticks
        plt.tick_params(axis='x',
                        which='both',
                        bottom='on',
                        top='off',
                        pad=10)
        # Can't seem to set label color differently, changing tick_params color changes labels.
        ax.xaxis.label.set_color('#FFFFFF')

        # setting dates in x-axis automatically triggers use of AutoDateLocator
        x = [datetime.fromtimestamp(point['x']) for point in device['data']]
        y = [point['y'] for point in device['data']]
        plt.plot(x, y, color='#e4794e', linewidth=2)

        # pick values for y-axis
        y_ticks_values = np.array([point['y'] for point in device['data']])
        y_ticks = np.linspace(y_ticks_values.min(), y_ticks_values.max(), ticks)
        y_ticks = np.round(y_ticks, decimals=2)

        plt.yticks(y_ticks, [str(val) + device.get('unit') for val in y_ticks])
        # plt.ylim(ymin=0.1)  # Only show values of a certain threshold.

        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf,
                    format='png',
                    facecolor=fig.get_facecolor(),
                    dpi=dpi)
        buf.seek(0)
        filename = 'graph-{}.png'.format(int(time.time()))
        with io.open(filename, 'wb') as f:
            f.write(buf.read())
        return filename

    def get_metrics(self, metrics, name, period):
        devices = self.device.list()
        _id = self.find_id(name, [], devices)
        if not _id:
            return 'I couldn\'t find your device.'

        metrics_names = metrics.split('.')
        _, filter = self.metric_filter(metrics_names)

        now = datetime.now()
        past = now - timedelta(minutes=240)

        metrics_data = self.metrics.get(_id, past, now, filter)
        device, names = self.get_data(metrics_data)
        if not device.get('data'):
            return 'Could not find any data for these metrics'
        # creates file
        slack = Slacker(os.environ.get('SLACK_TOKEN'))
        slack.chat.post_message(
            self.msg['channel'],
            'Preparing the graphs for you this very moment',
            as_user=self.server.slack.server.username
        )

        filename = self.create_graph(device)

        attachment = [
            {
                'text': ('I brought you a graph for {} for the device `{}`'.format(' '.join(names), name) +
                         '\nComing up in just a sec.'),
                'mrkdwn_in': ['text']
            }
        ]

        slack.chat.post_message(
            self.msg['channel'],
            '',
            attachments=attachment,
            as_user=self.server.slack.server.username
        )

        # uploads and sends the graph to channel
        file_response = slack.files.upload(
            filename,
            filename='{}.png'.format(name),
            channels=self.msg['channel']
        )
        # Deletes the graph file after upload so it doesn't litter the container
        os.remove(filename)

        return None # We're sending information in function itself this time

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
            'text': 'Look I found a shiny graph for you!'
        }

        server.slack.post_message(
            msg['channel'],
            '',
            as_user=server.slack.server.username,
            **kwargs)
    elif results is None:
        return None
    else:
        return results
