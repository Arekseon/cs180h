import dlib, cv2, time, utils, mmap, sys, json
import utils, posix_ipc
from PIL import Image
import numpy as np

scale_x = utils.SCALE_DOWN
upsample_num = 1

predictor_path = "shape_predictor_68_face_landmarks.dat"
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(predictor_path)

focused_mod = False
focused_recs = []
focused_rec_delta = 0.2

use_Focus = True

author_process = "PROCESS_ONE"
process_two_name = "PROCESS_TWO"
SEND_POINTS_CODE = "sending_face_points"
RECEIVED_POINTS_CODE = "received_points"
LAST_MESSAGE = "LAST_MESSAGE"

def start_camera():
    cap = cv2.VideoCapture(1)
    return cap
   

def get_image_from_camera(cam):
    ret, frame = cam.read()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray,None,fx=scale_x, fy=scale_x, interpolation = cv2.INTER_CUBIC)
    width, height = gray.shape[:2]
    return gray, width, height

def kill_camera(cam):
    cam.release()
    

# Check if a point is inside a rectangle
def rect_contains(rect, point) :
   if point[0] < rect[0] :
      return False
   elif point[1] < rect[1] :
      return False
   elif point[0] > rect[2] :
      return False
   elif point[1] > rect[3] :
      return False
   return True

def sanitize_point(old_point,size):
   
   point_x = max(old_point[0], 0)
   point_x = min(point_x, size[1])
   point_y = max(old_point[1], 0)
   point_y = min(point_y, size[0])
   point = (point_x,point_y)
   return point

def get_faces_points(img):
    # cv2.imshow('image2',img)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()


    detected_faces = detector(img, upsample_num)
    focused_recs = []
    faces_points = []
    for k, d in enumerate(detected_faces):
        # print("Detection : Top: {} Right: {} Bottom: {} Left: {}".format(
        #      d.top(), d.right(), d.bottom(), d.left()))
        focused_recs.append({
            'left':     d.left(),
            'right':    d.right(),
            'bottom':   d.bottom(),
            'top':      d.top()
            })
        shape = predictor(img, d)
        points = []
        for i in xrange(0,68):
           point = (shape.part(i).x, shape.part(i).y)
           points.append(sanitize_point(point,img.shape))
        faces_points.append(points)
    return faces_points, focused_recs

def get_focused_faces_points(img, focused_recs, g_width, g_height):
    faces_found = []
    new_focused_recs = []
    for rec in focused_recs:

        # crop rectangle
        width = rec['right'] - rec['left']
        height = rec['top'] - rec['bottom']
        scaled_rec = {
            'left':     max(int(rec['left']     - width*focused_rec_delta), 0),
            'right':    min(int(rec['right']    + width*focused_rec_delta), g_width),
            'bottom':   min(int(rec['bottom']   - height*focused_rec_delta),g_height),
            'top':      max(int(rec['top']      + height*focused_rec_delta),0)
        }
        offset_x = scaled_rec['left']
        offset_y = scaled_rec['top']

        croped_img = img[scaled_rec['top']:scaled_rec['bottom'], scaled_rec['left']: scaled_rec['right']]

        # process croped image
        croped_face_points, new_local_focused_recs = get_faces_points(croped_img)
    
        # return global coordinates
        global_face_points = []
        for local_face in croped_face_points:
            global_face = []
            for local_point in local_face:
                global_point = (local_point[0] + offset_x, local_point[1]+ offset_y)
                global_face.append(global_point)
            global_face_points.append(global_face)

        global_new_focused_recs = []
        for local_focused_rec in new_local_focused_recs:
            global_rec = {
                'left':   local_focused_rec['left']   + offset_x,
                'right':  local_focused_rec['right']  + offset_x,
                'bottom': local_focused_rec['bottom'] + offset_y,
                'top':    local_focused_rec['left']   + offset_y
            }
            global_new_focused_recs.append(global_rec)
        return global_face_points, global_new_focused_recs
            





def process_image_get_points(cam, focused_recs, focused_mod):
    start_time = time.time()
    img, width, height = get_image_from_camera(cam)

    to_console = ("focused mode: {}".format(focused_mod)),
    if not focused_mod:
        points, focused_recs = get_faces_points(img)
    else:
        points, focused_recs = get_focused_faces_points(img, focused_recs, width, height)
    # global focused_mod
    if use_Focus:
        focused_mod = len(focused_recs)>0


    to_console += ("; frame fps is {}".format(int(1/(time.time() - start_time)))),
    meta = {
        'author': author_process,
        'receiver': process_two_name,
        'action': SEND_POINTS_CODE,
        'face_found':len(points)==1,
        'points':points,
        'width':width,
        'height':height
    }
    return meta, focused_recs, focused_mod, to_console

def create_shared_memory_and_semaphore():
    SHARED_MEMORY_NAME = utils.SHARED_MEMORY_NAME#"SHWIFTY_MEMORY"
    SHM_SIZE = utils.SHM_SIZE #4096
    SEMAPHORE_NAME = utils.SEMAPHORE_NAME #"SHWIFTY_SEMAPHORE"

    try:
        shared_memory = posix_ipc.SharedMemory(SHARED_MEMORY_NAME, posix_ipc.O_CREX, size=SHM_SIZE)
        semaphore     = posix_ipc.Semaphore(SEMAPHORE_NAME, posix_ipc.O_CREX)
    except :
        print("Looks like memory and/or semaphore haven't been released last time")
        print("no biggie, let me clean it up for you")
        clean_up(SHARED_MEMORY_NAME, SEMAPHORE_NAME)
        print("all clean, now let's try again")
        shared_memory = posix_ipc.SharedMemory(SHARED_MEMORY_NAME, posix_ipc.O_CREX, size=SHM_SIZE)
        semaphore     = posix_ipc.Semaphore(SEMAPHORE_NAME, posix_ipc.O_CREX)

    return shared_memory, semaphore

def unlink_shared_memort_and_semaphore(mapfile, shared_memory, semaphore):
    mapfile.close()
    shared_memory.unlink()
    semaphore.unlink()

def clean_up(SHARED_MEMORY_NAME, SEMAPHORE_NAME):
    try:
        posix_ipc.unlink_shared_memory(SHARED_MEMORY_NAME)
        posix_ipc.unlink_semaphore(SEMAPHORE_NAME)
    except:
        print ("memory or semaphore doesn't need cleanup")
    print ("\nAll clean!")

def wait_for_new_message(initial_message, mapfile, semaphore):
    message_i_just_read = initial_message
    while message_i_just_read == initial_message:
        semaphore.acquire()
        message_i_just_read = utils.read_from_memory(mapfile)
        semaphore.release()
        time.sleep(0.001)
    return json.loads(message_i_just_read)   


def wait_for_new_message2(mapfile, semaphore):
    new_message_found = False
    while not new_message_found:
        semaphore.acquire()
        message_i_just_read = utils.read_from_memory(mapfile)
        json_i_just_read = json_to_obj(message_i_just_read)
        if json_i_just_read['author'] == process_two_name and json_i_just_read['receiver'] == author_process:
            # message_to_send = {
            #     'author': author_process,
            #     'receiver': process_one_name,
            #     'action': reply_code
            # }
            # if last_message:
            #     message_to_send['action'] = LAST_MESSAGE
            # utils.write_to_memory(mapfile, message_to_send)
            new_message_found = True
        semaphore.release()
        time.sleep(0.001)
    return json_i_just_read

def json_to_obj(str):
    try:
        meta = json.loads(str)
    except:
        print("something wrong with json, exiting")
        print str
        exit()
    return meta


if __name__ == '__main__':
    try:
        shared_memory, semaphore = create_shared_memory_and_semaphore()

        mapfile = mmap.mmap(shared_memory.fd, shared_memory.size)
        shared_memory.close_fd()

        starting_message = {
            'author': author_process,
            'receiver': process_two_name,
            'action': utils.FIRST_HANDSHAKE
        }
        starting_message = json.dumps(starting_message)


        # starting_message = utils.FIRST_HANDSHAKE
        utils.write_to_memory(mapfile, starting_message)
        message_i_just_read = starting_message

        print("Waiting for second process")
        waiting_time = 0
        while message_i_just_read == starting_message:
            sys.stdout.write("\r{0}".format("."*waiting_time))
            sys.stdout.flush()
            semaphore.release()
            time.sleep(1)
            waiting_time+=1
            semaphore.acquire()
            message_i_just_read = utils.read_from_memory(mapfile)
        semaphore.release()

        print("")
        print("I feel second process is ready, let's roll")
        time.sleep(1)

        cam = start_camera()
        # meta, focused_recs, focused_mod, to_console = process_image_get_points(cam,[], False)
        # meta_json = json.dumps(meta)
        # utils.write_to_memory(mapfile, meta_json)
        # utils.write_to_memory(mapfile, utils.THIRD_HANDSHAKE)
        

        start_time = time.time()
        frame_counter = 0
        focused_mod = False
        focused_recs = []
        # message_i_just_wrote = utils.THIRD_HANDSHAKE
        while True:
            # answer = wait_for_new_message(message_i_just_wrote, mapfile, semaphore)
            answer = wait_for_new_message2(mapfile, semaphore)
            # answer = wait_for_new_message(meta_json, mapfile, semaphore)
            if answer['action'] == LAST_MESSAGE:
                break
            semaphore.acquire()
            meta, focused_recs, focused_mod, to_console = process_image_get_points(cam, focused_recs, focused_mod)
            meta_json = json.dumps(meta)
            utils.write_to_memory(mapfile, meta_json)
            semaphore.release()
            to_console = ("{}; frame_counter: {}".format(to_console, frame_counter))

            sys.stdout.write("\r{0}".format(to_console))
            sys.stdout.flush()
            # message_i_just_wrote = meta_json

            frame_counter+=1
            # print("_______________________________")


        print("")
        print("average fps: {}".format(frame_counter/(time.time() - start_time)))
        print("My job here is done")
        time.sleep(1)
        
        kill_camera(cam)
        print("Unlinking memory and semaphore")
        unlink_shared_memort_and_semaphore(mapfile, shared_memory, semaphore)

    finally:
        kill_camera(cam)
        # unlink_shared_memort_and_semaphore(mapfile, shared_memory, semaphore)