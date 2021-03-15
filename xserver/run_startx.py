#
#
# Start a headless xserver for a headless server.
#
#
import time
from x_server import startx

# This uses code from AI2THOR Docker that creates a xorg.conf based on the
# current GPU and then starts a headless Xorg in a new thread.

startx()

print(" Now going to sleep", flush=True)
while True:
    time.sleep(1)
