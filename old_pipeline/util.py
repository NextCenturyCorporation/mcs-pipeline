#
#  Utilities, in particular AWS things
#
# NOTE:
# 1.  Please set your ssh config to allow ssh commands without having accept
# the # fingerprint (known hosts).   # To do that, add the following command
# to your ~/.ssh/config:     StrictHostKeyChecking accept-new
#
# See:  https://unix.stackexchange.com/questions/33271/
#       how-to-avoid-ssh-asking-permission
#
# 2. Set your AWS credentials in ~/.aws/credentials.  This is needed to get
# the S3 buckets and AWS machines to use.
#

import os
import subprocess
from typing import List

import boto3
import psutil

from old_pipeline.secrets import Secrets

PEM_FILE = Secrets['PEM_FILE']
USERNAME = Secrets['USERNAME']

def get_s3_buckets():
    """ Look on AWS and get the list of buckets"""
    buckets = []
    s3 = boto3.resource('s3')
    for bucket in s3.buckets.all():
        buckets.append(bucket.name)
    return buckets


def get_aws_machines(
        instance_type: str = 'p2.xlarge',
        region: str = 'us-east-1',
        tag_name: str = 'Name',
        tag_value: str = ''
) -> List[str]:
    """ Look on AWS and determine all the machines that we have running.
    The assumption is that we are looking for machines
    of type machine_type.
    """

    ec2 = boto3.client('ec2', region_name=region)
    response = ec2.describe_instances(
        Filters=[
            {
                'Name': 'instance-state-name',
                'Values': ['running']
            },
            {
                'Name': f'tag:{tag_name}',
                'Values': [f'*{tag_value}*']
            },
            {
                'Name': 'instance-type',
                'Values': [instance_type]
            }
        ]
    )

    machines = [
        instance['PublicDnsName']
        for reservation in response['Reservations']
        for instance in reservation['Instances']
    ]

    return machines


def get_remote_user_info(machine_dns):
    """ The name of the remote user depends on the type of machine that is running.
    For ubuntu images, the username is 'ubuntu'. For Amazon, it is 'ec2-user'
    """
    return f"{USERNAME}@{machine_dns}"


def safe_log(log, intro, msg):
    """Try to log.  Make sure that we have a log,
     then make sure that we have a message.  If both, write it. """

    if log is None:
        return
    if msg is None:
        return

    stripped_msg = msg.strip()
    if len(stripped_msg) == 0:
        return

    log.info(intro + " " + stripped_msg)


def run_command_and_capture_output(commandList, log=None):
    """Run a command on the current machine.  The command
    can be something that runs locally (like 'ls') or
    an ssh call (like 'ssh -i <pem> ubuntu@machine ls').
    This captures the output and writes it to a log.  It
    does not return until the command is done. """
    process = subprocess.Popen(commandList,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               universal_newlines=True,
                               shell=True)

    safe_log(log, "", f"Sending the following command: {commandList}")

    while True:
        output = process.stdout.readline()
        safe_log(log, "Output:", f"{output}")
        return_code = process.poll()
        if return_code is not None:
            safe_log(log, "Return_code:", f"{return_code}")
            # Process has finished, read rest of the output
            for output in process.stdout.readlines():
                safe_log(log, "Output:", f"{output}")
            break
    return return_code


def run_command_and_return(commandList, log=None):
    """Run a command, disconnect from it, and return.  This is
    useful when the the command runs in the background (like
    'Xorg &').  If the command errors out or does not exist,
    no return is presented, you check to see if it is running."""
    subprocess.Popen(commandList, close_fds=True, shell=True)


def shell_run_command_remote(machine_dns, command, log=None):
    '''Run the command on the remote machine using ssh.'''
    userInfo = get_remote_user_info(machine_dns)
    process_command = ["ssh", "-i", PEM_FILE, userInfo, command]
    return_code = run_command_and_capture_output(process_command, log)
    return return_code


def shell_run_background_remote(machine_dns, command, log=None):
    userInfo = get_remote_user_info(machine_dns)

    # This is surprisingly difficult.  We need to run a command, then
    #  disconnect.
    # See:  https://unix.stackexchange.com/questions/572798/how-can-i-\
    # start-a-long-running-background-process-via-ssh-and-immediately-disc
    # Should probably be using python daemon command.
    cmd = f"ssh -i {PEM_FILE} {userInfo} {command} & sleep 20 && exit"
    log.info("Running command: " + cmd)
    return_code = os.system(cmd)
    return return_code


def docker_run_command(machine_dns, json_file_name_fullpath,
                       command, log=None):
    """ Running a command on a remote machine looks like :
            "ssh -i pem_file user@machine command"
        For ours, it looks like:
            "ssh -i pem_file user@machine docker run --privileged -v
            `pwd`:/data dockerimage python3 ta1_code /data/json_file"

        We are using volume mapping to make the json file available to
        the docker, by mapping the home directory on the instance to the /data
        directory in the docker.  That means that the docker image will see
        the file as /data/filename.  Similarly, when the docker image
        writes to the output (/data/output_file), we will need to strip
        off the /data and get output_file from the instance.
    """
    userInfo = get_remote_user_info(machine_dns)

    head, tail = os.path.split(json_file_name_fullpath)
    mapped_dir = "/data/"
    process_command = ["ssh", "-i", PEM_FILE, userInfo] + command
    return_code, output_file = run_command_and_capture_output(process_command,
                                                              log)

    # Strip the mapped dir from the output file to get the name of
    # the output file on the instance
    if output_file is not None:
        output_file = output_file.partition(mapped_dir)[2]
    return return_code, output_file


def copy_file_to_aws(machine_dns, file_name, log=None, remote_dir=""):
    head, tail = os.path.split(file_name)
    remote_user = get_remote_user_info(machine_dns)
    remote_location = remote_user + ":" + remote_dir + tail
    process_command = ['scp', '-i', PEM_FILE, file_name, remote_location]
    return_code = run_command_and_capture_output(process_command, log)
    return return_code


def copy_file_from_aws(machine_dns, file_name, log=None):
    ubuntu_machine_dns = get_remote_user_info(machine_dns) + ":" + file_name
    if log:
        log.info(f"Ubuntu command: {ubuntu_machine_dns}")
    process_command = ['scp', '-i', PEM_FILE, ubuntu_machine_dns, "."]
    return_code = run_command_and_capture_output(process_command, log)
    return return_code


def check_if_process_running(process_name, print_match=False):
    '''
    Check if there is any running process with a command line that matches
    the passed process_name.  psutil.process_iter returns Process objects.
    We look in the full command line.  Note that the commandline is a list,
    so you have to be careful with the match.

    Example:  you start a process with 'bash -s "while :; do sleep 1; done &"'
    The command line looks like:
           ['/bin/bash', '-c', 'while :; do sleep 1; done &']
    So, you cannot look for the entire passed command, just parts of it.
    '''
    process_name = process_name.lower()
    for proc in psutil.process_iter():
        cmd_line = [cmd.lower() for cmd in proc.cmdline()]
        if print_match:
            print(f"{cmd_line}")
        try:
            found = any(process_name in cmd for cmd in cmd_line)
            if found:
                if print_match:
                    print(proc.name())
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False
