hide = """{
    "title": "list  <command>",
    "text": "You can list things like `open alerts`, `devices` or `services`. For each command there are more options, to see them write `sdbot list <command> help`",
    "mrkdwn_in": ["text"],
    "color": "#3EB891"
}"""
import re
import time
import json

from serverdensity.wrapper import Device
from serverdensity.wrapper import Service
from serverdensity.wrapper import Alert

from limbo.plugins.common.basewrapper import BaseWrapper

COMMANDS = ['open alerts', 'services', 'devices', 'help']
COLOR = '#3EB891'


class Wrapper(BaseWrapper):
    def __init__(self):
        super(Wrapper, self).__init__()
        self.device = Device(self.token)
        self.service = Service(self.token)
        self.alert = Alert(self.token)

    def results_of(self, command, typeof, name):
        if typeof == 'help' or command == 'help':
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
        if not number:
            message = 'Here are 5 services, if you want to see more than that you can, just do `sdbot list services <number>`'
        else:
            message = 'Here are all your {} services'.format(len(slack_tcp + slack_http))
        return slack_tcp + slack_http, message

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
                },
                {
                    'title': 'Online Status',
                    'value': self.online_status(device.get('lastPayloadAt', '')),
                    'short': True
                }
            ]
        } for device in devices]
        if not number:
            message = 'Here are 5 devices, if you want to see more than that you can, just do `sdbot list devices <number>`'
        else:
            message = 'Here are your devices'
        return slack_formatting, message

    def extra_help(self, command):
        help_command = {
            'open alerts': {
                'title': 'Open Alerts',
                'mrkdwn_in': ['text'],
                'text': ('The full command for `open alerts` is `open alerts' +
                         ' <type> <name>` where `type` is either a `device`' +
                         ', `service` or a `group`. `name` is the name of that ' +
                         'entity. Both `type` and `name` is optional. If ' +
                         'none is used I will give you 5 alerts by default, ' +
                         'if you want all alerts write `list open alerts all` ' +
                         'instead.'),
                'color': COLOR
            },
            'devices': {
                'title': 'Devices',
                'mrkdwn_in': ['text'],
                'text': ('The full command for `devices` is `devices <number>`' +
                         ', if a number is not specified I will give you 5 ' +
                         'devices by default'),
                'color': COLOR
            },
            'services': {
                'title': 'Services',
                'mrkdwn_in': ['text'],
                'text': ('The full command for listing services is ' +
                         '`sdbot list services <number>`, if a number is not ' +
                         'specified I will give you 5 services by default'),
                'color': COLOR
            }
        }

        if command == 'open alerts':
            helptext = [help_command['open alerts']]
        elif command == 'devices':
            helptext = [help_command['devices']]
        elif command == 'services':
            helptext = [help_command['services']]
        elif command == 'help':
            helptext = [attachment for attachment in help_command.values()]
        return helptext, ''

    def list_alerts(self, command, typeof, name):
        params = {
            'filter': {'fixed': False}
        }
        valid = ['service', 'device']
        if typeof and typeof in valid:
            params['filter']['config.subjectType'] = typeof
        elif typeof == 'group':
            params['filter']['subjectGroup'] = typeof
        else:
            text = 'Instead of `{}` you should have used `group`, `service`, `device` or `all`'.format(typeof), ''
            return text

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
            # When making a standard `list open alerts` we want to give a limited amount of alerts.
            stripped_alerts = alerts[:5]
        else:
            # we want to keep the entire list here
            stripped_alerts = alerts
        open_alerts = []
        for alert in stripped_alerts:
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
            if len(alerts) > len(stripped_alerts):
                message = ('You have {} open alerts but I\'m only showing the last {},'.format(len(alerts), len(stripped_alerts)) +
                           ' do `list open alerts all` to see all of them')
            else:
                message = 'Chop chop, you\'d better sort out these open alerts soon'
            return open_alerts, message
        else:
            return 'I could not find any open alerts for you.', ''



def on_message(msg, server):
    text = msg.get("text", "")
    return  # Code above is currently deprecated, revisit to implement alias for listing

    match = re.findall(r"^sdbot list ((open)?\s?\b\w+\b)\s?(\b\w+\b)?\s?(\b\w+\b)?", text)
    if not match:
        return
    command, _, typeof, name = match[0]

    if command not in COMMANDS:

        text = ('I\'m sorry, but couldn\'t quite understand you there, perhaps' +
                ' you could try one of these commands `find`, `status`, `value` or `metrics`')
        return text

    api = Wrapper()
    results, message = api.results_of(command, typeof, name)
    if isinstance(results, list):
        kwargs = {
            'attachments': json.dumps(results),
            'text': message
        }

        server.slack.post_message(
            msg['channel'],
            '',
            as_user=server.slack.server.username,
            **kwargs)
    else:
        return results
