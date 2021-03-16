import json
import random

from pipeline import util


def get_first_machine():
    machines = util.get_aws_machines(machine_type='*', location='*')
    machines.sort()
    if len(machines) > 0:
        return machines[0]


def test_copy_file_to_aws():
    temp_name = "file_" + str(random.randint(0, 999999))
    temp_filename = "/tmp/" + temp_name
    with open(temp_filename, 'w') as f:
        f.write("blah\n")
    print(f"Copying filename to AWS: {temp_name} ")
    success = util.copy_file_to_aws(get_first_machine(), temp_filename)
    print(f"Success: {success}")
    return temp_name


def test_copy_file_from_aws():
    temp_name = test_copy_file_to_aws()
    print(f"Copying filename from AWS: {temp_name} ")
    success = util.copy_file_from_aws(get_first_machine(), temp_name)
    print(f"Success: {success}")


def test_print_command():
    print("\n---test_printCommand---")
    tmpname = test_copy_file_to_aws()
    success = util.docker_run_command(get_first_machine(), tmpname)
    print(f"Success: {success}")


def test_get_s3_buckets():
    print("\n---test_getS3Buckets---")
    buckets = util.get_s3_buckets()
    print(f"Buckets:  {buckets}")


def test_get_aws_machines():
    print("\n---test_getAWSMachines---")
    machines = util.get_aws_machines(machine_type='t2.micro')
    print("Current t2.micro Machines: ")
    print(json.dumps(machines, indent=4, default=str))

    machines = util.get_aws_machines(machine_type='*', location='us-east-1')
    print("All Current Machines: ")
    print(json.dumps(machines, indent=4, default=str))

    machines = util.get_aws_machines(machine_type='p2.xlarge',
                                   location='us-east-1')
    print("p2.xlarge Current Machines: ")
    print(json.dumps(machines, indent=4, default=str))


def run_test_mess():
    machine = "ec2-52-205-76-200.compute-1.amazonaws.com"
    run_command = "cd /home/ubuntu/mess_original_code/mess_final/ && " + \
                  " ./runall.sh"
    util.shell_run_command(machine, run_command, None)
