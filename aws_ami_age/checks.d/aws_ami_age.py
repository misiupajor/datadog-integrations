# -*- coding: utf-8 -*-
#!/usr/bin/env python

# ../conf.d/ami_age.d/conf.yaml
#init_config:
#
# instances:
#  - min_collection_interval: 300
#    metric_name: "aws.ami_age"
#    age: 14
#    debug: "false"

from dateutil.parser import parse
import datetime
import requests

from datadog_checks.checks import AgentCheck
from datadog_checks.errors import CheckException

# force a installation of boto3 is missing, as it is a core dependency for this integration to work.
try: import boto3
except ImportError:
    from pip._internal import main as pip
    pip(['install', '--user', 'boto3'])
    import boto3

 # the special variable __version__ will be shown in the Agent status page
__author__ = "Misiu Pajor <misiu.pajor@datadoghq.com>"
__version__ = "1.0.2"

class AmiAge(AgentCheck):

    # helper function to receive metadata for this instance
    def get_metadata(self, type):
        try:
            response = requests.get("http://169.254.169.254/latest/meta-data/{}".format(type))
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise CheckException("HTTP error caught: {}".format(e))
        except requests.exceptions.RequestException as e:
            raise CheckException("Connection error: {}".format(e))
        return response.text

    def days_old(self, date):
        # @returns: diff in days between given date and now
        get_date_obj = parse(date)
        date_obj = get_date_obj.replace(tzinfo=None)
        diff = datetime.datetime.now() - date_obj
        return diff.days

    def check(self, instance):
        age = instance.get('age', 14) # age in days that we consider an ami to be expired
        debug = instance.get('debug', 'false')
        metric_name = instance.get('metric_name', 'aws.ami_age')

        # get current available zone we're running on
        availability_zone = self.get_metadata("placement/availability-zone")[:-1]
        # get local instance id
        instance_id = self.get_metadata("instance-id")
        # get local ami image used
        ami_id = self.get_metadata("ami-id")


        ec2 = boto3.resource('ec2',
            region_name=availability_zone
            # if in developer mode
            #aws_access_key_id="<redacted>",
            #aws_secret_access_key="<redacted>"
        )
        # get image metadata
        image = ec2.Image(ami_id)

        # custom tags that will be populated to the metric we create
        custom_tags = [
            'instance_id:%s' % instance_id, # ec2 instance id
            'ami_id:%s' % image.image_id, # ami id the instance is using
            'ami_name:%s' % image.name # ami name
        ]
        # retrieve all the custom tags set in AWS on this ami (eg., systemid, team)
        if image.tags is not None:
            for tag in image.tags:
                custom_tags.append("{}:{}".format(tag['Key'], tag['Value']))

        # this will return days since this ami was created
        day_old = self.days_old(image.creation_date)

        # validate if this ami has expired according to the time in days we've set (age)
        if day_old > age: # age is read from this integrations conf.yaml, default is 14 days
            # ami has expired, let's notify Datadog about it.
            if debug == "true":
                self.log.info("Expired image: ''{}'' with creation date: {} is now: _{}_ days old.".format(
                    image.id, image.creation_date, day_old
                ))
            # create a gauge metric with Datadog. metric_name is read from conf.yaml.
            self.gauge(metric_name, day_old, tags=custom_tags)
