#
# Runs a single job on a single machine.  Must be extended by derived classes
#


class SingleTask:

    def __init__(self, machine_dns, json_file_name, log):
        """  Passed an EC2 machine name on AWS and a json filename,
        this runs a job on AWS."""

        self.machine_dns = machine_dns
        self.json_file_name = json_file_name
        self.log = log

    def process(self):
        raise NotImplementedError
