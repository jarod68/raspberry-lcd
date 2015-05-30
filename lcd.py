#!/usr/bin/env python

import sys
sys.path.append('/share/raspberry-lcd/quick2wire-python-api')

from i2clibraries import i2c_lcd
from threading import Thread, RLock
import datetime
import random
import time
import os
import signal
import json
import urllib.request
import RPi.GPIO as GPIO

# CONSTANTS :

LCD_TIME_SLEEP_TIME_S = 0.10
LCD_TOP_SLEEP_TIME_S = 5
LCD_TEMPERATURE_SLEEP_TIME_S = 60
NEW_PING_INTERVAL_TIME_S = 15

IP_TO_PINGS = "/share/raspberry-lcd/ip.txt"

# GLOBAL OBJECTS :

lcdLock = RLock()
lcd = i2c_lcd.i2c_lcd(0x27,1, 2, 1, 0, 4, 5, 6, 7, 3)

pingListLock = RLock()
pingObjects = []

GPIO.setmode(GPIO.BOARD)

class LCDTime(Thread):

    def __init__(self):
        Thread.__init__(self)
        self.Terminated = False 

    def run(self):
        while not self.Terminated:
            with lcdLock:
              lcd.setPosition(2, 0)
              now = datetime.datetime.now()
              lcd.writeString(now.strftime("%H:%M:%S"))

            time.sleep(LCD_TIME_SLEEP_TIME_S)

    def stop(self): 
      self.Terminated = True

class LCDTop(Thread):

    defectShow = False
    
    def __init__(self, pingTask):
        Thread.__init__(self)
        self.Terminated = False
        self.pingTask = pingTask

    def run(self):
        while not self.Terminated:
            
            with pingListLock:

              for ping in pingObjects:

                if ping.state == False:

                  with lcdLock:
                    lcd.setPosition(1, 0)
                    lcd.writeString("                ")
                    lcd.setPosition(1, 0)
                    lcd.writeString(ping.ip+" NOK ")
                    time.sleep(LCD_TOP_SLEEP_TIME_S)
                    print (ping.ip+" NOK")

            with lcdLock:
              lcd.setPosition(1, 0)
              pingsInList = self.pingTask.numberOfPingInList()
              lcd.writeString("Pings "+str(pingsInList - self.pingTask.numberOfPingInError())+"/"+str(pingsInList)+" OK     ")
              
            time.sleep(LCD_TOP_SLEEP_TIME_S)

            with lcdLock:
              lcd.setPosition(1, 0)
              now = datetime.datetime.now()
              lcd.writeString(now.strftime("%a %d %b %Y"))
              
            time.sleep(LCD_TOP_SLEEP_TIME_S)

    def stop(self): 
      self.Terminated = True



class LCDTemperature(Thread):

    def __init__(self):
        Thread.__init__(self)
        self.Terminated = False 

    def run(self):
        while not self.Terminated:
          data = urllib.request.urlopen('http://192.168.1.177')
          data = json.loads(data.read().decode('utf-8'))
          #data = json.loads('{"iT":"22.0","oT":"16.0","iH":"44.0","iP":"1003.2"}')
          with lcdLock:
              lcd.setPosition(2, 10)
              lcd.writeString(str(data['iT'])+"°c")

         
          time.sleep(LCD_TEMPERATURE_SLEEP_TIME_S)

    def stop(self): 
      self.Terminated = True

class PingObject:

    def __init__(self, ip):
      self.ip = ip
      self.state = False

    def isReachable():
      return self.state

class PingTask(Thread):

    def __init__(self, filename, ledManager):
        Thread.__init__(self)
        self.Terminated = False
        self.ledManager = ledManager
        self.filename = filename
        # with open(filename) as f:
        #   with pingListLock:
        #     for line in f:
        #       line = line.replace("\n", "")
        #       pingObjects.append(PingObject(line))

    def loadFile(self):
      with open(self.filename) as f:
        with pingListLock:
          del pingObjects[:]
          for line in f:
              line = line.replace("\n", "")
              pingObjects.append(PingObject(line))

    def numberOfPingInError(self):
      errorPings = 0
      with pingListLock:
        for ping in pingObjects:
          if ping.state == False:
              errorPings += 1

      return errorPings

    def numberOfPingInList(self):
      with pingListLock:
        return len(pingObjects)
        

    def run(self):
        while not self.Terminated:
          self.loadFile()
          with pingListLock:
            for ping in pingObjects:
              response = os.system("ping -c 1 -w 2 " + ping.ip)
              if response == 0:
                  ping.state = True
              else:
                  ping.state = False

          pingsInError = self.numberOfPingInError()
          if pingsInError != 0:
            self.ledManager.displayErrorSequence(activated=True)
          else:
            self.ledManager.displayErrorSequence(activated=False)

          if pingsInError == self.numberOfPingInList():
            self.ledManager.displayOKSequence(activated=False)
          else:
            self.ledManager.displayOKSequence(activated=True)
          
          time.sleep(NEW_PING_INTERVAL_TIME_S)  
    def stop(self): 
      self.Terminated = True


class LedManager(Thread):

    def __init__(self, R_Pin, G_Pin, B_Pin):
      self.Terminated = False
      Thread.__init__(self)
      GPIO.setup(R_Pin, GPIO.OUT)
      GPIO.setup(G_Pin, GPIO.OUT)
      GPIO.setup(B_Pin, GPIO.OUT)
      
      self.r= GPIO.PWM(R_Pin, 75)  # channel=R_Pin frequency=75Hz
      self.r.start(0)

      self.g= GPIO.PWM(G_Pin, 75)  # channel=G_Pin frequency=75Hz
      self.g.start(0)

      self.b= GPIO.PWM(B_Pin, 75)  # channel=B_Pin frequency=75Hz
      self.b.start(0)

      self.displayOKSeq = False
      self.displayErrorSeq = False
      self.displayBootSeq = False
      

    def bootSequence(self):      
      wait=0.005
      for dc in range(0, 101, 5):
        self.r.ChangeDutyCycle(dc)
        time.sleep(wait)

      for dc in range(0, 101, 5):
        self.g.ChangeDutyCycle(dc)
        time.sleep(wait)

      for dc in range(0, 101, 5):
        self.b.ChangeDutyCycle(dc)
        time.sleep(wait)

      for dc in range(100, -1, -5):
        self.r.ChangeDutyCycle(dc)
        time.sleep(wait)

      for dc in range(100, -1, -5):
        self.g.ChangeDutyCycle(dc)
        time.sleep(wait)

      for dc in range(100, -1, -5):
        self.b.ChangeDutyCycle(dc)
        time.sleep(wait)

    def errorSequence(self):      
      wait=0.05
      for dc in range(0, 101, 5):
        self.r.ChangeDutyCycle(dc)
        time.sleep(wait)

      time.sleep(wait * 10)

      for dc in range(100, -1, -5):
        self.r.ChangeDutyCycle(dc)
        time.sleep(wait)


    def okSequence(self):      
      wait=0.05
      for dc in range(0, 101, 5):
        self.g.ChangeDutyCycle(dc)
        time.sleep(wait)

      time.sleep(wait * 10)

      for dc in range(100, -1, -5):
        self.g.ChangeDutyCycle(dc)
        time.sleep(wait)

    def run(self):
        while not self.Terminated:

          if self.displayBootSeq == True:
            self.bootSequence()

          if self.displayOKSeq == True:
            self.okSequence()

          if self.displayErrorSeq == True:
            self.errorSequence()

          
          
          time.sleep(0) # Yield the thread

    def displayErrorSequence(self, activated):
      self.displayErrorSeq = activated

    def displayOKSequence(self, activated):
      self.displayOKSeq = activated

    def displayBootSequence(self, activated) :
      self.displayBootSeq = activated

    def stop(self):
      self.Terminated = True
      self.r.stop()
      self.g.stop()
      self.b.stop()
      GPIO.cleanup()


# Configuration parameters
# I2C Address, Port, Enable pin, RW pin, RS pin, Data 4 pin, Data 5 pin, Data 6 pin, Data 7 pin, Backlight pin (optional)
# below are correct settings for SainSmart IIC/I2C/TWI 1602 Serial LCD Module 
ledManager = LedManager(R_Pin=7, G_Pin=11, B_Pin=13)
ledManager.displayBootSequence(activated=True)

# If you want to disable the cursor, uncomment the following line
lcd.command(lcd.CMD_Display_Control | lcd.OPT_Enable_Display)
lcd.backLightOn()

pingTask = PingTask(filename=IP_TO_PINGS, ledManager=ledManager)
timeThread = LCDTime()
tempThread = LCDTemperature()
topThread = LCDTop(pingTask=pingTask)


ledManager.start()
pingTask.start()
timeThread.start()
tempThread.start()
topThread.start()
ledManager.displayBootSequence(activated=False)

def signal_handler(signal, frame):
        print('Killing threads...')
        timeThread.stop()
        topThread.stop()
        tempThread.stop()
        pingTask.stop()
        ledManager.stop()
        print('OK')
        with lcdLock:
          lcd.clear()
          lcd.backLightOff()
        sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)


ledManager.join()
timeThread.join()
topThread.join()
tempThread.join()
pingTask.join()

