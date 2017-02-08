

NULL_CHAR = '@'

SHARED_MEMORY_NAME = "SHWIFTY_MEMORY"
SEMAPHORE_NAME = "SHWIFTY_SEMAPHORE"
SHM_SIZE = 4096


SCALE_DOWN = 0.5

FIRST_HANDSHAKE = "FIRST_HANDSHAKE"
SECOND_HANDSHAKE = "SECOND_HANDSHAKE"
THIRD_HANDSHAKE = "THIRD_HANDSHAKE"
READY_FOR_NEXT = "READY_FOR_NEXT"
JOB_DONE = "JOB_DONE"
# IMAGE_LOOP_COUNTER = 200

def write_to_memory(mapfile, s):
    mapfile.seek(0)
    # s += NULL_CHAR
    mapfile.write("{}{}".format(s,NULL_CHAR))

def read_from_memory(mapfile):
    mapfile.seek(0)
    s = []
    c = mapfile.read_byte()
    while c != NULL_CHAR:
        s.append(c)
        c = mapfile.read_byte()
            
    s = ''.join(s)
    return s