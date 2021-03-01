#
#  Utilities, in particular AWS things
#
# NOTE:
# 1.  Please set your ssh config to allow ssh commands without having accept the fingerprint (known hosts).
# To do that, add the following command to your ~/.ssh/config:     StrictHostKeyChecking accept-new
#
# See:  https://unix.stackexchange.com/questions/33271/how-to-avoid-ssh-asking-permission
#
# 2. Set your AWS credentials in ~/.aws/credentials.  This is needed to get the S3 buckets and
# AWS machines to use.
#


import os
import subprocess
import time
from os import path

import boto3

from pipeline.secrets import Secrets

PEM_FILE = Secrets['PEM_FILE']
USERNAME = Secrets['USERNAME']


def getDateInFileFormat():
    """Get the date in a format like 2020-03-01, useful for creating files"""
    timeInFileFormat = time.strftime('%Y-%m-%d', time.localtime(time.time()))
    return timeInFileFormat


def getS3Buckets():
    """ Look on AWS and get the list of buckets"""
    buckets = []
    s3 = boto3.resource('s3')
    for bucket in s3.buckets.all():
        buckets.append(bucket.name)
    return buckets


# TODO:  Add ability to look for particular tags (key,value) because might have multiple sets of machines
def getAWSMachines(machine_type='p2.xlarge', location='us-east-1'):
    """ Look on AWS and determine all the machines that we have running AWS that we can use.
    The assumption is that we are looking for machines of type machine_type.
    """

    machines = []

    ec2 = boto3.client('ec2', region_name=location)
    response = ec2.describe_instances()
    reservations = response.get('Reservations')
    for reservation in reservations:
        instances = reservation.get('Instances')
        for instance in instances:
            instance_location = instance.get('Placement').get('AvailabilityZone')
            instance_type = instance.get('InstanceType')
            public_dns = instance.get('PublicDnsName')
            instance_status = instance.get('State').get('Code')
            # print(f"Machine:  {public_dns} {instance_location} {instance_type}")

            # Status 16 means running.
            if instance_status == 16:
                # Do not look for an exact match for location, because the desired location could be
                # us-east-1, but the actual location could be 'us-east-1b'.
                if location == "*" or instance_location.find(location) > -1:
                    if machine_type == "*" or instance_type == machine_type:
                        machines.append(public_dns)

    return machines


def getRemoteUserInfo(machine_dns):
    """ The name of the remote user depends on the type of machine that is running.
    For ubuntu images, the username is 'ubuntu'. For Amazon, it is 'ec2-user'
    """
    return f"{USERNAME}@{machine_dns}"


def runCommandAndCaptureOutput(commandList, log=None):
    process = subprocess.Popen(commandList,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               universal_newlines=True)

    output_file = None

    if log:
        log.info(f"Sending the following command: {commandList}")

    while True:
        output = process.stdout.readline()
        stripped = output.strip()
        if len(stripped) > 0:
            if log:
                log.info(f"Output: {stripped}")
        output_file_index = stripped.find("OUTPUT_FILE:")
        if output_file_index > 0:
            split_stripped = stripped.split(" ")
            if len(split_stripped) > 1:
                output_file = split_stripped[1]
        return_code = process.poll()
        if return_code is not None:
            if log:
                log.info(f"Return_code {return_code}")
            # Process has finished, read rest of the output
            for output in process.stdout.readlines():
                output = output.strip()
                if len(output) > 0:
                    if log:
                        log.info(f"Output: {output}")
            break
    return return_code, output_file


def shellRunCommand(machine_dns, command, log=None):
    '''Run the command on the remote machine using ssh.'''
    userInfo = getRemoteUserInfo(machine_dns)
    process_command = ["ssh", "-i", PEM_FILE, userInfo, command]
    return_code, _ = runCommandAndCaptureOutput(process_command, log)
    return return_code


def shellRunBackground(machine_dns, command, log=None):
    userInfo = getRemoteUserInfo(machine_dns)

    # This is surprisingly difficult.  We need to run a command, then disconnect.
    # See:  https://unix.stackexchange.com/questions/572798/how-can-i-start-a-long-running-background-process-via-ssh-and-immediately-disc
    # Should probably be using python daemon command.
    process_command = f"ssh -i {PEM_FILE} {userInfo} {command} & sleep 20 && exit"
    log.info("Running command: " + process_command)
    return_code = os.system(process_command)
    return return_code


def dockerRunCommand(machine_dns, json_file_name_fullpath, command, log=None):
    """ Running a command on a remote machine looks like :
            "ssh -i pem_file user@machine command"
        For ours, it looks like:
            "ssh -i pem_file user@machine docker run --privileged -v `pwd`:/data dockerimage python3 ta1_code /data/json_file"

        We are using volume mapping to make the json file available to the docker, by mapping
        the home directory on the instance to the /data directory in the docker.  That means that
        the docker image will see the file as /data/filename.  Similarly, when the docker image
        writes to the output (/data/output_file), we will need to strip off the /data and get
        output_file from the instance.
    """
    userInfo = getRemoteUserInfo(machine_dns)

    head, tail = os.path.split(json_file_name_fullpath)
    mapped_dir = "/data/"
    file_name_in_docker = mapped_dir + tail
    process_command = ["ssh", "-i", PEM_FILE, userInfo] + command
    return_code, output_file = runCommandAndCaptureOutput(process_command, log)

    # Strip the mapped dir from the output file to get the name of the output file on the instance
    if output_file is not None:
        output_file = output_file.partition(mapped_dir)[2]
    return return_code, output_file


def copyFileToAWS(machine_dns, file_name_fullpath, log=None, remote_dir=""):
    head, tail = path.split(file_name_fullpath)
    ubuntu_machine_dns = getRemoteUserInfo(machine_dns) + ":" + remote_dir + tail
    process_command = ['scp', '-i', PEM_FILE, file_name_fullpath, ubuntu_machine_dns]
    return_code, _ = runCommandAndCaptureOutput(process_command, log)
    return return_code


def copyFileFromAWS(machine_dns, file_name, log=None):
    ubuntu_machine_dns = getRemoteUserInfo(machine_dns) + ":" + file_name
    if log:
        log.info(f"Ubuntu command: {ubuntu_machine_dns}")
    process_command = ['scp', '-i', PEM_FILE, ubuntu_machine_dns, "."]
    return_code, _ = runCommandAndCaptureOutput(process_command, log)
    return return_code
