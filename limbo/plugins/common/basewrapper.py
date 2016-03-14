import os
import time
import re

from pytz import timezone


class BaseWrapper(object):
    def __init__(self):
        if not os.environ.get('SD_AUTH_TOKEN'):
            raise Exception('SD_AUTH_TOKEN is missing from environment')
        self.token = os.environ.get('SD_AUTH_TOKEN')
        self.timezone = timezone(os.environ.get('TIMEZONE', 'Europe/London'))

    @classmethod
    def clean_parsing(cls, string):
        reg = '<http://((-?\w+-?\.?)+)\|(-?\w+-?\.?)+>'
        match = re.search(reg, string)

        if match:
            clean_string = match.group(1)
            string = string.replace(string[match.start():match.end()], clean_string)
        return string

    def find_name(self, _id, services, devices):
        for s in services:
            if _id == s['_id']:
                return s['name']
        for d in devices:
            if _id == d['_id']:
                return d['name']
        return 'No name'

    def find_id(self, name, services, devices):
        for s in services:
            if name == s['name']:
                return s['_id']
        for d in devices:
            if name == d['name']:
                return d['_id']

    def get_data(self, data, names=None):
        """Inputs the data from the metrics endpoints and returns
        the node that has contains the data + names of the metrics."""

        if not names:
            names = []
        for d in data:
            if d.get('data') or d.get('data') == []:
                names.append(d.get('name'))
                return d, names
            else:
                names.append(d.get('name'))
                return self.get_data(d.get('tree'), names)

    def extract_unit(self, device):
        units = device.get('units', '')
        if not units:
            units = device.get('unit', '')
        return units

    def online_status(self, lastpayload):
        if not lastpayload:
            return 'Unknown'
        diff = time.time() - lastpayload['sec']
        if diff < 180:
            return 'Online'
        else:
            return 'Last online {} minutes ago'.format(diff/60)

    def metric_filter(self, metrics, filter=None):
        """from a list of metrics ie ['cpuStats', 'CPUs', 'usr'] it constructs
        a dictionary that can be sent to the metrics endpoint for consumption"""

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
