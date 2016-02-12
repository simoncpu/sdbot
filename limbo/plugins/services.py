"""{
    "title": "services <command> <name> (<period>)",
    "text": "You can get more info about your services through commands such as `find`, `status` or `value`",
    "mrkdwn_in": ["text"],
    "color": "#F9F19A"
}"""

import json
import requests
import re

from datetime import timedelta
from datetime import datetime

from serverdensity.wrapper import Service
from serverdensity.wrapper import Metrics
from serverdensity.wrapper import ServiceStatus
from limbo.plugins.common.basewrapper import BaseWrapper

COMMANDS = ['status', 'value']
BASEURL = 'https://api.serverdensity.io/'


class Wrapper(BaseWrapper):
    def __init__(self, msg, server):
        super(Wrapper, self).__init__()
        self.service = Service(self.token)
        self.metrics = Metrics(self.token)
        self.status = ServiceStatus(self.token)
        self.server = server
        self.msg = msg

    def results_of(self, command, name, period):
        if command == 'value':
            result = self.get_value(name)
        elif command == 'status':
            result = self.get_status(name)
        return result

    def get_value(self, name):
        services = self.service.list()
        _id = self.find_id(name, services, [])
        if not _id:
            return 'I couldn\'t find your service'
        service = self.service.view(_id)
        locations = service['checkLocations']
        all_results = []
        for location in locations:
            filtered = {'time': {location: 'all'}}
            now = datetime.now()
            past30 = now - timedelta(minutes=35)

            metrics = self.metrics.get(_id, past30, now, filtered)
            service = metrics[0]['tree'][0]
            data = service['data']

            latest = '{}s'.format(round(data[-1]['y'], 3))
            avg = '{}s'.format(round(sum([point['y'] for point in data])/len(data), 3))

            result = {
                'title': service['name'],
                'color': '#F9F19A',
                'fields': [
                    {
                        'title': '30 Minute Average',
                        'value': avg,
                        'short': True
                    },
                    {
                        'title': 'Latest Value',
                        'value': latest,
                        'short': True
                    }
                ]
            }
            all_results.append(result)

        return all_results

    def real_name(self, _id, nodes):
        for node in nodes:
            if _id == node['id']:
                return node['name']

    def get_status(self, name):
        services = self.service.list()
        _id = self.find_id(name, services, [])
        if not _id:
            return 'I couldn\'t find your service'
        nodes = requests.get(BASEURL + 'service-monitor/nodes', params={'token': self.token})
        statuses = self.status.location(_id)

        all_results = []
        for status in statuses:

            result = {
                'title': self.real_name(status['location'], nodes.json()),
                'color': '#F9F19A',
                'fields': [
                    {
                        'title': 'Round Trip Time',
                        'value': '{}s'.format(round(status['rtt'], 3)),
                        'short': True
                    },
                    {
                        'title': 'Status of Location',
                        'value': status['status'],
                        'short': True
                    },
                    {
                        'title': 'Response Time',
                        'value': '{}s'.format(round(status['time'], 3)),
                        'short': True
                    },
                    {
                        'title': 'Status Code',
                        'value': status['code'],
                        'short': True
                    }
                ]
            }
            all_results.append(result)
        return all_results

def on_message(msg, server):
    text = msg.get("text", "")
    match = re.findall(r"sdbot services (\b\w+\b)\s?(\b\w+\b)?\s?(\b\w+\b)?", text)
    if not match:
        return
    command, name, period = match[0]

    if command not in COMMANDS:
        text = ('I\'m sorry, but couldn\'t quite understand you there, perhaps' +
                'you could try one of these commands `find`, `status`, `value`')

        return text

    api = Wrapper(msg, server)
    results = api.results_of(command, name, period)
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