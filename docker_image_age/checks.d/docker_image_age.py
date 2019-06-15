# -*- coding: utf-8 -*-
#!/usr/bin/env python

from dateutil.parser import parse
import datetime
import docker

from datadog_checks.checks import AgentCheck
from datadog_checks.errors import CheckException

 # the special variable __version__ will be shown in the Agent status page
__author__ = "Misiu Pajor <misiu.pajor@datadoghq.com>"
__version__ = "1.1"


class DockerImageAge(AgentCheck):

    ''' get container id from container pid '''
    def get_cid_from_pid(self, pid):
        with open("/host/proc/%s/cgroup" % pid) as f:
            for l in f.readlines():
                parts = l.split("/")
                cid = parts[-1].strip()
                if len(cid) == 64:        
                    return cid

    ''' get container labels and metadata '''
    def get_container_metadata(self, cid):
        client = docker.from_env()
        container = client.containers.get(cid)
        image = client.images.get(container.attrs['Config']['Image'])
        tags = [
            'container_id:%s' % container.id,
            'container_name:%s' % container.name,
            'image_name:%s' % container.attrs['Config']['Image']
        ]

        for label_name, label_value in container.labels.items():
            # skip labels that are specific to datadog's auto discovery functionalites
            if "com.datadoghq.ad" in label_name:
                continue
            tags.append("{}:{}".format(label_name, label_value))

        return tags, image.attrs["Created"]

    def days_old(self, date):
        # @returns: diff in days between given date and now
        get_date_obj = parse(date)
        date_obj = get_date_obj.replace(tzinfo=None)
        diff = datetime.datetime.now() - date_obj
        return diff.days

    def check(self, instance):
        age = instance.get('age', 0) # age in days that we consider an image to be expired
        pid = instance.get('pid', False)
        debug = instance.get('debug', False)
        metric_name = instance.get('metric_name', 'docker.image_age')
        cid = self.get_cid_from_pid(pid)

        # retrieve custom tags and metadata for the discovered container 
        custom_tags, created_date = self.get_container_metadata(cid)
        # this will return days since the docker image was created
        day_old = self.days_old(created_date)
        # yield debug messages if debug is true
        if debug:
            self.log.info("Discovered: age: {}, pid: {}, debug: {}, metric_name: {}, cid: {} with custom tags: {} and image was created: {}"
                .format(age, pid, debug, metric_name, cid, custom_tags, created_date))
            self.log.info("container id/name: {} / {} is using image: {} that was built {} days ago"
                .format(custom_tags[0], custom_tags[1], custom_tags[2], day_old)) 

        # validate if image has expired according to the time in days we've set
        if int(day_old) >= int(age): # age is read from the label annotation set on the container
            # create a gauge metric with Datadog. metric_name is read from conf.yaml.
            self.gauge(metric_name, day_old, tags=custom_tags)
