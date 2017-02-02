import time
print"something else",
time.sleep(1)
print"lolo"

import sys
import time, pygame.camera, pygame.image

# for i in range(10):
#     sys.stdout.write("\r{0}>".format("="*i))
#     sys.stdout.flush()
#     time.sleep(0.5)

# # # print"2345"
# import cStringIO

# def start_camera():
#     pygame.camera.init()
#     cam = pygame.camera.Camera(pygame.camera.list_cameras()[1])
#     cam.start()
#     return cam    

# def get_image_from_camera(cam):
#     return cam.get_image()

# def kill_camera(cam):
#     cam.stop()
#     pygame.camera.quit()




# output = cStringIO.StringIO()
# output.write('First line.\n')


import numpy as np
import cv2

cap = cv2.VideoCapture(1)

while(True):
    # Capture frame-by-frame
    ret, frame = cap.read()

    # Our operations on the frame come here
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Display the resulting frame
    cv2.imshow('frame',gray)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()