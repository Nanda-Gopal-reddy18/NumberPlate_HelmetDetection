import numpy as np
import cv2 as cv
import subprocess
import time
import os
from yoloDetection import detectObject, displayImage
import sys
from pathlib import Path


global class_labels
global cnn_model
global cnn_layer_names

def loadLibraries(): #function to load yolov3 model weight and class labels
        global class_labels
        global cnn_model
        global cnn_layer_names
        base_dir = Path(__file__).resolve().parent
        labels_path = base_dir / 'yolov3model' / 'yolov3-labels'
        cfg_path = base_dir / 'yolov3model' / 'yolov3.cfg'
        weights_path = base_dir / 'yolov3model' / 'yolov3.weights'
        
        class_labels = open(labels_path).read().strip().split('\n') #reading labels from yolov3 model
        print(str(class_labels)+" == "+str(len(class_labels)))
        cnn_model = cv.dnn.readNetFromDarknet(str(cfg_path), str(weights_path)) #reading model
        cnn_layer_names = cnn_model.getLayerNames() #getting layers from cnn model
        # Flatten layer indices safely to support different OpenCV versions
        unconnected_layers = np.array(cnn_model.getUnconnectedOutLayers()).flatten()
        cnn_layer_names = [cnn_layer_names[i - 1] for i in unconnected_layers] #assigning all layers

def detectFromImage(imagename): #function to detect object from images
        #random colors to assign unique color to each label
        label_colors = (0,255,0)#np.random.randint(0,255,size=(len(class_labels),3),dtype='uint8')
        image = cv.imread(imagename) #image reading
        if image is None:
                raise ValueError(f"Invalid image path or unable to read image: {imagename}")
        image_height, image_width = image.shape[:2] #converting image to two dimensional array
        indexno = 0
        image, _ = detectObject(cnn_model, cnn_layer_names, image_height, image_width, image, label_colors, class_labels, indexno)#calling detection function
        displayImage(image,0)#display image with detected objects label

def detectFromVideo(videoFile): #function to read objects from video
        
        #random colors to assign unique color to each label
        label_colors = (0,255,0)#np.random.randint(0,255,size=(len(class_labels),3),dtype='uint8')
        indexno = 0
        video = cv.VideoCapture(videoFile)
        if not video.isOpened():
                raise ValueError(f"Unable to load/open video: {videoFile}")
        frame_height, frame_width = None, None  #reading video from given path
        
        while True:
                frame_grabbed, frames = video.read() #taking each frame from video
                #print(frame_grabbed)
                if not frame_grabbed: #condition to check whether video loaded or not
                        break
                if frame_width is None or frame_height is None:
                        frame_height, frame_width = frames.shape[:2] #detecting object from frame
                frames, _ = detectObject(cnn_model, cnn_layer_names, frame_height, frame_width, frames, label_colors, class_labels, indexno)
                #displayImage(frames,index)
                #indexno = indexno + 1
                print(indexno)
                if indexno == 5:
                    video.release()    
                    break

        print ("Releasing resources")
        video.release()


if __name__ == '__main__':
        loadLibraries()
        print("sample commands to run code with image or video")
        print("python yolo.py image input_image_path")
        print("python yolo.py video input_video_path")
        if len(sys.argv) == 3:
                if sys.argv[1] == 'image':
                        detectFromImage(sys.argv[2])
                elif sys.argv[1] == 'video':
                        detectFromVideo(sys.argv[2])
                else:
                        print("invalid input")
        else:
                print("follow sample command to run code")

                
	#video_path = None
	#video_output_path = "out.avi"
