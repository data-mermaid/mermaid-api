#! /bin/python
"""
Script to check the ElasticBeanstalk Environment status and wait for `Ok`.
Usage: python wait_for_ok.py <my-eb-env-name> <commit_sha1>
"""
import sys
import boto3
import time
import datetime
import signal


class DeployError(Exception):
    pass


def handler(signum, frame):
    raise DeployError("Deploy timeout, there may be a problem with %s")


print(datetime.datetime.utcnow())

# Set a timeout signal for the deploy to fail
# 20 minutes
signal.signal(signal.SIGALRM, handler)
signal.alarm(20 * 60)

client = boto3.client('elasticbeanstalk')

env_name = sys.argv[1]
commit = sys.argv[2]

if env_name == '' or commit == '':
    raise ValueError('Both env name and commit sha need to be provided.')

new_label = commit
print('New Version: ', new_label)

current_status = client.describe_environment_health(
    EnvironmentName=env_name,
    AttributeNames=['HealthStatus'])['HealthStatus']

current_label = client.describe_environments(
    EnvironmentNames=[env_name])['Environments'][0]['VersionLabel']
print('Current Version: ', current_label)

count = 0
wait_interval = 5

# When the update starts, the version label will be the old one until
# the new one is deployed. Once it is successfully deployed, we need
# to wait for the status to be `Ok`. Therefore, `or` is suitable.
while current_label != new_label or current_status != 'Ok':
    time.sleep(wait_interval)
    count += 1
    sys.stdout.write('.')
    sys.stdout.flush()
    current_status = client.describe_environment_health(
        EnvironmentName=env_name, AttributeNames=['HealthStatus']
    )['HealthStatus']
    current_label = client.describe_environments(
        EnvironmentNames=[env_name])['Environments'][0]['VersionLabel']


signal.alarm(0)
print("\nEnv is up.")
