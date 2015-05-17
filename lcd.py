#!/usr/bin/env python

import sys
sys.path.append('./quick2wire-python-api')

from i2clibraries import i2c_lcd
import datetime
import random
from threading import Thread, RLock
import time
import os
import signal
import json

lcdLock = RLock()
lcd = i2c_lcd.i2c_lcd(0x27,1, 2, 1, 0, 4, 5, 6, 7, 3)

pingListLock = RLock()
pingObjects = []

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

            time.sleep(0.10)

    def stop(self): 
      self.Terminated = True

class LCDTop(Thread):

    defectShow = False

    def __init__(self):
        Thread.__init__(self)
        self.Terminated = False 

    def run(self):
        while not self.Terminated:
            
            with pingListLock:
              flag = False
              for ping in pingObjects:
                flag = False
                if ping.state == False:
                  flag = True
                  with lcdLock:
                   lcd.setPosition(1, 0)
                   lcd.writeString("                ")
                   lcd.setPosition(1, 0)
                   lcd.writeString(ping.ip+" NOK ")
                if flag == True :
                  time.sleep(5)
            
            with lcdLock:
              if flag == True :
                lcd.setPosition(1, 0)
                lcd.writeString("                ")
              else:
                lcd.setPosition(1, 0)
                lcd.writeString("Pings OK !      ")
                time.sleep(5)

              lcd.setPosition(1, 0)
              now = datetime.datetime.now()
              lcd.writeString(now.strftime("%a %d %b %Y"))
              
            time.sleep(5)

    def stop(self): 
      self.Terminated = True



class LCDTemperature(Thread):

    def __init__(self):
        Thread.__init__(self)
        self.Terminated = False 

    def run(self):
        while not self.Terminated:
          data = json.loads('{"iT":"22.0","oT":"16.0","iH":"44.0","iP":"1003.2"}')
          with lcdLock:
              lcd.setPosition(2, 10)
              lcd.writeString(data['iT']+"°c")

         
          time.sleep(60)

    def stop(self): 
      self.Terminated = True

class PingObject:

    def __init__(self, ip):
      self.ip = ip
      self.state = False

    def isReachable():
      return self.state

class PingTask(Thread):

    def __init__(self, filename):
        Thread.__init__(self)
        self.Terminated = False
        
        with open(filename) as f:
          with pingListLock:
            for line in f:
              pingObjects.append(PingObject(line))

    def run(self):
        while not self.Terminated:
          with pingListLock:
            for ping in pingObjects:
              response = os.system("ping -c 1 " + ping.ip)
              if response == 0:
                  ping.state = True
              else:
                  ping.state = False
          
          time.sleep(5)

    def stop(self): 
      self.Terminated = True

# Configuration parameters
# I2C Address, Port, Enable pin, RW pin, RS pin, Data 4 pin, Data 5 pin, Data 6 pin, Data 7 pin, Backlight pin (optional)
# below are correct settings for SainSmart IIC/I2C/TWI 1602 Serial LCD Module 


# If you want to disable the cursor, uncomment the following line
lcd.command(lcd.CMD_Display_Control | lcd.OPT_Enable_Display)
lcd.backLightOn()

pingTask = PingTask(filename="ip.txt")
timeThread = LCDTime()
tempThread = LCDTemperature()
topThread = LCDTop()

pingTask.start()
timeThread.start()
tempThread.start()
topThread.start()

def signal_handler(signal, frame):
        print('Killing threads...')
        timeThread.stop()
        topThread.stop()
        tempThread.stop()
        pingTask.stop()
        print('OK')
        with lcdLock:
          lcd.clear()
          lcd.backLightOff()
        sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)



timeThread.join()
topThread.join()
tempThread.join()
pingTask.join()

