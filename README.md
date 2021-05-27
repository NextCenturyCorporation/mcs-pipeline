# mcs-pipeline
MCS Project for running evaluations

This code runs scene files on EC2 machines.  Assumptions:
* There are some number of identical EC2 machines running and that they can be identified (details below)
* The EC2 machines have all the software running necessary
* The scene files are already on the machines
* You know how to run a single scene file on the remote the machine.   

### Python Environment Setup

From the mcs-pipeline root, create a virtual environment.

```bash
$ python3 -m venv --prompt pipeline venv
$ source venv/bin/activate
(pipeline) $ python -m pip install --upgrade pip setuptools wheel
(pipeline) $ python -m pip install -r requirements.txt
```

### Pre-requisites / setup 

* Working ssh.  You should have a pem that will allow you to do something like:

    <code>ssh -i ~/.ssh/pemfilename.pem username@ec2.2.amazon.com run_script.sh</code>
    
* secrets file, containing the pemfilename and the username.  Copy from pipeline/secrets_template.py 
to pipeline/secrets.py and fill it in.  Do not add to github.
* AWS credentials file.  This should be in the file ~/.aws/credentials.  This will allow you to 
use [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) to get 
EC2 machines.  
* Add the following to your ~/.ssh/config:   <code>StrictHostKeyChecking accept-new</code>
This will allow the EC2 machines to be called without you agreeing to accept them 
manually.

###  Logical Steps

* See what machines are running.  Within the code you can look for specific 
types of machines (like 'p2.xlarge', the default) or a location ('us-east-1'). 
It would be pretty easy to get it to look for tags. 
* Get a list of the scenes to run
* Create a thread pool of size of the number of machines
* In each thread:
  * Get the next scene to run 
  * Call a TA1-performer specific class to run the scene
  * On failure, add the scene back to the list of scenes to run

### Scene Running Class

The class that runs a single scene on an EC2 machine is TA1-performer specific.  
The general idea is that it:
* clears out any directories, as necessary
* copies the scene file to the appropriate directory
* runs the scene
* determines if there was an error

### Usage

Here is an example of running the MESS code.  Warning:  It's not very pretty, but 
we're going to use mess_tasks_runner.py as if it were an interactive tool.  

* Have a running EC2 machine that has the MESS code and the tasks on it, or a small number
* Open mess_task_runner.py in your editor of choice
* Go to the bottom of the file and comment out all the code below getTasks and run it.
* You should see something that looks like:
<pre>2021-03-01 17:16:22,782 main         INFO     Starting runtasks
2021-03-01 17:16:23,017 main         INFO     Number of machines 1
2021-03-01 17:16:23,017 main         INFO     Machines available:  ['ec2-18-206-232-67.compute-1.amazonaws.com']
2021-03-01 17:16:23,020 main         INFO     Number of tasks: 7220
2021-03-01 17:16:23,020 main         INFO     Tasks ['delta_0017_41.json', 'delta_001.....
</pre>
* Start the X Server and verify that it is running:
  * Uncomment the line <code>run_tasks.runXStartup()</code>
  * Run mess_task_runner.py
  * Recomment line
  * Wait 30 seconds 
  * Uncomment the line <code>run_tasks.runCheckXorg()</code>
  * Run mess_task_runner.py
  * Recomment line
  * The result of the above should look like:
<pre>
2021-03-01 17:25:05,148 main         INFO     Sending the following command: ['ssh', '-i', '~/.ssh/clarkdorman-keypair.pem', 'ubuntu@ec2-18-206-232-67.compute-1.amazonaws.com', 'ps auxwww | grep Xorg']
2021-03-01 17:25:05,919 main         INFO     Output: root      3818  0.4  0.0 264508 45724 tty2     Ssl+ 22:24   0:00 /usr/lib/xorg/Xorg -noreset +extension GLX +extension RANDR +extension RENDER -config /tmp/tmpdu2so5p9 :0
2021-03-01 17:25:05,919 main         INFO     Output: ubuntu    3918  0.0  0.0  13316  3228 ?        Ss   22:25   0:00 bash -c ps auxwww | grep Xorg
2021-03-01 17:25:05,919 main         INFO     Output: ubuntu    3920  0.0  0.0  14860  1016 ?        S    22:25   0:00 grep Xorg
2021-03-01 17:25:05,920 main         INFO     Return_code 0
</pre>
* Run a trivial test:
  * This code uses mcs_test.py which starts a controller and runs for 10 steps.  If this 
  is not on the EC2 machine, you will need some other trivial code.  
  * Uncomment the line <code>run_tasks.run_test()</code>
  * Run mess_task_runner.py and re-comment.  
  * Output should look like:
<pre>
2021-03-01 17:31:13,858 main         INFO     Sending the following command: ['ssh', '-i', '~/.ssh/clarkdorman-keypair.pem', 'ubuntu@ec2-18-206-232-67.compute-1.amazonaws.com', 'cd /home/ubuntu/ai2thor-docker && python3 mcs_test.py']
2021-03-01 17:31:17,309 main         INFO     Output: Found path: /home/ubuntu/MCS-AI2-THOR-Unity-App-v0.3.6.2.x86_64
2021-03-01 17:31:17,328 main         INFO     Output: Mono path[0] = '/home/ubuntu/MCS-AI2-THOR-Unity-App-v0.3.6.2_Data/Managed'
2021-03-01 17:31:17,328 main         INFO     Output: Mono config path = '/home/ubuntu/MCS-AI2-THOR-Unity-App-v0.3.6.2_Data/Mono/etc'
2021-03-01 17:31:17,503 main         INFO     Output: Preloaded 'ScreenSelector.so'
2021-03-01 17:31:17,513 main         INFO     Output: Display 0 '0': 1024x768 (primary device).
2021-03-01 17:31:17,559 main         INFO     Output: Logging to /home/ubuntu/.config/unity3d/CACI with the Allen Institute for Artificial Intelligence/MCS-AI2-THOR/Player.log
2021-03-01 17:31:23,718 main         INFO     Output: Image saved to /home/ubuntu/output_image_0.jpg
....
2021-03-01 17:31:23,719 main         INFO     Output: Image saved to /home/ubuntu/output_image_9.jpg
2021-03-01 17:31:23,861 main         INFO     Return_code 0
</pre>
* Try a small run:
  * Copy over an mcs_config.yaml that does not write to the bucket.  Create the mcs_config.yaml in 
  this directory
  * Modify pipeline/mess_config_change.py to make sure that it is looking at the right file locally
  * Uncomment the <code>run_tasks.change_mcs_config()</code> line
  * Run mess_task_runner.py
  * Recomment the line
  * Create a short list of scene files or use <code>tasks_single_tasks.txt</code>.  Set mess_task_runner to use 
  that list of scene files (TASK_FILE_PATH)
  * Uncomment the line <code>run_tasks.runTasks()</code>
  * Run mess_task_runner.py
* Big run:
  * Start lots of machines (~120 or so)
  * Same as the small run, following the same basic steps, one at a time: 
    * Start the X server on each by uncommenting that line and running.  Since this does not  
    run a thread per machine, this might take a couple of minutes
    * Copy over mcs_config.yaml.  Make sure to put in all the information, set 
    the AWS keys, make sure bucket and directory is correct, correct metadata level etc.  Uncomment 
    that line and run.  Again, not parallelized (i.e. thread per machine) so takes a couple 
    of minutes.  
    * Make a file with the correct list of tasks and set the TASK_FILE_PATH to point to it
    * Run the tasks

### Logs

Logs are written into a subdirectory called logs/.   There is one large log file and 
many machine-specific logs, one per machine.  The information is the same, but 
the one large log file can have many machines writing to it at once, so it's 
hard to parse sometimes.  

## Acknowledgements

This material is based upon work supported by the Defense Advanced Research Projects Agency (DARPA) and Naval Information Warfare Center, Pacific (NIWC Pacific) under Contract No. N6600119C4030. Any opinions, findings and conclusions or recommendations expressed in this material are those of the author(s) and do not necessarily reflect the views of the DARPA or NIWC Pacific.