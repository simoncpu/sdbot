"""{
    "title": "devices <argument> <name>",
    "text": "You can get more info about your devices using arguments like `find`, `value`, `available` or `list`. To get more help about each argument, type `sdbot devices help`",
    "mrkdwn_in": ["text"],
    "color": "#E83880"
}"""
import re
import json
from datetime import datetime
from datetime import timedelta
from serverdensity.wrapper import Device
from serverdensity.wrapper import Metrics

from limbo.plugins.common.basewrapper import BaseWrapper

COMMANDS = ['find', 'value', 'available', 'list', 'help']
COLOR = '#E83880'


class Wrapper(BaseWrapper):
    def __init__(self, msg, server):
        super(Wrapper, self).__init__(msg, server)
        self.device = Device(self.token)
        self.metrics = Metrics(self.token)

    def results_of(self, command, metrics, name):
        if command == 'help' or name == 'help':
            result = self.extra_help(command)
        elif command == 'find':
            result = self.find_device(name)
        elif command == 'value':
            result = self.get_value(name, metrics)
        elif command == 'available':
            result = self.get_available(name)
        elif command == 'list':
            result = self.list_devices(name)
        return result

    def extra_help(self, command):
        help_command = {
            'value': {
                'title': 'Latest Value for a Device',
                'mrkdwn_in': ['text'],
                'text': ('To get the latest value for a device, type ' +
                         '`sdbot devices metric.here for deviceName`. ' +
                         'The metrics need to be separated by dots.'),
                'color': COLOR
            },
            'find': {
                'title': 'Find a Device',
                'mrkdwn_in': ['text'],
                'text': ('To find a device type ' +
                         '`sdbot devices find deviceName`. I can also accept regex for the argument `deviceName`. ' +
                         'For example `sdbot devices find 2$`.'),
                'color': COLOR
            },
            'list': {
                'title': 'List Devices',
                'mrkdwn_in': ['text'],
                'text': ('To get a list of your devices type, ' +
                         '`sdbot devices list <no>`. In this case `<no>` ' +
                         'a number. If you leave it out I will ' +
                         'list the first 5 devices.'),
                'color': COLOR
            },
            'available': {
                'title': 'Available Metrics',
                'mrkdwn_in': ['text'],
                'text': ('To get all the available metrics for a device, type ' +
                         '`sdbot devices available deviceName`. This will ' +
                         'display a list of metrics you can use for the command `devices value` or `graph`'),
                'color': COLOR
            }
        }

        if command == 'value':
            helptext = [help_command['value']]
        elif command == 'available':
            helptext = [help_command['available']]
        elif command == 'find':
            helptext = [help_command['find']]
        elif command == 'list':
            helptext = [help_command['list']]
        elif command == 'help':
            helptext = [attachment for attachment in help_command.values()]
        return helptext

    def _format_devices(self, devices):
        formatted = [{
            'text': '*Device Name*: {}'.format(device['name']),
            'color': COLOR,
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
                },
                {
                    'title': 'Online Status',
                    'value': self.online_status(device.get('lastPayloadAt', '')),
                    'short': True
                }
            ]
        } for device in devices]
        return formatted

    def list_devices(self, number):
        if number:
            try:
                number = number.strip()
                number = int(number)
            except ValueError:
                text = '{} is not a number, now is it. You see, it needs to be.'.format(number)
                return text
        devices = self.device.list()
        if number:
            devices_trunc = devices[:number]
        else:
            devices_trunc = devices[:5]

        return self._format_devices(devices_trunc)

    def find_device(self, name):
        devices = self.device.list()

        if not name:
            msg = 'Here are all the devices that I found'
            device_list = "\n".join([device['name'] for device in devices])
            result = msg + '\n```' + device_list + '```'
            return result

        devices = [device for device in devices if re.search(name, device['name'])]
        formatted_devices = self._format_devices(devices)

        if len(formatted_devices) == 0:
            formatted_devices = [{
                'text': 'Sorry, I couldn\'t find a device with that name :(',
                'color': COLOR
            }]

        return formatted_devices

    def get_value(self, name, metrics):
        devices = self.device.list()
        _id = self.find_id(name, [], devices)
        if not _id:
            return 'I couldn\'t find your device'

        if not metrics:
            return ('You have not included any metrics the right way to do it ' +
                    'is give metrics this way `sdbot devices value memory.memSwapFree for {}`'.format(name))
        metrics = metrics.split('.')
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
            'color': COLOR,
            'fields': [
                {
                    'title': 'Latest Value',
                    'value': '{}{}'.format(device['data'][-1]['y'], self.extract_unit(device)),
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

        if not _id:
            return 'It looks like there is no device named `{}`'.format(name)
        now = datetime.now()
        past30 = now - timedelta(minutes=120)

        metrics = self.metrics.available(_id, past30, now)
        available = list(self.flatten(metrics))
        text = ''
        for a in available:
            text += '.'.join(a) + '\n'
        if text:
            text = 'Here are the metrics you can use\n' + '```' + text + '```'
        else:
            text = 'Your device seems to be offline, it doesn\'t contain any metrics in the last 2 hours'
        return text

def on_message(msg, server):
    text = msg.get("text", "")
    text = Wrapper.clean_parsing(text)

    match = re.findall(r"^[sS][dD][bB]ot devices? (\b\w+\b)\s?((\.?[\/0-9A-Za-z.\s\[\]\-()_]+){1,3} for)?\s?(.*)?", text)

    if not match:
        return

    command, unclean_metrics, _, name = match[0]
    name = name.strip()
    if not name and command not in ['list', 'help']:
        text = ('It looks like you forgot to add a name, ' +
                'try `sdbot devices {} {} deviceName`'.format(command, unclean_metrics))
        return text

    metrics = unclean_metrics.split('for')[0].strip()
    if command not in COMMANDS:
        text = ('I\'m sorry, but couldn\'t quite understand you there, perhaps' +
                ' you could try one of these commands `find`, `value`, ' +
                '`available` or `list`')
        return text

    api = Wrapper(msg, server)
    results = api.results_of(command, metrics, name)
    if isinstance(results, list):
        kwargs = {
            'attachments': json.dumps(results),
            'text': 'This is what I got for you'
        }

        server.slack.post_message(
            msg['channel'],
            '',
            as_user=server.slack.server.username,
            **kwargs)
    else:
        return results
