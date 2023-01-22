import cv2
import numpy as np
import sys
import os
from os import listdir
from os.path import isfile, join

#"video_025.mp4"
def background_subtract(file_name):
    
    out_name = file_name.removesuffix('.mp4')+'_output.mp4'
    cap = cv2.VideoCapture(file_name)
    out = cv2.createBackgroundSubtractorMOG2()   
    fourcc = cv2.VideoWriter_fourcc(*'MP4V')
    output = cv2.VideoWriter(out_name, fourcc, 20.0, (640,512), isColor=False)
    
    print(out_name+" is processed!")
    
    while(cap.isOpened()):
        
        ret, frame = cap.read()
    
        if ret==True:
            frame = cv2.flip(frame,180)

            outmask = out.apply(frame)
            output.write(outmask)
    
            #cv2.imshow('original', frame)
            #cv2.imshow('Motion Tracker', outmask)
    
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            break

    output.release()
    cap.release()
    cv2.destroyAllWindows()
    
    print(out_name+" is completed!")
    
    
if __name__ == "__main__":
    filespath = dir_path = os.path.dirname(os.path.realpath(__file__))#str(sys.argv[1])
    onlyfiles = [f for f in listdir(filespath) if isfile(join(filespath, f))]
    for file_name in onlyfiles:
        if file_name.endswith('.mp4') and not file_name.endswith('_output.mp4'):
            background_subtract(file_name)
        
        
    
