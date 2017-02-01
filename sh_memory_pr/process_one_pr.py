import pygame.camera, pygame.image
import dlib, cv2, time, utils, mmap, sys, json
import utils
import posix_ipc
from PIL import Image

scale_x = 0.2
upsample_num = 1

detector = dlib.get_frontal_face_detector()
predictor_path = "shape_predictor_68_face_landmarks.dat"
predictor = dlib.shape_predictor(predictor_path)





temp_img_file_bmp = "photo.bmp"
temp_img_file_jpeg = "photo_jpg"

def start_camera():
    pygame.camera.init()
    cam = pygame.camera.Camera(pygame.camera.list_cameras()[1])
    cam.start()
    return cam    

def get_image_from_camera(cam):
    return cam.get_image()

def kill_camera(cam):
    cam.stop()
    pygame.camera.quit()
    

def get_PIL_from_pygame(img):
    pygame.image.save(img, temp_img_file_bmp)
    # time.sleep(1)

    # im = Image.open(temp_img_file_bmp)
    # bg = Image.new("RGB", im.size, (255,255,255,255))
    # bg.paste(im,im)
    # bg.save(temp_img_file_jpeg)

    img = Image.open(temp_img_file_bmp)
    img.save(temp_img_file_jpeg,'jpeg')

    img_grey = cv2.imread(temp_img_file_jpeg, cv2.IMREAD_GRAYSCALE)    
    img_grey = cv2.resize(img_grey,None,fx=scale_x, fy=scale_x, interpolation = cv2.INTER_CUBIC)
    width, height = img_grey.shape[:2]
    return img_grey, width, height


def PIL_image_to_pygame(image):
    mode = image.mode
    size = image.size
    data = image.tostring()

    this_image = pygame.image.fromstring(data, size, mode)
    return this_image

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
    # time_point_0 = time.time()
    # detector = dlib.get_frontal_face_detector()
    # predictor_path = "shape_predictor_68_face_landmarks.dat"
    # predictor = dlib.shape_predictor(predictor_path)
    # print("time_point_0 in {}".format(time_point_0 - time.time()))

    


    # time_point_1 = time.time()
    detected_faces = detector(img, upsample_num)
    # print("time_point_1 in {}".format(time_point_1 - time.time()))
    

    # print("Number of faces detected: {}".format(len(detected_faces)))
    faces_points = []


    # time_point_4 = time.time()
    for k, d in enumerate(detected_faces):
        # print("Detection {}: Left: {} Top: {} Right: {} Bottom: {}".format(
        #    k, d.left(), d.top(), d.right(), d.bottom()))

        # time_point_2 = time.time()
        shape = predictor(img, d)
        # print("time_point_2 in {}".format(time_point_2 - time.time()))


        # time_point_3 = time.time()
        points = []
        for i in xrange(0,68):
           point = (shape.part(i).x, shape.part(i).y)
           points.append(sanitize_point(point,img.shape))
        faces_points.append(points)
        # print("time_point_3 in {}".format(time_point_3 - time.time()))

    # print("time_point_4 in {}".format(time_point_4 - time.time()))


    return faces_points

def process_image_get_points(cam):
    start_time = time.time()
    img = get_image_from_camera(cam)
    img = get_image_from_camera(cam)


    # time_point = time.time()
    # print("got image from camera in {}".format(time_point - start_time))
    img, width, height = get_PIL_from_pygame(img)
    # print("transformed image in {}".format(time.time() - time_point))



    # time_point = time.time()
    points =  get_faces_points(img)
    # print("found points in {}".format(time.time() - time_point))
    print("frame fps is {}".format(1/(time.time() - start_time))),
    meta = {
        'face_found':len(points)==1,
        'points':points,
        'width':width,
        'height':height
    }
    # print meta
    # print("face found: {}".format(len(points)))
    return meta

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
        s = "memory segment %s removed" % SHARED_MEMORY_NAME
        print (s)
    except:
        print ("memory doesn't need cleanup")
        
        
    try:
        posix_ipc.unlink_semaphore(SEMAPHORE_NAME)
        s = "semaphore %s removed" % SEMAPHORE_NAME
        print (s)
    except:
        print ("semaphore doesn't need cleanup")


    print ("\nAll clean!")

def wait_for_new_message(initial_message, mapfile, semaphore):
    message_i_just_read = initial_message
    while message_i_just_read == initial_message:
        semaphore.acquire()
        message_i_just_read = utils.read_from_memory(mapfile)
        if not message_i_just_read == initial_message:
            utils.write_to_memory(mapfile, utils.JOB_DONE)
        semaphore.release()

        time.sleep(0.001)
    return message_i_just_read   




if __name__ == '__main__':

    shared_memory, semaphore = create_shared_memory_and_semaphore()

    mapfile = mmap.mmap(shared_memory.fd, shared_memory.size)
    shared_memory.close_fd()

    starting_message = utils.FIRST_HANDSHAKE
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


    print("")
    print("I feel second process is ready, let's roll")
    time.sleep(1)

    cam = start_camera()
    meta = process_image_get_points(cam)
    meta_json = json.dumps(meta)
    utils.write_to_memory(mapfile, meta_json)
    semaphore.release()

    start_time = time.time()
    frame_counter = 0
    for i in xrange(utils.IMAGE_LOOP_COUNTER):
        wait_for_new_message(meta_json, mapfile, semaphore)
        semaphore.acquire()
        meta = process_image_get_points(cam)
        meta_json = json.dumps(meta)
        utils.write_to_memory(mapfile, meta_json)
        semaphore.release()
        print("frame_counter: {}".format(frame_counter))
        frame_counter+=1



    print("average fps: {}".format(utils.IMAGE_LOOP_COUNTER/(time.time() - start_time)))
    print("My job here is done")
    time.sleep(1)
    
    kill_camera(cam)
    print("Unlinking memory and semaphore")
    unlink_shared_memort_and_semaphore(mapfile, shared_memory, semaphore)