#!/bin/env python
#-*- coding:utf-8 -*-

__author__ = 'Sun Wei'

import urllib2
import json
import socket
import time
import commands
import requests

GAUGE = 'GAUGE'
COUNTER = 'COUNTER'
falcon_client = "http://127.0.0.1:1988/v1/push"

class NginxStats:
    def __init__(self, stats_url='http://127.0.0.1:9527/status.json'):
        self.stats_url = stats_url
        self.ip = socket.gethostname()
        self.step = 60
        self.metric = "nginx.%s"

    def stats(self):
        self.timestamp = int(time.time())
        response = urllib2.urlopen(self.stats_url)
        jsonDecode = json.load(response)
        data = []
        #handle nginx total stats
        data.extend(self.metricTotal(jsonDecode))
        #handle api.klabchina stats
        data.extend(self.metricByGroup(jsonDecode,'api.klabchina'))
        #handle assets.klabchina stats
        data.extend(self.metricByGroup(jsonDecode,'assets.klabchina'))
        #handle cms.klabchina stat
        data.extend(self.metricByGroup(jsonDecode, 'cms.klabchina'))
        return data

    def metricTotal(self, jsonDecode):
        data = []
        if jsonDecode.has_key('connections'):
            connections = jsonDecode['connections']
            keys = [ 'writing', 'idle' , 'reading', 'active']
            for key in keys:
                counterKey = 'connections.' + key
                data.append({
                    'metric': self.metric % counterKey,
                    'endpoint': self.ip,
                    'tags': 'program=nginx,key=%s' % counterKey,
                    'timestamp': self.timestamp,
                    'step': self.step,
                    'value': connections.get(key, 0),
                    'counterType': 'GAUGE'
                 })

        if jsonDecode.has_key('requests'):
            requests = jsonDecode['requests']
            keys = ['total','current']
            for key in keys:
                counterKey = 'requests.' + key
                data.append({
                    'metric': self.metric % counterKey,
                    'endpoint': self.ip,
                    'tags': 'program=nginx,key=%s' % counterKey,
                    'timestamp': self.timestamp,
                    'step': self.step,
                    'value': int(requests[key]),
                    'counterType': 'GAUGE'
                })
        return data

    def metricByGroup(self, jsonDecode, groupName):
        data = []
        if not jsonDecode.has_key(groupName):
            return data
        groupData = jsonDecode[groupName]
        keys = { 'upstream_resp_time_sum':[], 'status':['5xx', '4xx', '3xx', '2xx', '1xx'],
                     'upstream_requests_total':[],'request_times':['0-100', '100-500', '500-1000', '1000-inf'],'requests_total':[] }
        for (k,v) in keys.items():
            if len(v) == 0:
                counterKey = '%s.%s' % (groupName, k)
                value = 0
                if groupData.has_key(k):
                    value = float(groupData[k])
                data.append({
                    'metric': self.metric % counterKey,
                    'endpoint': self.ip,
                    'tags': 'program=nginx,key=%s' % counterKey,
                    'timestamp': self.timestamp,
                    'step': self.step,
                    'value': value,
                    'counterType': 'GAUGE'
                })
            else:
                for ko in v:
                    counterKey = '%s.%s.%s' % (groupName, k, ko)
                    if groupData.has_key(k) and groupData[k].has_key(ko):
                        value = float(groupData[k][ko])
                        data.append({
                            'metric': self.metric % counterKey,
                            'endpoint': self.ip,
                            'tags': 'program=nginx,key=%s' % counterKey,
                            'timestamp': self.timestamp,
                            'step': self.step,
                            'value': value,
                            'counterType': 'GAUGE'
                        })
        return data




def main():
    statsData = NginxStats().stats()
    return statsData


if __name__ == '__main__':
    proc = commands.getoutput(''' ps -ef|grep 'nginx-monitor.py'|grep -v grep|wc -l ''')
    if int(proc) < 3:
        r = requests.post("http://127.0.0.1:1988/v1/push", data=json.dumps(main()))
        print r.text