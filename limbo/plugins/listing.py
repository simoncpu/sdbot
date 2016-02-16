"""{
    "title": "list  <command>",
    "text": "You can list things like `open alerts`, `devices` or `services`. For each command there are more options, to see them write `sdbot list <command> help`",
    "mrkdwn_in": ["text"],
    "color": "#FFF000"
}"""
import re
import time
import json

from serverdensity.wrapper import Device
from serverdensity.wrapper import Service
from serverdensity.wrapper import Alert

from limbo.plugins.common.basewrapper import BaseWrapper

COMMANDS = ['open alerts', 'services', 'devices', 'help']
COLOR = '#FFF000'


class Wrapper(BaseWrapper):
    def __init__(self):
        super(Wrapper, self).__init__()
        self.device = Device(self.token)
        self.service = Service(self.token)
        self.alert = Alert(self.token)

    def results_of(self, command, typeof, name):
        if typeof == 'help':
            result = self.extra_help(command)
        elif command == 'open alerts':
            result = self.list_alerts(command, typeof, name)
        elif command == 'devices':
            result = self.get_devices(typeof)
        elif command == 'services':
            result = self.get_services(typeof)
        return result

    def get_services(self, number):
        services = self.service.list()
        if number:
            services = services[:int(number)]
        else:
            services = services[:5]

        http = [s for s in services if s['checkType'] == 'http']
        tcp = [s for s in services if s['checkType'] == 'tcp']

        slack_http = [{
            'text': '*Service Name*: {}'.format(service['name']),
            'color': COLOR,
            'mrkdwn_in': ['text'],
            'fields': [{
                    'title': 'Group',
                    'value': service.get('group') if service.get('group') else 'Ungrouped',
                    'short': True
                },
                {
                    'title': 'Type of check',
                    'value': service.get('checkType'),
                    'short': True
                },
                {
                    'title': 'Url',
                    'value': service.get('checkUrl'),
                    'short': True
                },
                {
                    'title': 'Method',
                    'value': service.get('checkMethod'),
                    'short': True
                },
                {
                    'title': 'Slow threshold',
                    'value': str(service.get('slowThreshold')) + 'ms',
                    'short': True
                }
            ]
        } for service in http]

        slack_tcp = [{
            'text': '*Service Name*: {}'.format(service['name']),
            'color': COLOR,
            'mrkdwn_in': ['text'],
            'fields': [{
                    'title': 'Group',
                    'value': service.get('group') if service.get('group') else 'Ungrouped',
                    'short': True
                },
                {
                    'title': 'Type of check',
                    'value': service.get('checkType'),
                    'short': True
                },
                {
                    'title': 'Host',
                    'value': service.get('host'),
                    'short': True
                },
                {
                    'title': 'Port',
                    'value': service.get('port'),
                    'short': True
                }
            ]
        } for service in tcp]
        return slack_tcp + slack_http

    def get_devices(self, number):
        devices = self.device.list()
        if number:
            devices = devices[:int(number)]
        else:
            devices = devices[:5]
        # list expression
        slack_formatting = [{
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
                }
            ]
        } for device in devices]
        return slack_formatting

    def extra_help(self, command):
        if command == 'open alerts':
            helpfile = [{
                'title': 'Open Alerts',
                'mrkdwn_in': ['text'],
                'text': ('The full command for `open alerts` is `open alerts' +
                         ' <type> <name>` where `type` is either a `device`' +
                         ', `service` or `group`. `name` is the name of that ' +
                         'entity. Both `type` and `name` is optional. If ' +
                         'none is used I will give you 5 alerts by default, ' +
                         'if you want all alerts write `list open alerts all` ' +
                         'instead.'),
                'color': COLOR
            }]
        elif command == 'devices':
            helpfile = [{
                'title': 'Devices',
                'mrkdwn_in': ['text'],
                'text': ('The full command for `devices` is `devices <number>`' +
                         ', if a number is not specified I will give you 5 ' +
                         'devices by default'),
                'color': COLOR
            }]
        elif command == 'services':
            helpfile = [{
                'title': 'Services',
                'mrkdwn_in': ['text'],
                'text': ('The full command for listing services is ' +
                         '`sdbot list services <number>`, if a number is not ' +
                         'specified I will give you 5 services by default'),
                'color': COLOR
            }]
        return helpfile

    def list_alerts(self, command, typeof, name):
        params = {
            'filter': {'fixed': False}
        }
        not_valid = ['group', 'all']

        if typeof and typeof not in not_valid:
            params['filter']['config.subjectType'] = typeof
        if typeof == 'group':
            params['filter']['subjectGroup'] = typeof

        services = self.service.list()
        devices = self.device.list()

        if name:
            _id = name if not name else self.find_id(name, services, devices)
            params['filter']['config.subjectId'] = _id

        if typeof == 'group':
            _id = ''

        results = self.alert.triggered(params=params)
        alerts = sorted(results, key=lambda alert: alert['config']['lastTriggeredAt']['sec'], reverse=True)
        if not typeof or name:
            alerts = alerts[:5]
        open_alerts = []
        for alert in alerts:
            field = alert['config']['fullName'].split(' > ')
            comparison = alert['config'].get('fullComparison') if alert['config'].get('fullComparison') else ''
            value = alert['config'].get('value') if alert['config'].get('value') else ''
            group = alert['config']['group'] if alert['config'].get('group') else 'Ungrouped'
            triggered_time = time.localtime(alert['config']['lastTriggeredAt']['sec'])

            _id = alert['config']['subjectId']
            name = self.find_name(_id, services, devices)
            attachment = {
                'title': '{}'.format(name),
                'text': '{} {} {}'.format(
                    field[1],
                    comparison,
                    value
                ),
                'color': COLOR,
                'fields': [
                    {
                        'title': 'Last triggered',
                        'value': time.strftime('%Y-%m-%d, %H:%M:%S', triggered_time)
                    },
                    {
                        'title': 'Group',
                        'value': group,
                        'short': True
                    }
                ]
            }
            open_alerts.append(attachment)
        if open_alerts:
            return open_alerts
        else:
            return 'I could not find any open alerts for you.'



def on_message(msg, server):
    text = msg.get("text", "")
    match = re.findall(r"sdbot list ((open)?\s?\b\w+\b)\s?(\b\w+\b)?\s?(\b\w+\b)?", text)
    if not match:
        return
    command, _, typeof, name = match[0]

    if command not in COMMANDS:

        text = ('I\'m sorry, but couldn\'t quite understand you there, perhaps' +
                ' you could try one of these commands `find`, `status`, `value` or `metrics`')
        import pdb; pdb.set_trace()
        return text

    api = Wrapper()
    results = api.results_of(command, typeof, name)
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
