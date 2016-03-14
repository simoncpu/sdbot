"""{
    "title": "alerts <argument>",
    "text": "The `list` argument will display the open alerts. For instructions on how to use this, type `sdbot alerts help`.",
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

COMMANDS = ['list', 'help']
COLOR = '#3EB891'


class Wrapper(BaseWrapper):
    def __init__(self):
        super(Wrapper, self).__init__()
        self.alert = Alert(self.token)
        self.device = Device(self.token)
        self.service = Service(self.token)

    def results_of(self, command, typeof, name):
        if typeof == 'help' or command == 'help':
            result = self.extra_help(command)
        elif command == 'list':
            result = self.list_alerts(command, typeof, name)
        return result

    def extra_help(self, command):
        help_command = {
            'list': {
                'title': 'List Open Alerts',
                'mrkdwn_in': ['text'],
                'text': ('The full command for alerts is `sdbot alerts list' +
                         ' <type> <name>`, where `type` is either the word `device`' +
                         ', `service` or `group`. The argument `name` corresponds to the ' +
                         'name of that entity. Both `type` and `name` are optional. If ' +
                         'none is used I will give you 5 alerts by default. ' +
                         'If you want all alerts write, type `sdbot alerts list all`.'),
                'color': COLOR
            }
        }

        if command == 'list':
            helptext = [help_command['list']]
        elif command == 'help':
            helptext = [attachment for attachment in help_command.values()]
        return helptext, ''

    def _is_mongoId(self, _id):
        if len(_id) == 24:
            return True
        return False

    def list_alerts(self, command, typeof, name):
        params = {
            'filter': {'fixed': False}
        }
        valid = ['service', 'device']
        if typeof and typeof in valid:
            params['filter']['config.subjectType'] = typeof
        elif typeof == 'group':
            params['filter']['subjectGroup'] = name
        elif typeof in ['all', '']:
            pass  # don't need to do anything
        else:
            text = 'Instead of `{}` you should have used `group`, `service`, `device` or `all`'.format(typeof), ''
            return text

        services = self.service.list()
        devices = self.device.list()

        if name and typeof != 'group':
            _id = name if not name else self.find_id(name, services, devices)
            params['filter']['config.subjectId'] = _id

        results = self.alert.triggered(params=params)
        alerts = sorted(results, key=lambda alert: alert['config']['lastTriggeredAt']['sec'], reverse=True)
        if not (typeof or name):
            # When making a standard `alerts list` we want to give a limited amount of alerts.
            stripped_alerts = alerts[:5]
        else:
            # we want to keep the entire list here
            stripped_alerts = alerts
        open_alerts = []

        for alert in stripped_alerts:
            field = alert['config']['fullName'].split(' > ')
            comparison = alert['config'].get('fullComparison', '')
            value = '{}{}'.format(alert['config'].get('value', ''), alert['config'].get('units', ''))
            group = alert['config'].get('group', 'Ungrouped')
            triggered_time = time.localtime(alert['config']['lastTriggeredAt']['sec'])

            _id = alert['config']['subjectId']
            if self._is_mongoId(_id):
                name = self.find_name(_id, services, devices)
                name = '{}: {}'.format(alert['config']['subjectType'].title(), name)
            else:
                name = 'Group: {}'.format(_id)

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
                    # waiting on backend bugfix sd-2190
                    # {
                    #     'title': 'Group',
                    #     'value': group,
                    #     'short': True
                    # }
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
    text = Wrapper.clean_parsing(text)

    match = re.findall(r"^[sS][dD][bB]ot alerts (\b\w+\b)\s?(\b\w+\b)?\s?(\b\w+\b)?", text)
    if not match:
        return
    command, typeof, name = match[0]
    if command not in COMMANDS:

        text = ('I\'m sorry, but couldn\'t quite understand you there, perhaps' +
                ' you could try `list`, use `sdbot list help` to get more info.')
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
