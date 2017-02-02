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
    blank_image = cv2.resize(blank_image,None,fx=(1/utils.SCALE_DOWN), fy=(1/utils.SCALE_DOWN), interpolation = cv2.INTER_CUBIC)
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

            cv2.imshow('image',blank_image)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                write_last_message(mapfile, semaphore)
                break
            else:
                message_i_just_read = utils.READY_FOR_NEXT


