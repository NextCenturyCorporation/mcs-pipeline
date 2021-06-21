import cv2
import numpy as np
from PIL import Image
import machine_common_sense as mcs
import os
import time 

def reject_outliers(data, m=2):
    return abs(data - np.mean(data)) < m * np.std(data)

def get_support_coords(img):
    src = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    src_gray = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(src_gray,100,200,5)
    tmp = Image.fromarray(edges)

    tmp = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    contours, hierarchy = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    max_area = 0
    for c in contours:
        hull = cv2.convexHull(c)
        hullx = hull[:,0,0]
        hully = hull[:,0,1]
        rect = cv2.minAreaRect(c)
        box = cv2.boxPoints(rect)
        box = np.int0(box)
        width = box[:,0].max() - box[:,0].min()
        area2 = (hullx.max()-hullx.min())*(hully.max()-hully.min())
        if (area2 > max_area) and (width < 500):
            max_area = area2
            max_contour = c
        
    hull = cv2.convexHull(max_contour)
    if np.std(hull[:,0,0]) > 50:
        new_hull = hull[reject_outliers(hull[:,0,0], m=1)]
    else:
        new_hull = hull
    final = cv2.drawContours(tmp, [new_hull], 0, (0,255,0), 2)

    minx = new_hull[:,0,0].min()
    maxx = new_hull[:,0,0].max()
    miny = new_hull[:,0,1].min()
    maxy = new_hull[:,0,1].max()
    return ((minx, maxx), (miny, maxy))



def compute_gravity_plausibility(images):
    # get the coordinates of the supporting box
    (minx, maxx), (miny, maxy) = get_support_coords(images[0])
    # compute the location of the pole
    crop = np.array(images[25])[:60,:]
    crop2 = cv2.copyMakeBorder(crop, 5, 5, 0, 0, cv2.BORDER_CONSTANT)

    edges = cv2.Canny(cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY),20,100,5)
    edges2 = cv2.Canny(cv2.cvtColor(crop2, cv2.COLOR_RGB2GRAY),20,100,5)

    # compute COM of the pole via contours
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    min_c = 10000
    max_c = 0
    for c in contours:
        if c[:,0,0].min() < min_c:
            min_c = c[:,0,0].min()
        if c[:,0,0].max() > max_c:
            max_c = c[:,0,0].max()

    edges2[:, :min_c] = 0
    edges2[:,(max_c+1):] = 0
    edges2[6:64:,(min_c+1):max_c] = 0

    contours, hierarchy = cv2.findContours(edges2, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    max_area = 0
    for c in contours:
        hull = cv2.convexHull(c)
        hull[:,0,1] -= 5

    midpoint = (hull[:,0,0].max() - hull[:,0,0].min())/2 + hull[:,0,0].min()

    # check whether or not the object will be supported by the support box
    if midpoint > maxx:
        supported = False
    elif midpoint < minx:
        supported = False
    else:
        supported = True

    #compute whether or not theres is a box on the ground at end of scene via edge detection
    start_edges = cv2.Canny(cv2.cvtColor(np.asarray(images[0]), cv2.COLOR_RGB2GRAY),100,200,5)
    finish_edges = cv2.Canny(cv2.cvtColor(np.asarray(images[-1]), cv2.COLOR_RGB2GRAY),100,200,5)
    diff_edges = (finish_edges - start_edges)[(miny+5):]

    contours, hierarch  = cv2.findContours(diff_edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    max_area = 0
    for c in contours:
        #area = cv2.contourArea(c)
        hull = cv2.convexHull(c)
        hullx = hull[:,0,0]
        hully = hull[:,0,1]
        area2 = (hullx.max()-hullx.min())*(hully.max()-hully.min())
        if (area2 > max_area):
            max_area = area2
    if max_area > 1000:
        on_ground = True
    else:
        on_ground = False
    if (not supported) and on_ground:
        plausible = True
    elif (not supported) and (not on_ground):
        plausible = False
    elif supported and on_ground:
        plausible = False
    elif supported and (not on_ground):
        plausible = True

    return plausible


def run_gravity_scene(json_path, controller, base_path="~/logs", num_steps=60):
    scene_data, status = mcs.load_scene_json_file(json_path)
    scene_data["history_dir"] = f"{base_path}/log.json"
    output = controller.start_scene(scene_data)

    images = []
    images.append(output.image_list[0])
    for step in range(num_steps):
        output = controller.step("Pass")
        images.append(output.image_list[0])
        if step < (num_steps-1):
            controller.make_step_prediction(choice="plausible", confidence=1)
        else:
            plausible = compute_gravity_plausibility(images)
            if plausible:
                controller.make_step_prediction(choice="plausible", confidence=1)
                choice="plausible"
            else:
                controller.make_step_prediction(choice="implausible", confidence=1)
                choice="implausible"
    controller.end_scene(choice=choice,confidence=1)

    return plausible


if __name__ == '__main__':
    print("starting controller")
    unity_app_file_path = "/home/ubuntu/MCS-AI2-THOR-Unity-App-v0.3.8.x86_64"
    controller = mcs.create_controller(unity_app_file_path)
    # assumes all the steps are 60...can change this if this is not the case at test
    NUMSTEPS = 60
    time.sleep( 2)
    print("started controller")
    time.sleep(2)
    dir = "/home/ubuntu/scenes/validation/"
    time.sleep(2)
    for filename in os.listdir(dir):
        if filename.endswith(".json"):
            print(f"Running scene: {filename}")
            run_gravity_scene(dir+filename, controller, num_steps=NUMSTEPS)
            print("finished scene")

