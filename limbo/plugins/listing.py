"""{
    "title": "list  <command>  (<type>) (<name>)",
    "text": "You can list things like `open alerts`, `devices` or `services`. Type is either a `group`, `service` or a `device` [dev]",
    "mrkdwn_in": ["text"],
    "color": "#FFF000"
}"""
import re
import time
import json
import requests
from limbo.plugins.common.basewrapper import BaseWrapper

COMMANDS = ['open alerts', 'services', 'devices']
TOKEN = '8e252354ccecb6509421ced215b33770'
BASEURL = 'https://api.serverdensity.io/'


class Wrapper(BaseWrapper):
    def __init__(self):
        pass

    def results_of(self, command, typeof, name):
        if command == 'open alerts':
            result = self.list_alerts(command, typeof, name)
        elif command == 'devices':
            result = self.get_devices()
        elif command == 'services':
            result = self.available_metrics()
        return result

    def list_alerts(self, command, typeof, name):
        params = {
            'filter': {'fixed': False},
            'token': TOKEN
        }
        not_valid = ['group', 'all']

        if typeof and typeof not in not_valid:
            params['filter']['config.subjectType'] = typeof
        if typeof == 'group':
            params['filter']['subjectGroup'] = typeof

        services = requests.get(BASEURL + 'inventory/services?token=' + TOKEN)
        devices = requests.get(BASEURL + 'inventory/devices?token=' + TOKEN)

        if name:
            _id = name if not name else self.find_id(name, services.json(), devices.json())
            params['filter']['config.subjectId'] = _id

        if typeof == 'group':
            _id = ''

        params['filter'] = json.dumps(params['filter'])
        results = requests.get(BASEURL + 'alerts/triggered', params=params)
        alerts = sorted(results.json(), key=lambda alert: alert['config']['lastTriggeredAt']['sec'], reverse=True)
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
            name = self.find_name(_id, services.json(), devices.json())
            attachment = {
                'title': '{}'.format(name),
                'text': '{} {} {}'.format(
                    field[1],
                    comparison,
                    value
                ),
                'color': '#FFF000',
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
    command, _, typeof, id = match[0]

    if command not in COMMANDS:
        return 'I\'m sorry, but couldn\'t quite understand you there, perhaps you could try one of these commands `find`, `status`, `value` or `metrics`'

    api = Wrapper()
    results = api.results_of(command, typeof, id)
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
