#!/usr/bin/env python
#-*- coding: utf-8 -*-
import cv2 
import pytesseract
import os
import pygame
from pygame.locals import*
import time
import RPi.GPIO as GPIO
import numpy as np
from picamera.array import PiRGBArray
from picamera import PiCamera
import requests, uuid, json
from pygame.locals import *
import io
import pyaudio
import wave
import sys
import pyzbar.pyzbar as pyzbar
# Imports the Google Cloud client library
from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types

GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(22, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(23, GPIO.IN, pull_up_down = GPIO.PUD_UP) 
GPIO.setup(27, GPIO.IN, pull_up_down = GPIO.PUD_UP) # quit button

#os.putenv('SDL_VIDEODRIVER','fbcon')
#os.putenv('SDL_FBDEV','/dev/fb1')
#os.putenv('SDL_MOUSEDRV','TSLIB')
#os.putenv('SDL_MOUSEDEV','/dev/input/touchscreen')

#camera = PiCamera()
#camera.resolution = (320, 240)
#camera.framerate = 30
#rawCapture = PiRGBArray(camera, size=(320, 240))

pygame.init()
Clock = pygame.time.Clock()
count = 0
pygame.mouse.set_visible(True)
WHITE = 255,255,255
BLACK = 0,0,0
screen = pygame.display.set_mode((320,240))

my_font = pygame.font.Font('/home/pi/final_project/simhei/SimHei.ttf', 30)
#my_font = pygame.font.Font('Sim', 30)
my_buttons = {'image-T':(80,60),'voice-T':(240,60),'remain':(80,200),'quit':(240,200)}
screen.fill(WHITE) #Erase the work space
rectList = []
surList = []

global language
language = '&to=zh'

for my_text, text_pos in my_buttons.items():
    text_surface = my_font.render(my_text, True, BLACK)
    surList.append(text_surface)
    rect = text_surface.get_rect(center=text_pos)
    rectList.append(rect)
    screen.blit(text_surface, rect)

pygame.display.flip()

def quit():
    global code_running
    code_running = False
    
def ImageTrans():
    camera = PiCamera()
    camera.resolution = (320, 240)
    camera.framerate = 30

    rawCapture = PiRGBArray(camera, size=(320, 240))
    flag = True # true
    for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
        image = frame.array
        cv2.imshow("Frame", image)
        key = cv2.waitKey(1) & 0xFF
    
        rawCapture.truncate(0)

        if key == ord("s"):
            text = pytesseract.image_to_string(image).encode('utf-8','ignore')
            print(text)
            cv2.imshow("Frame", image)
            cv2.waitKey(0)
            break

    key_var_name = 'TRANSLATOR_TEXT_SUBSCRIPTION_KEY'
    if not key_var_name in os.environ:
        raise Exception('Please set/export the environment variable: {}'.format(key_var_name))
    subscription_key = os.environ[key_var_name]

    endpoint_var_name = 'TRANSLATOR_TEXT_ENDPOINT'
    if not endpoint_var_name in os.environ:
        raise Exception('Please set/export the environment variable: {}'.format(endpoint_var_name))
    endpoint = os.environ[endpoint_var_name]

    path = '/translate?api-version=3.0'
    params = language
    constructed_url = endpoint + path + params

    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }
    text = text.replace('\n','')
    body = [{
        'text': text
    }]

    request = requests.post(constructed_url, headers=headers, json=body)
    response = request.json()

    json_string = json.dumps(response, sort_keys=True, indent=4,
                 ensure_ascii=False, separators=(',', ': '))   
    json_string = json_string.encode('utf-8')
    #print(type(json_string))
    s1 = json_string.replace("[","").replace("]","")
    s2 = json.loads(s1)
    translated_result = s2["translations"]["text"]
    translated_result = translated_result.encode('utf-8')
    print(translated_result)
    camera.close()
    cv2.destroyAllWindows()
    return translated_result

def Voicetrans():
    
    global stream
    global p
    # hide the wrong information
    os.close(sys.stderr.fileno())
    
    BUTT = 17    # GPIO 17, the button that start recording when pressed
    # the button voltage become low when pressed
    # CHUNK could be intepreted as data package or pieces
    CHUNK = 512 
    FORMAT = pyaudio.paInt16  
    RATE = 44100  # 44100 samples/second, sampling rate
    WAVE_OUTPUT_FILENAME = "/home/pi/final_project/Voice/voice_record.wav"
    print('Please start recording by pressing the button 17...')
    GPIO.remove_event_detect(17)
    GPIO.wait_for_edge(BUTT, GPIO.FALLING)
    #print("test")
        
    # To use PyAudio, first instantiate PyAudio using pyaudio.PyAudio(), which sets up the portaudio system.
    p = pyaudio.PyAudio()
    stream = p.open(format = FORMAT,
                    channels = 1,  
                    rate = RATE,
                    input = True,
                    frames_per_buffer = CHUNK)
    print("Recording...")

   
    # Recoding when button pressed, and stop when button released
    frames = []
    while GPIO.input(BUTT) == 0:
        data = stream.read(CHUNK)
        frames.append(data)
        #print("Test...")
    print("Finish recording,file output：" + WAVE_OUTPUT_FILENAME + '\n')
    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(p.get_sample_size(FORMAT))    # Returns the size (in bytes) for the specified sample format.
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    client = speech.SpeechClient()

    # The name of the audio file to transcribe
    file_name = os.path.join(
        os.path.dirname(__file__),
        '/home/pi/final_project/Voice/voice_record.wav')
    # Loads the audio into memory
    with io.open(file_name, 'rb') as audio_file:
        content = audio_file.read()
        audio = types.RecognitionAudio(content=content)

    config = types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=44100,
        #language_code='cmn-Hans-CN')
        language_code='en-US')

    # Detects speech in the audio file
    response = client.recognize(config, audio)

    for result in response.results:
        print(format(result.alternatives[0].transcript))
        print('Confidence: {}'.format(result.alternatives[0].confidence))
    text = format(result.alternatives[0].transcript)
    key_var_name = 'TRANSLATOR_TEXT_SUBSCRIPTION_KEY'
    if not key_var_name in os.environ:
        raise Exception('Please set/export the environment variable: {}'.format(key_var_name))
    subscription_key = os.environ[key_var_name]

    endpoint_var_name = 'TRANSLATOR_TEXT_ENDPOINT'
    if not endpoint_var_name in os.environ:
        raise Exception('Please set/export the environment variable: {}'.format(endpoint_var_name))
    endpoint = os.environ[endpoint_var_name]

    path = '/translate?api-version=3.0'
    #params = '&to=zh'
    params = language
    constructed_url = endpoint + path + params

    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }
    text = text.replace('\n','')
    body = [{
        'text': text
    }]

    request = requests.post(constructed_url, headers=headers, json=body)
    response = request.json()

    json_string = json.dumps(response, sort_keys=True, indent=4,
                 ensure_ascii=False, separators=(',', ': '))   
    json_string = json_string.encode('utf-8')
    #print(type(json_string))
    s1 = json_string.replace("[","").replace("]","")
    s2 = json.loads(s1)
    translated_result = s2["translations"]["text"]
    translated_result = translated_result.encode('utf-8')
    print(translated_result)
    return translated_result,format(result.alternatives[0].confidence)

def QR_recog( ):
    camera = PiCamera()
    camera.resolution = (1024, 768)
    camera.framerate = 30

    rawCapture = PiRGBArray(camera, size=(1024, 768))

    for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
        image = frame.array
        cv2.imshow("Frame", image)
        key = cv2.waitKey(1) & 0xFF
    
        rawCapture.truncate(0)

        if key == ord("s"):
            cv2.imshow("Frame", image)
            cv2.imwrite('test.png',image)
            cv2.waitKey(0)
            break

    image = cv2.imread("test.png")

    decodedObjects = pyzbar.decode(image)

    for obj in decodedObjects:
        print("Type:", obj.type)
        print("Data:", obj.data, "\n")
    text = obj.data
    cv2.imshow("Frame", image)
    cv2.waitKey(0)
    
    key_var_name = 'TRANSLATOR_TEXT_SUBSCRIPTION_KEY'
    if not key_var_name in os.environ:
        raise Exception('Please set/export the environment variable: {}'.format(key_var_name))
    subscription_key = os.environ[key_var_name]

    endpoint_var_name = 'TRANSLATOR_TEXT_ENDPOINT'
    if not endpoint_var_name in os.environ:
        raise Exception('Please set/export the environment variable: {}'.format(endpoint_var_name))
    endpoint = os.environ[endpoint_var_name]

    path = '/translate?api-version=3.0'
    params = language
    constructed_url = endpoint + path + params

    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }
    text = text.replace('\n','')
    body = [{
        'text': text
    }]

    request = requests.post(constructed_url, headers=headers, json=body)
    response = request.json()

    json_string = json.dumps(response, sort_keys=True, indent=4,
                 ensure_ascii=False, separators=(',', ': '))   
    json_string = json_string.encode('utf-8')
    #print(type(json_string))
    s1 = json_string.replace("[","").replace("]","")
    s2 = json.loads(s1)
    translated_result = s2["translations"]["text"]
    translated_result = translated_result.encode('utf-8')
    print(translated_result)
    camera.close()
    cv2.destroyAllWindows()
    return translated_result

code_running=True
x = -1
y = -1
while code_running :
    time.sleep(0.1)
    #Clock.tick(60)
    x = -1
    y = -1
    my_buttons = {'image-T':(80,60),'voice-T':(240,60),'settings':(80,200),'QR_Scan':(240,200)}
    screen.fill(WHITE) #Erase the work space

    for my_text, text_pos in my_buttons.items():
        text_surface = my_font.render(my_text, True, BLACK)
        surList.append(text_surface)
        rect = text_surface.get_rect(center=text_pos)
        rectList.append(rect)
        screen.blit(text_surface, rect)

    pygame.display.flip()
    
    for event in pygame.event.get():
        if(event.type is MOUSEBUTTONDOWN):
            pos = pygame.mouse.get_pos()
        elif(event.type is MOUSEBUTTONUP):
            pos = pygame.mouse.get_pos()
            x,y = pos
            
    if (y > 40 and y < 80 and x > 40 and x < 120):
        flag_s = True
        #translated_text = ImageTrans()
        #print("test press")
        translated_text = ImageTrans()
        while (flag_s):
            x = -1
            y = -1
            time.sleep(0.01)
            my_result = {translated_text:(160,140),'Translation result':(160,40)}
            rectList2 = []
            surList2 = []
            screen.fill(WHITE) #Erase the work space
            for my_text, text_pos in my_result.items():
                my_text = my_text.decode(encoding='UTF-8')
                text_surface = my_font.render(my_text, True, BLACK)
                surList2.append(text_surface)
                rect = text_surface.get_rect(center=text_pos)
                rectList2.append(rect)
                screen.blit(text_surface, rect)
            pygame.display.flip()
                                                                               
            if(not GPIO.input(22)): # go back to the first page
                flag_s = False
                
            if(not GPIO.input(27)): # exit the program
                flag_s = False
                code_running = False

    elif (y > 40 and y < 80 and x > 200 and x < 280):
        text,confidence = Voicetrans()
        flag_s = True
        while (flag_s):
            x = -1
            y = -1
            my_result = {text:(160,140),confidence:(160,180),'Translation result':(160,40)}
            rectList2 = []
            surList2 = []
            screen.fill(WHITE) #Erase the work space
            for my_text, text_pos in my_result.items():
                my_text = my_text.decode(encoding='UTF-8')
                text_surface = my_font.render(my_text, True, BLACK)
                surList2.append(text_surface)
                rect = text_surface.get_rect(center=text_pos)
                rectList2.append(rect)
                screen.blit(text_surface, rect)
            pygame.display.flip()
                                                                               
            if(not GPIO.input(22)): # go back to the first page
                flag_s = False
                
            if(not GPIO.input(27)): # exit the program
                flag_s = False
                code_running = False
        #GPIO.remove_event_detect(17)
    elif (y > 180 and y < 220 and x > 40 and x < 120): #language change
        flag_s = True
        while (flag_s):
            x = -1
            y = -1
            time.sleep(0.01)
            language_sel = {'Chinese':(80,60),'Deutsch':(240,60),'Italian':(80,200),'Back':(240,200)}
            screen.fill(WHITE) #Erase the work space

            for my_text, text_pos in language_sel.items():
                text_surface = my_font.render(my_text, True, BLACK)
                surList.append(text_surface)
                rect = text_surface.get_rect(center=text_pos)
                rectList.append(rect)
                screen.blit(text_surface, rect)

            pygame.display.flip()
    
            for event in pygame.event.get():
                if(event.type is MOUSEBUTTONDOWN):
                    pos = pygame.mouse.get_pos()
                elif(event.type is MOUSEBUTTONUP):
                    pos = pygame.mouse.get_pos()
                    x,y = pos
            if (y > 40 and y < 80 and x > 40 and x < 120):
                language = '&to=zh'
            elif (y > 40 and y < 80 and x > 200 and x < 280):
                language = '&to=de'
            elif (y > 180 and y < 220 and x > 40 and x < 120):
                language = '&to=it'
            elif (y > 180 and y < 220 and x > 200 and x < 280):
                flag_s = False
            if(not GPIO.input(22)): # go back to the first page
                flag_s = False
                
            if(not GPIO.input(27)): # exit the program
                flag_s = False
                code_running = False
    elif (y > 180 and y < 220 and x > 200 and x < 280): # QR_code scanning
        QR_text = QR_recog()
        flag_s = True
        while (flag_s):
            time.sleep(0.01)
            x = -1
            y = -1
            my_result = {QR_text:(160,140),'Translation result':(160,40)}
            rectList2 = []
            surList2 = []
            screen.fill(WHITE) #Erase the work space
            for my_text, text_pos in my_result.items():
                my_text = my_text.decode(encoding='UTF-8')
                text_surface = my_font.render(my_text, True, BLACK)
                surList2.append(text_surface)
                rect = text_surface.get_rect(center=text_pos)
                rectList2.append(rect)
                screen.blit(text_surface, rect)
            pygame.display.flip()
                                                                               
            if(not GPIO.input(22)): # go back to the first page
                flag_s = False
                
            if(not GPIO.input(27)): # exit the program
                flag_s = False
                code_running = False

    if(not GPIO.input(27)):
        code_running = False
        flag_s = False
        print("physical button")


        



