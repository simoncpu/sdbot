"""{
    "title": "devices <command> (<metrics> for) <name>",
    "text": "You can get more info about your services through commands such as `find`, `value`, `available`",
    "mrkdwn_in": ["text"],
    "color": "#A3B0CA"
}"""
import re
import json
from datetime import datetime
from datetime import timedelta
from serverdensity.wrapper import Device
from serverdensity.wrapper import Metrics

from limbo.plugins.common.basewrapper import BaseWrapper

COMMANDS = ['find', 'value', 'available']


class Wrapper(BaseWrapper):
    def __init__(self):
        super(Wrapper, self).__init__()
        self.device = Device(self.token)
        self.metrics = Metrics(self.token)

    def results_of(self, command, metrics, name):
        if command == 'find':
            result = self.find_device(name)
        elif command == 'value':
            result = self.get_value(name, metrics)
        elif command == 'available':
            result = self.get_available(name)
        return result

    def find_device(self, name):
        results = self.device.list()

        if not name:
            msg = 'Here are all the devices that I found'
            device_list = "\n".join([device['name'] for device in results])
            result = msg + '\n```' + device_list + '```'
            return result

        # list expression
        devices = [{
            'text': '*Device Name*: {}'.format(device['name']),
            'color': '#A3B0CA',
            'mrkdwn_in': ['text'],
            'fields': [{
                    'title': 'Group',
                    'value': device.get('group') if device.get('group') else 'Ungrouped',
                    'short': True
                },
                {
                    'title': 'Provider',
                    'value': device.get('provider') if device.get('provider') else 'No provider',
                    'short': True
                },
                {
                    'title': 'Id',
                    'value': device.get('_id'),
                    'short': True
                }
            ]
        } for device in results if device['name'] == name]
        return devices

    def metric_filter(self, metrics, filter=None):
        metrics = list(metrics)
        if not filter:
            filter = {}
            filter[metrics.pop()] = 'all'
            return self.metric_filter(metrics, filter)
        else:
            try:
                metric = metrics.pop()
                dic = {metric: filter}
                return self.metric_filter(metrics, dic)
            except IndexError:
                return metrics, filter

    def get_data(self, data, names=None):
        if not names:
            names = []
        for d in data:
            if d.get('data') or d.get('data') == []:
                names.append(d.get('name'))
                return d, names
            else:
                names.append(d.get('name'))
                return self.get_data(d.get('tree'), names)

    def get_value(self, name, metrics):
        devices = self.device.list()
        _id = self.find_id(name, [], devices)
        if not _id:
            return 'I couldn\'t find your device'

        metrics = metrics.split(' ')
        _, filter = self.metric_filter(metrics)

        now = datetime.now()
        past30 = now - timedelta(minutes=35)

        metrics = self.metrics.get(_id, past30, now, filter)
        device, names = self.get_data(metrics)
        if not device.get('data'):
            return 'Could not find any data for these metrics'
        result = {
            'title': 'Device name: {}'.format(name),
            'text': ' > '.join(names),
            'color': '#F9F19A',
            'fields': [
                {
                    'title': 'Latest Value',
                    'value': '{}{}'.format(device['data'][-1]['y'], device.get('units', '')),
                    'short': True
                }
            ]
        }
        return [result]

    def flatten(self, lst):
        for dct in lst:
            key = dct["key"]
            if "tree" not in dct:
                yield [key]  # base case
            else:
                for result in self.flatten(dct["tree"]):  # recursive case
                    yield [key] + result

    def get_available(self, name):
        devices = self.device.list()
        _id = self.find_id(name, [], devices)

        now = datetime.now()
        past30 = now - timedelta(minutes=120)

        metrics = self.metrics.available(_id, past30, now)
        available = list(self.flatten(metrics))
        text = ''
        for a in available:
            text += ' > '.join(a) + '\n'
        text = 'Here are the metrics you can use\n' + '```' + text + '```'
        return text

def on_message(msg, server):
    text = msg.get("text", "")
    match = re.findall(r"sdbot devices (\b\w+\b)\s?((\s?\w+){1,3} for)?\s?(\b\w+\b)?", text)
    if not match:
        return

    command, unclean_metrics, _, name = match[0]
    metrics = unclean_metrics.split('for')[0].strip()
    if command not in COMMANDS:
        text = ('I\'m sorry, but couldn\'t quite understand you there, perhaps' +
                ' you could try one of these commands `find`, `value`' +
                ' or `available`')
        return text

    api = Wrapper()
    results = api.results_of(command, metrics, name)
    if isinstance(results, list):
        kwargs = {
            'attachments': json.dumps(results),
            'text': 'This is the device I found for you'
        }

        server.slack.post_message(
            msg['channel'],
            '',
            as_user=server.slack.server.username,
            **kwargs)
    else:
        return results
