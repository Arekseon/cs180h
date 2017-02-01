import sys
import os
import dlib
import glob

import cv2
import numpy as np
import random
import sqlite3
import json
import numpy as np
import time
import threading
import socket
import json
# import lock

DO_BLACK = False
DO_WITH_ORIGIN = True
SERVER_MODE = False
BUSY = False

predictor_path = "shape_predictor_68_face_landmarks.dat"
predictor = dlib.shape_predictor(predictor_path)
delaunay_color = (255,0,0)
points_color = (0, 0, 255)

mutex = threading.Lock()

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
 
# Draw a point
def draw_point(img, p, color ) :
    cv2.circle (img, p, 3, color, -1, cv2.LINE_8, 0)
 
 
# Draw delaunay triangles
def draw_delaunay(img, subdiv, delaunay_color ) :
 
    triangleList = subdiv.getTriangleList();
    size = img.shape
    r = (0, 0, size[1], size[0])
 
    for t in triangleList :
        pt1 = (t[0], t[1])
        pt2 = (t[2], t[3])
        pt3 = (t[4], t[5])
        if rect_contains(r, pt1) and rect_contains(r, pt2) and rect_contains(r, pt3) :
            cv2.line(img, pt1, pt2, delaunay_color, 1, cv2.LINE_8, 0)
            cv2.line(img, pt2, pt3, delaunay_color, 1, cv2.LINE_8, 0)
            cv2.line(img, pt3, pt1, delaunay_color, 1, cv2.LINE_8, 0)

def get_faces_points(img):
   detector = dlib.get_frontal_face_detector()
   detected_faces = detector(img, 1)

   print("Number of faces detected: {}".format(len(detected_faces)))
   faces_points = []
   for k, d in enumerate(detected_faces):
      print("Detection {}: Left: {} Top: {} Right: {} Bottom: {}".format(
           k, d.left(), d.top(), d.right(), d.bottom()))
      shape = predictor(img, d)
      points = []
      for i in xrange(0,68):
         point = (shape.part(i).x, shape.part(i).y)
         points.append(sanitize_point(point,img.shape))
      faces_points.append(points)
   return faces_points

def sanitize_point(old_point,size):
   
   point_x = max(old_point[0], 0)
   point_x = min(point_x, size[1])
   point_y = max(old_point[1], 0)
   point_y = min(point_y, size[0])
   point = (point_x,point_y)
   return point

def save_points_to_db(db_name, file_name, faces_points):
   conn = sqlite3.connect(db_name)
   c = conn.cursor()
   c.execute("INSERT INTO points VALUES (?,?)", (file_name, json.dumps(faces_points) ) )
   conn.commit()
   conn.close()
def get_points_from_db(db_name, file_name):
   conn = sqlite3.connect(db_name)
   c = conn.cursor()
   c.execute('SELECT points_json FROM points WHERE file_name=?', (file_name,))
   result = c.fetchone()[0]
   conn.commit()
   conn.close()
   return json.loads(result)

def create_db(db_name):
   conn = sqlite3.connect(db_name)
   c = conn.cursor()
   c.execute('''CREATE TABLE points (file_name text, points_json text)''')
   conn.commit()
   conn.close()

def do_the_subjob_extract_points(file_name, db_name):
   # Read in the image.
   img_grey = cv2.imread(file_name, cv2.IMREAD_GRAYSCALE);  

   faces_points = get_faces_points(img_grey) 
   mutex.acquire()
   save_points_to_db(db_name, file_name, faces_points)
   mutex.release()

def do_the_subjob_draw_points(file_name, db_name, output_file_name, img):
   faces_points = get_points_from_db(db_name, file_name) 
   # Rectangle to be used with Subdiv2D
   # size = img.shape
   # rect = (0, 0, size[1], size[0])

   # for face_points in faces_points:
   #    # Create an instance of Subdiv2D
   #    subdiv = cv2.Subdiv2D(rect);

   #    for p in face_points :
   #       subdiv.insert((p[0],p[1]))
         
   #    # Draw delaunay triangles
   #    draw_delaunay (img, subdiv, (255, 0, 0));

   #    # Draw points
   #    for p in face_points :
   #       draw_point(img, (p[0],p[1]), (0,0,255))
   img = draw_points_on_image(img, faces_points)

   print "save to {}".format(output_file_name)
   cv2.imwrite(output_file_name, img);

def draw_points_on_image(img, points):
   faces_points = points
   # Rectangle to be used with Subdiv2D
   size = img.shape
   rect = (0, 0, size[1], size[0])

   for face_points in faces_points:
      # Create an instance of Subdiv2D
      subdiv = cv2.Subdiv2D(rect);

      for p in face_points :
         subdiv.insert((p[0],p[1]))
         
      # Draw delaunay triangles
      draw_delaunay (img, subdiv, (255, 0, 0));

      # Draw points
      for p in face_points :
         draw_point(img, (p[0],p[1]), (0,0,255))
   return img


def do_the_job(file_name, output_file_name, db_name):

   
   do_the_subjob_extract_points(file_name, db_name)

   img = cv2.imread(file_name);
   if DO_BLACK:
      blank_output_file_name = output_file_name.replace("OUT","BLANK_OUT")
      blank_image = np.zeros((img.shape[0], img.shape[1], 3), np.uint8)
      do_the_subjob_draw_points(file_name, db_name, blank_output_file_name, blank_image)

   if DO_WITH_ORIGIN:
      do_the_subjob_draw_points(file_name, db_name, output_file_name, img)      



def do_the_job_with_folder(folder_name):
   faces_folder_path = "./{}".format(folder_name)
   output_folder_name = "{}_output".format(folder_name)
   if not os.path.exists(output_folder_name):
      os.makedirs(output_folder_name)


   db_name = "{}_db.db".format(folder_name)
   if not os.path.exists(db_name):
      create_db(db_name)
   

   file_counter = 1000
   for file_name in glob.glob(os.path.join(faces_folder_path, "*.png")):
      print "doing file ", file_name
      output_file_name = "./{}/{}".format(output_folder_name, os.path.basename(file_name))
      # output_file_name = "./{}/OUT_{}.png".format(output_folder_name, file_counter)
      file_counter+=1 
      do_the_job(file_name, output_file_name, db_name)
   return file_counter - 1000

# def do_the_job_with_folder_using_threads(folder_name):
#    faces_folder_path = "./{}".format(folder_name)
#    output_folder_name = "{}_output".format(folder_name)
#    if not os.path.exists(output_folder_name):
#       os.makedirs(output_folder_name)


#    db_name = "{}_db.db".format(folder_name)
#    if not os.path.exists(db_name):
#       create_db(db_name)
   
#    threads = []
#    file_counter = 1000
#    for file_name in glob.glob(os.path.join(faces_folder_path, "*.png")):
#       print "doing file ", file_name
#       output_file_name = "./{}/OUT_{}.png".format(output_folder_name, file_counter)
#       file_counter+=1 

#       t = threading.Thread(target=do_the_job, args=(file_name, output_file_name, db_name,))
#       threads.append(t)
#       t.start()
#    for t in threads:
#        t.join()

#    return file_counter - 1000



def do_the_job_with_file(file_name, output_folder_name=None, db_name=None):
   if db_name==None:
      db_name = "{}_db.db".format(file_name)
      if not os.path.exists(db_name):
         create_db(db_name)
   
   if output_folder_name == None:
      output_file_name = "{}_output.png".format(os.path.basename(file_name)), db_name
   else:
      output_file_name = "./{}/{}".format(output_folder_name, os.path.basename(file_name))
   do_the_job(file_name, output_file_name, db_name)
   # do_the_job(file_name, "{}_output.png".format(os.path.basename(file_name)), db_name)

def run_server(PORT_NUMBER=3141):
   s = socket.socket()
   # PORT_NUMBER = 5002
   HOST_NAME = ""
   server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   server_socket.bind((HOST_NAME,PORT_NUMBER))
   server_socket.listen(5)
   SIZE = 4096000
   
   print "Starting server"
   while True:
      client_socket, address = server_socket.accept()
      data = client_socket.recv(SIZE)
      print "GOT DATA " , data
      request = json.loads(data)
      
      action = request['action'] 
      if action == "print_message":
         print request["message"]
         client_socket.send(json.dumps("{}_roger".format(request['message'])))
      
      elif action == "run_points_for_folder":
         folder_name = request['folder'] 
         print "do the folder = {}".format(action)
         start_time = time.clock()

         file_counter = do_the_job_with_folder(folder_name)
         end_time = time.clock()
         total_time = end_time - start_time
         print "time spent: {} for {} files. average time = {}".format(total_time, file_counter, total_time/file_counter )
         


         respond_message = {
            'action':'respond',
            'folder':folder_name,
            'status':'done'
         }
      


      elif action == "run_points_for_frame":
         file_name = request['file_name']
         folder_name = request['folder']

   

         db_name = request['database']
         if not os.path.exists(db_name):
            create_db(db_name)
      


         output_folder_name = "{}_output".format(folder_name)
         if not os.path.exists(output_folder_name):
            os.makedirs(output_folder_name)

         do_the_job_with_file("./{}/{}".format(folder_name, file_name), output_folder_name, db_name)
         respond_message = {
            'action':'respond_for_frame',
            'file':file_name,
            'status':'done'
         }


      elif action == "check_if_ready_to_work":
         respond_message = {
            'action':'respond_ready_to_work',
            'answer':not BUSY
         }         
         
      elif action == "get_point_from_image_serial":
         image = request['image']
         file_name = request['file_name']
         # points = get_faces_points(image)

         #test
         # img = draw_points_on_image(img, points)
         # cv2.imwrite("{}.jpeg".format(file_name), img)
         respond_message = {
            'action':'test_answer',
            'answer':'no error'
         }








      else:
         print "unknown command"
      message_send = json.dumps(respond_message)
      client_socket.send(message_send)
      print message_send

















if __name__ == '__main__':
   start_time = time.clock()
   

   if len(sys.argv) < 2:
      print("No input")
   else:
      if "server_mode" in sys.argv:
         port = int(sys.argv[2])
         SERVER_MODE = True
         run_server(port)

      else:
         print "no server"
      file_name = sys.argv[1]

   # do_the_job_with_file("homer.png")



   # folder_name = "bb"
   
   # file_counter = do_the_job_with_folder(folder_name)

   # file_counter = do_the_job_with_folder_using_threads(folder_name)

   end_time = time.clock()
   total_time = end_time - start_time
   # print "time spent: {} for {} files. average time = {}".format(total_time, file_counter, total_time/file_counter )
   
# time spent: 89.718687 for 51 files. average time = 1.75918994118
# time spent: 89.593586 for 51 files. average time = 1.75673698039




# ffmpeg -i input.mp4 -vf fps=30 out%d.png
# ffmpeg -r 30 -start_number 790 -f image2 -i OUT_%d.png -vcodec mjpeg -qscale 1 video.avi