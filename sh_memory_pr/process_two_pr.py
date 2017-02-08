import utils, time, posix_ipc, mmap, json, cv2
import numpy as np
def access_shared_memory_and_semaphore():
    SHARED_MEMORY_NAME = utils.SHARED_MEMORY_NAME 	#"SHWIFTY_MEMORY"
    SEMAPHORE_NAME = utils.SEMAPHORE_NAME 			#"SHWIFTY_SEMAPHORE"

    try:
        shared_memory = posix_ipc.SharedMemory(SHARED_MEMORY_NAME)
        semaphore = posix_ipc.Semaphore(SEMAPHORE_NAME)
    except:
        print("looks like there is no memory created yet")
        exit()
    return shared_memory, semaphore

def unlink_shared_memort_and_semaphore(mapfile, shared_memory, semaphore):
    mapfile.close()
    shared_memory.unlink()
    semaphore.unlink()

def wait_for_new_message(initial_message, mapfile, semaphore):
    message_i_just_read = initial_message
    while message_i_just_read == initial_message:
        semaphore.acquire()
        message_i_just_read = utils.read_from_memory(mapfile)
        if not message_i_just_read == initial_message:
            utils.write_to_memory(mapfile, utils.READY_FOR_NEXT)
        semaphore.release()

        time.sleep(0.001)
    return message_i_just_read    

def write_last_message(mapfile, semaphore):
    semaphore.acquire()
    utils.write_to_memory(mapfile, utils.JOB_DONE)
    semaphore.release()    

def draw_point(img, p, color ) :
    cv2.circle (img, p, 1, (0,0,255), -1)

def json_to_obj(str):
    try:
        meta = json.loads(str)
    except:
        print("something wrong with json, exiting")
        print message_i_just_read
        exit()
    return meta

def draw_points_on_blank(meta):
    blank_image = np.zeros((int(meta['width']), int(meta['height']), 3), np.uint8)
    for faces in meta['points']: 
        for p in faces:
            draw_point(blank_image, (p[0],p[1]), (0,0,255))
    # cv2.imshow('image',blank_image)
    # cv2.waitKey(1)
    return blank_image

def resize_back(blank_image):
    return cv2.resize(blank_image,None,fx=(1/utils.SCALE_DOWN), fy=(1/utils.SCALE_DOWN), interpolation = cv2.INTER_CUBIC)
    

def draw_face_vector_on_blank(meta, blank_image):
    size = blank_image.shape
    
    image_points = np.array([
                            meta['points'][0][33],# (359, 391),     # Nose tip
                            meta['points'][0][8],# (399, 561),     # Chin
                            meta['points'][0][36],# (337, 297),     # Left eye left corner
                            meta['points'][0][45],# (513, 301),     # Right eye right corne
                            meta['points'][0][48],# (345, 465),     # Left Mouth corner
                            meta['points'][0][54]# (453, 469)      # Right mouth corner
                        ], dtype="double")


    model_points = np.array([
                            (0.0, 0.0, 0.0),             # Nose tip
                            (0.0, -330.0, -65.0),        # Chin
                            (-225.0, 170.0, -135.0),     # Left eye left corner
                            (225.0, 170.0, -135.0),      # Right eye right corne
                            (-150.0, -150.0, -125.0),    # Left Mouth corner
                            (150.0, -150.0, -125.0)      # Right mouth corner
                         
                        ])


    focal_length = size[1]
    center = (size[1]/2, size[0]/2)
    # focal_length = meta['width']
    # center = (meta['width']/2, meta['height']/2)

    camera_matrix = np.array(
                             [[focal_length, 0, center[0]],
                             [0, focal_length, center[1]],
                             [0, 0, 1]], dtype = "double"
                             )

    dist_coeffs = np.zeros((4,1)) # Assuming no lens distortion
    (success, rotation_vector, translation_vector) = cv2.solvePnP(model_points, image_points, camera_matrix, dist_coeffs)#, flags=cv2.CV_ITERATIVE)


    (nose_end_point2D, jacobian) = cv2.projectPoints(np.array([(0.0, 0.0, 1000.0)]), rotation_vector, translation_vector, camera_matrix, dist_coeffs)
    # for p in image_points:
    #     cv2.circle(blank_image, (int(p[0]), int(p[1])), 3, (0,0,255), -1)

    p1 = ( int(image_points[0][0]), int(image_points[0][1]))
    p2 = ( int(nose_end_point2D[0][0][0]), int(nose_end_point2D[0][0][1]))
     
    cv2.line(blank_image, p1, p2, (255,0,0), 2)
    return blank_image



if __name__ == '__main__':
    shared_memory, semaphore = access_shared_memory_and_semaphore()
    mapfile = mmap.mmap(shared_memory.fd, shared_memory.size)

    print("Starting the process")
    time.sleep(1)
    semaphore.acquire()
    first_readed_message = utils.read_from_memory(mapfile)
    if not first_readed_message == utils.FIRST_HANDSHAKE :
        print("brr, some bullshit here")
    else:
        print("Passing back the handshake")
    utils.write_to_memory(mapfile, utils.SECOND_HANDSHAKE)
    semaphore.release()
    message_i_just_read = utils.SECOND_HANDSHAKE
    # message_i_just_read = wait_for_new_message(message_i_just_read, mapfile, semaphore, False)
        


    while True:
        message_i_just_read = wait_for_new_message(message_i_just_read, mapfile, semaphore)
        if message_i_just_read == utils.THIRD_HANDSHAKE or message_i_just_read== utils.SECOND_HANDSHAKE:
            continue
        else:
            meta = json_to_obj(message_i_just_read)
            blank_image = draw_points_on_blank(meta)
            if len(meta['points'])>0:
                blank_image = draw_face_vector_on_blank(meta, blank_image)

            blank_image = resize_back(blank_image)

            cv2.imshow('image',blank_image)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                write_last_message(mapfile, semaphore)
                break
            else:
                message_i_just_read = utils.READY_FOR_NEXT


