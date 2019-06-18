# -*- coding: utf-8 -*-
#!/usr/bin/env python
import time
import re
import os
from datetime import datetime, time
from datadog_checks.checks import AgentCheck
from datadog_checks.errors import CheckException

__version__ = "1.0.0"
__author__ = "Misiu Pajor <misiu.pajor@datadoghq.com>" 

class FilesinFolderAtGivenTime(AgentCheck):

    def is_time_between(self, begin_time, end_time):
        check_time = datetime.now().time()
        if begin_time < end_time:
            return check_time >= begin_time and check_time <= end_time
        else: # crosses midnight
            return check_time >= begin_time or check_time <= end_time

    def count_files(self, path, regex):
        return len([f for f in os.listdir(path) if re.match(regex, f)])

    def check(self, instance):
        metric_name = instance.get('metric_name') # value is read from myintegration.yaml
        begin_time = instance.get('begin_time')
        end_time = instance.get('end_time')
        path = instance.get('path')
        regex = instance.get('regex')

        begin_time = tuple(map(int, begin_time.split(',')))
        begin_hour, begin_minute = begin_time
        end_time = tuple(map(int, end_time.split(',')))
        end_hour, end_minute = end_time

        if self.is_time_between(time(begin_hour, begin_minute), time(end_hour, end_minute)):
            print("Time is between given range: {} - {}. Continue to check if file: {} exist in path: {}".format(begin_time, end_time, regex, path))
            files_found = self.count_files(path, regex)
            self.gauge(metric_name, files_found, tags=['path:%s' % path, 'regex:%s' % regex])
