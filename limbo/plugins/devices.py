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
import requests
from limbo.plugins.common.basewrapper import BaseWrapper

BASEURL = 'https://api.serverdensity.io/'


COMMANDS = ['find', 'value', 'available']
TOKEN = '8e252354ccecb6509421ced215b33770'


class Wrapper(BaseWrapper):
    def __init__(self):
        pass

    def results_of(self, command, metrics, name):
        if command == 'find':
            result = self.find_device(name)
        elif command == 'value':
            result = self.get_value(name, metrics)
        elif command == 'available':
            result = self.get_available(name)
        return result

    def find_device(self, name):
        results = requests.get(BASEURL + 'inventory/devices?token=' + TOKEN)
        in_json = results.json()
        if not name:
            msg = 'Here are all the devices that I found'
            device_list = "\n".join([device['name'] for device in in_json])
            result = msg + '\n```' + device_list + '```'
            return result

        # list expression
        devices = [{
            'text': '**Device Name**: {}'.format(device['name']),
            'color': '#A3B0CA',
            'mrkdwn_in': ['text'],
            'fields': [{
                    'title': 'Group',
                    'value': device.get('group') if device.get('group') else 'Ungrouped',
                    'short': True
                },
                {
                    'title': 'Provider',
                    'value': device.get('provider', 'None'),
                    'short': True
                },
                {
                    'title': 'Id',
                    'value': device.get('_id'),
                    'short': True
                }
            ]
        } for device in in_json if device['name'] == name]
        return devices

    def metric_filter(self, metrics, filter=None):
        metrics = list(metrics)
        if not filter:
            filter = {}
            filter[metrics.pop()] = 'ALL'
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
            if d.get('data'):
                names.append(d.get('name'))
                return d, names
            else:
                names.append(d.get('name'))
                return self.get_data(d.get('tree'), names)

    def get_value(self, name, metrics):
        devices = requests.get(BASEURL + 'inventory/devices?token=' + TOKEN)
        _id = self.find_id(name, [], devices.json())
        if not _id:
            return 'I couldn\'t find your device'

        metrics = metrics.split(' ')
        _, filter = self.metric_filter(metrics)

        now = datetime.now()
        past30 = now - timedelta(minutes=35)
        params = {
            'start': past30.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'end': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'token': TOKEN,
            'filter': json.dumps(filter)
        }

        metrics = requests.get(BASEURL + 'metrics/graphs/' + _id,
                               params=params)
        device, names = self.get_data(metrics.json())
        result = {
            'title': name,
            'text': ' > '.join(names),
            'color': '#F9F19A',
            'fields': [
                {
                    'title': 'Latest Value',
                    'value': '{}{}'.format(device['data'][-1]['y'], device['unit']),
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
        devices = requests.get(BASEURL + 'inventory/devices?token=' + TOKEN)
        _id = self.find_id(name, [], devices.json())

        now = datetime.now()
        past30 = now - timedelta(minutes=120)

        params = {
            'token': TOKEN,
            'start': past30.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'end': now.strftime('%Y-%m-%dT%H:%M:%SZ')
        }

        metrics = requests.get(BASEURL + 'metrics/definitions/' + _id,
            params=params)
        available = list(self.flatten(metrics.json()))
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
