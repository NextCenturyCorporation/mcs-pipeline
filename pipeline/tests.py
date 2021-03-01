import json
import random

from pipeline import util
from pipeline.util import copyFileToAWS, copyFileFromAWS


def getFirstMachine():
    machines = util.getAWSMachines(machine_type='*', location='*')
    machines.sort()
    if len(machines) > 0:
        return machines[0]


def test_copyFileToAWS():
    temp_name = "file_" + str(random.randint(0, 999999))
    temp_filename = "/tmp/" + temp_name
    with open(temp_filename, 'w') as f:
        f.write("blah\n")
    print(f"Copying filename to AWS: {temp_name} ")
    success = copyFileToAWS(getFirstMachine(), temp_filename)
    print(f"Success: {success}")
    return temp_name


def test_copyFileFromAWS():
    temp_name = test_copyFileToAWS()
    print(f"Copying filename from AWS: {temp_name} ")
    success = copyFileFromAWS(getFirstMachine(), temp_name)
    print(f"Success: {success}")


def test_printCommand():
    print("\n---test_printCommand---")
    tmpname = test_copyFileToAWS()
    success = util.dockerRunCommand(getFirstMachine(), tmpname)
    print(f"Success: {success}")


def test_getS3Buckets():
    print("\n---test_getS3Buckets---")
    buckets = util.getS3Buckets()
    print(f"Buckets:  {buckets}")


def test_getAWSMachines():
    print("\n---test_getAWSMachines---")
    machines = util.getAWSMachines(machine_type='t2.micro')
    print(f"Current t2.micro Machines:")
    print(json.dumps(machines, indent=4, default=str))

    machines = util.getAWSMachines(machine_type='*', location='us-east-1')
    print(f"All Current Machines:")
    print(json.dumps(machines, indent=4, default=str))

    machines = util.getAWSMachines(machine_type='p2.xlarge', location='us-east-1')
    print(f"p2.xlarge Current Machines:")
    print(json.dumps(machines, indent=4, default=str))


def run_test_mess():
    machine = "ec2-52-205-76-200.compute-1.amazonaws.com"
    run_command = "cd /home/ubuntu/mess_original_code/mess_final/ && ./runall.sh"
    util.shellRunCommand(machine, run_command, None)

# test_copyFileToAWS()
# test_copyFileFromAWS()
# test_printCommand()
# test_getS3Buckets()
# test_getAWSMachines()
# run_test_mess()
