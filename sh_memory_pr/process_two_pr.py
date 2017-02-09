import utils, time, posix_ipc, mmap, json, cv2
import numpy as np

process_one_name = "PROCESS_ONE"
author_process = "PROCESS_TWO"
SEND_POINTS_CODE = "sending_face_points"
RECEIVED_POINTS_CODE = "received_points"
LAST_MESSAGE = "LAST_MESSAGE"

remember_last_n_frames = 3
last_frames = []

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

def wait_for_new_message2(reply_code, mapfile, semaphore, last_message=False):
    new_message_found = False
    while not new_message_found:
        semaphore.acquire()
        message_i_just_read = utils.read_from_memory(mapfile)
        json_i_just_read = json_to_obj(message_i_just_read)
        if json_i_just_read['author'] == process_one_name and json_i_just_read['receiver'] == author_process:
            message_to_send = {
                'author': author_process,
                'receiver': process_one_name,
                'action': reply_code
            }
            # print ("got message:")
            # print json_i_just_read
            if last_message:
                message_to_send['action'] = LAST_MESSAGE
            utils.write_to_memory(mapfile, json.dumps(message_to_send))
            new_message_found = True
        semaphore.release()
        time.sleep(0.001)
    return json_i_just_read



def write_last_message(mapfile, semaphore):
    last_message = {
                'author': author_process,
                'receiver': process_one_name,
                'action': LAST_MESSAGE
            }
    semaphore.acquire()
    utils.write_to_memory(mapfile, json.dumps(last_message))
    semaphore.release()    

def draw_point(img, p, color ) :
    cv2.circle (img, p, 1, color, -1)

def json_to_obj(str):
    try:
        meta = json.loads(str)
    except:
        print("something wrong with json, exiting")
        print str
        exit()
    return meta

# def draw_points_on_blank(meta):
#     blank_image = np.zeros((int(meta['width']), int(meta['height']), 3), np.uint8)
#     for faces in meta['points']: 
#         for p in faces:
#             draw_point(blank_image, (p[0],p[1]), (0,0,255))
#     # cv2.imshow('image',blank_image)
#     # cv2.waitKey(1)
#     return blank_image

def draw_points_on_existed_blank(points, blank_image, color):
    for p in points:
        draw_point(blank_image, (p[0],p[1]), color)
    return blank_image


def resize_back(blank_image):
    return cv2.resize(blank_image,None,fx=(1/utils.SCALE_DOWN), fy=(1/utils.SCALE_DOWN), interpolation = cv2.INTER_CUBIC)

def create_blank_image(width, height):
    return  np.zeros((width, height, 3), np.uint8)


def scale_points(points, scale):
    new_points = []
    for p in points:
        new_points.append(( int(p[0]*scale),  int(p[1]*scale)))
    return new_points

def running_average_points(points):
    global last_frames
    if len(last_frames) < remember_last_n_frames:
        last_frames.append(points)
        return points

    last_frames.append(points)
    #create average points
    average_points = []
    for i in xrange(0,len(last_frames[0])):
        average_points.append( (0,0) )

    for frame in last_frames:
        for i in xrange(0,len(frame)):
            average_points[i] = ( average_points[i][0] + frame[i][0], average_points[i][1] + frame[i][1]  )

    for i in xrange(0,len(average_points)):
        average_points[i] = (int(average_points[i][0]/remember_last_n_frames), int(average_points[i][1]/remember_last_n_frames) )
    
    # update last frames
    last_frames = last_frames[1:]
    # print ("..")
    # print average_points
    return average_points


def image_result(message):

    scaled_width = int(message['width']/utils.SCALE_DOWN)
    scaled_height = int(message['height']/utils.SCALE_DOWN)
    blank_image = create_blank_image(scaled_width, scaled_height)
    
    if message['face_found']:
        points = message['points'][0]
        scaled_points = scale_points(points,1/utils.SCALE_DOWN)

        averaged_scaled_points = running_average_points(scaled_points)

        # blank_image = draw_points_on_existed_blank(scaled_points, blank_image, (0,0,255))
        blank_image = draw_points_on_existed_blank(averaged_scaled_points, blank_image, (0,255,0))
        # blank_image = draw_face_vector_on_blank2(scaled_points, scaled_width, scaled_height, blank_image, (255,0,0))
        # blank_image = draw_face_vector_on_blank2(averaged_scaled_points, scaled_width, scaled_height, blank_image, (255,255,0))

    return blank_image


# def draw_face_vector_on_blank(meta, blank_image):
#     size = blank_image.shape
    
#     image_points = np.array([
#                             meta['points'][0][33], # Nose tip
#                             meta['points'][0][8],  # Chin
#                             meta['points'][0][36], # Left eye left corner
#                             meta['points'][0][45], # Right eye right corne
#                             meta['points'][0][48], # Left Mouth corner
#                             meta['points'][0][54]  # Right mouth corner
#                         ], dtype="double")


#     model_points = np.array([
#                             (0.0, 0.0, 0.0),             # Nose tip
#                             (0.0, -330.0, -65.0),        # Chin
#                             (-225.0, 170.0, -135.0),     # Left eye left corner
#                             (225.0, 170.0, -135.0),      # Right eye right corne
#                             (-150.0, -150.0, -125.0),    # Left Mouth corner
#                             (150.0, -150.0, -125.0)      # Right mouth corner
                         
#                         ])


#     focal_length = size[1]
#     center = (size[1]/2, size[0]/2)
#     # focal_length = meta['width']
#     # center = (meta['width']/2, meta['height']/2)

#     camera_matrix = np.array(
#                              [[focal_length, 0, center[0]],
#                              [0, focal_length, center[1]],
#                              [0, 0, 1]], dtype = "double"
#                              )

#     dist_coeffs = np.zeros((4,1)) # Assuming no lens distortion
#     (success, rotation_vector, translation_vector) = cv2.solvePnP(model_points, image_points, camera_matrix, dist_coeffs)#, flags=cv2.CV_ITERATIVE)


#     (nose_end_point2D, jacobian) = cv2.projectPoints(np.array([(0.0, 0.0, 1000.0)]), rotation_vector, translation_vector, camera_matrix, dist_coeffs)
#     # for p in image_points:
#     #     cv2.circle(blank_image, (int(p[0]), int(p[1])), 3, (0,0,255), -1)

#     p1 = ( int(image_points[0][0]), int(image_points[0][1]))
#     p2 = ( int(nose_end_point2D[0][0][0]), int(nose_end_point2D[0][0][1]))
     
#     cv2.line(blank_image, p1, p2, (255,0,0), 2)
#     return blank_image

def draw_face_vector_on_blank2(points, width, height, blank_image, color):
    size = blank_image.shape
    
    image_points = np.array([
                            points[33], # Nose tip
                            points[8],  # Chin
                            points[36], # Left eye left corner
                            points[45], # Right eye right corne
                            points[48], # Left Mouth corner
                            points[54]  # Right mouth corner
                        ], dtype="double")


    model_points = np.array([
                            (0.0, 0.0, 0.0),             # Nose tip
                            (0.0, -330.0, -65.0),        # Chin
                            (-225.0, 170.0, -135.0),     # Left eye left corner
                            (225.0, 170.0, -135.0),      # Right eye right corne
                            (-150.0, -150.0, -125.0),    # Left Mouth corner
                            (150.0, -150.0, -125.0)      # Right mouth corner
                         
                        ])


    # focal_length = size[1]
    # center = (size[1]/2, size[0]/2)
    focal_length = width
    center = (width/2, height/2)

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
     
    cv2.line(blank_image, p1, p2, color, 2)
    return blank_image

if __name__ == '__main__':
    shared_memory, semaphore = access_shared_memory_and_semaphore()
    mapfile = mmap.mmap(shared_memory.fd, shared_memory.size)

    print("Starting the process")
    time.sleep(1)


    global last_frames
    last_frames = []


    message = wait_for_new_message2(utils.SECOND_HANDSHAKE, mapfile, semaphore)
    if message['action'] == utils.FIRST_HANDSHAKE:
        print("receicevd first handshake, second handshake replied")
    else:
        print("i dunno, some error")
        print message


    while True:
        message = wait_for_new_message2(RECEIVED_POINTS_CODE , mapfile, semaphore)
        if message['action'] == SEND_POINTS_CODE:

            # blank_image = draw_points_on_blank(message)
            # if message['face_found']:
            #     blank_image = draw_face_vector_on_blank(message, blank_image)

            # blank_image = resize_back(blank_image)
            blank_image = image_result(message)

            cv2.imshow('image',blank_image)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                wait_for_new_message2(RECEIVED_POINTS_CODE, mapfile, semaphore, last_message=True)
                break
    print("done here")