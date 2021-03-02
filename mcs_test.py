#
# A minimalist test for MCS.  It starts a controller, reads in a scene
# (randomly picked) and goes forward for 10 steps.   On each step,
# it saves an image
#
#
import machine_common_sense as mcs

directory = "/home/ubuntu/"
unity_app_file_path = directory + "MCS-AI2-THOR-Unity-App-v0.3.6.1.x86_64"
config_json_file_path = directory + "retrieval_goal-0005.json"

controller = mcs.create_controller(unity_app_file_path)

if controller is None:
    print("Controller is NONE. Problem initializaing AI2-THOR !!!")
    exit(1)

config_data, status = mcs.load_config_json_file(config_json_file_path)
output = controller.start_scene(config_data)

action = 'MoveAhead'

for x in range(0, 10):
    step_output = controller.step(action)
    image_list = step_output.image_list
    if len(image_list) == 1:
        image = image_list[0]
        filename = directory + "output_image_" + str(x) + ".jpg"
        image.save(filename)
        print(f"Image saved to {filename}")
    else:
        print(f"Size of image list {len(image_list)}")

controller.end_scene(None)
