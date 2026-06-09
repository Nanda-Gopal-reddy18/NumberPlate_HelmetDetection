from tkinter import messagebox
from tkinter import *
from tkinter.filedialog import askopenfilename
from tkinter import simpledialog
import tkinter
import numpy as np
from tkinter import filedialog
import torch
import cv2
import easyocr
import os
import socket
import pickle
import pathlib
from pathlib import Path
pathlib.PosixPath = pathlib.WindowsPath

main = tkinter.Tk()
main.title("Number Plate Detection")
main.geometry("1300x1200")

global filename, model
CONFIDENCE_THRESHOLD = 0.3
GREEN = (0, 255, 0)
reader = easyocr.Reader(['en'])

def loadDataset():
    global filename
    text.delete('1.0', END)
    filename = filedialog.askdirectory(initialdir=".") #upload dataset file
    text.insert(END,filename+" loaded\n\n")

def loadModel():
    global filename, model
    text.delete('1.0', END)
    model = torch.hub.load('yolov5', 'custom', path='model/best.pt', force_reload=True,source='local')
    text.insert(END,"Yolov5 Vehicle Object Detection Model Loaded")

def getNumber(img):
    global reader
    cv2.imwrite("plate.jpg", img)
    output = "Unable to read"
    result = reader.readtext("plate.jpg")
    if len(result) >= 1:
        result = result[0]
        output = result[1]
    return output
    
def detectPlate():
    global model
    filename = filedialog.askopenfilename(initialdir="testImages") #upload dataset file
    img = cv2.imread(filename)
    img = cv2.resize(img, (512, 512))
    results = model(img)
    results.xyxy[0]  # im predictions (tensor)
    out = results.pandas().xyxy[0]  # im predictions (pandas)
    print(out)
    if len(out) > 0:
        for i in range(len(out)):
            xmin = int(out['xmin'].ravel()[i])
            ymin = int(out['ymin'].ravel()[i])
            xmax = int(out['xmax'].ravel()[i])
            ymax = int(out['ymax'].ravel()[i])
            name = out['name'].ravel()[i]
            roi = img[ymin:ymin+ymax,xmin:xmin+xmax]
            number = getNumber(roi)
            cv2.rectangle(img, (xmin, ymin), (xmax, ymax), (255, 0, 0), 2)
            cv2.putText(img, number, (xmin, ymin-20), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)            
    cv2.imshow("Detected Output", img)
    cv2.waitKey(0)

def graph():
    grp = cv2.imread('model/results.png')
    grp = cv2.resize(grp, (800, 600))
    cv2.imshow("Yolo Performance Graph", grp)
    cv2.waitKey(0)

def close():
    main.destroy()
    
font = ('times', 16, 'bold')
title = Label(main, text='Number Plate Detection')
title.config(bg='chocolate', fg='white')  
title.config(font=font)           
title.config(height=3, width=120)       
title.place(x=0,y=5)

font1 = ('times', 13, 'bold')
datasetButton = Button(main, text="Upload Vehicle Dataset", command=loadDataset)
datasetButton.place(x=700,y=150)
datasetButton.config(font=font1)  

loadButton = Button(main, text="Generate & Load Yolo Model", command=loadModel)
loadButton.place(x=700,y=200)
loadButton.config(font=font1)

updateButton = Button(main, text="Number Plate Detection from Test Image", command=detectPlate)
updateButton.place(x=700,y=250)
updateButton.config(font=font1) 

detectButton = Button(main, text="Yolo Performance Graph", command=graph)
detectButton.place(x=700,y=300)
detectButton.config(font=font1)

graphButton = Button(main, text="Exit", command=close)
graphButton.place(x=700,y=350)
graphButton.config(font=font1)

font1 = ('times', 12, 'bold')
text=Text(main,height=30,width=80)
scroll=Scrollbar(text)
text.configure(yscrollcommand=scroll.set)
text.place(x=10,y=100)
text.config(font=font1)


main.config(bg='light salmon')
main.mainloop()
