import os
import threading
from threading import Thread
import time
from datetime import datetime
from time import sleep
import signal
import sys
import RPi.GPIO as GPIO
from collections import deque
from queue import Queue
#import queue

# following are the setting
pwmPin = 12 #Pin with PWM capability please reference https://pinout.xyz/pinout/pin33_gpio12
pwmPin2 = 13 #Pin with PWM capability please reference https://pinout.xyz/pinout/pin33_gpio13 or None if no second fan
#tachoPin = 6 #Pin where the tacho is plugged in
desiredTemp = 45
maxTemp = 65 #At this temperature the fan will run at 100%
threshold = 15 #Percentage threshold how low the fan can run. 15 works for Noctua A4x10. Other fans need to be checked
rpmReadCycle = 100 #How often should the frequency from the tachometer be checked. The higher the more accurate but the longer it takes.
rpmFilePath = "rpm" #Path to where a file with the rpm number should be saved. So other apps can access it.
repeatInSec = 2 #How often should the measurement takes place. Every X seconds.

# Don't change, only if needed
pTemp = (maxTemp - desiredTemp) / 100.0 
dutyAverage = 0
pwmDuty = 100
pwmctr = None
pwmctr2 = None
rpmThread = None
tQueue = None
lastLogs = deque([])

# second thread for Tachometer
class FreqThread(threading.Thread):
	def __init__(self, queue, tempPin, rpmReadCycle, filepath, args=(), kwargs=None):
		global tpin
		threading.Thread.__init__(self, args=(), kwargs=None)
		self.queue = queue
		self.tpin = tempPin
		self.cycle = rpmReadCycle
		GPIO.setup(self.tpin, GPIO.IN)
		self.fpath = filepath
		

	def run(self):
		while self.queue.empty():
			self.getRPM()
			sleep(1)
	
	def getRPM(self):
		startedAt = time.time()
		pinread = None
		for c in range(self.cycle):
			pinread = GPIO.wait_for_edge(self.tpin, GPIO.FALLING, timeout=1000)
			if pinread is None:
				break
		self.rpmFile = open(self.fpath, "w")
		if pinread is None:
			print("Frequenzy~: 0Hz | RPM~: 0")
			self.rpmFile.write("0")
			self.rpmFile.close()
			return
		duration = time.time() - startedAt
		frequency = self.cycle / duration
		rpm = int(frequency / 2 * 60)
		self.rpmFile.write(str(rpm))
		self.rpmFile.close()
		print("Frequenzy~: {:3.2f} | RPM~: {:4d}".format(frequency, rpm))
		

#sets some initial data
def setup():
	global pwmctr, pwmctr2, tQueue
	tQueue = Queue();
	GPIO.setwarnings(False)
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(pwmPin, GPIO.OUT)	
	pwmctr=GPIO.PWM(pwmPin,100)
	pwmctr.start(100)
	if not pwmPin2 is None:
		GPIO.setup(pwmPin2, GPIO.OUT)
		pwmctr2=GPIO.PWM(pwmPin2,100)
		pwmctr2.start(100)

	#rpmThread = FreqThread(tQueue, tachoPin, rpmReadCycle, rpmFilePath, None)
	#rpmThread.start()
	return();
def getCPUtemp(): #reads the cpu temperature from the temp file
	f = open('/sys/class/thermal/thermal_zone0/temp', 'r')
	res = f.readline()
	f.close()
	temp = float(res) / 1000
	return temp
def changeDuty(): #calculates the needed PWM duty and changes it
	global sum, pwmDuty, pwmctr, pwmctr2, dutyAverage, mWaited, lastLogs
	temp = getCPUtemp()
	diff = temp-desiredTemp
	pDiff = 0
	if diff > 0:
		pDiff = diff / pTemp
	pwmDuty = int(pDiff)
	dutyAverage = (dutyAverage + pwmDuty) / 2 #Average for getting the fan faster then needed so the desired temperature can be reached even under load
	pwmDuty = pwmDuty + dutyAverage
	if pwmDuty > 100:
		pwmDuty = 100
	if pwmDuty < threshold and pwmDuty > 8:
		pwmDuty = threshold;
	elif pwmDuty < threshold and pwmDuty <= 8:
		pwmDuty = 0
	pwmctr.ChangeDutyCycle(pwmDuty)
	if not pwmctr2 is None:
		pwmctr2.ChangeDutyCycle(pwmDuty)
	logEntry = datetime.now().strftime("%Y/%m/%d %H:%M:%S") + " - actualTemp {:4.2f} TempDiff {:4.2f} pDiff {:4.2f} pwmDuty {:5.0f}".format(temp, diff, pDiff, pwmDuty)
	print(logEntry)
	lastLogs.append(logEntry)
	if len(lastLogs) > 10:
		lastLogs.popleft()
	logFile = open('/home/lander/logs/fansStats.txt', 'w')
	for logEntry in lastLogs:
		print(logEntry, file = logFile)
	logFile.close()
	return()
def fanOFF():
	global pwmctr, pwmctr2
	pwmctr.ChangeDutyCycle(0)
	if not pwmctr2 is None:
		pwmctr2.ChangeDutyCycle(0)
	return

try:
	setup()
	fanOFF()
	
	while True:
		changeDuty()
		sleep(repeatInSec)
except KeyboardInterrupt: # trap a CTRL+C keyboard interrupt 
	print("Wait for thread to be stopped")
	tQueue.put(None)
	fanOFF()
	GPIO.cleanup()
