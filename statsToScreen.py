import time

import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

import subprocess
import smbus2
from ina219 import INA219, DeviceRangeError

# Raspberry Pi pin configuration:
RST = None     # on the PiOLED this pin isnt used
# Note the following are only used with SPI:
DC = 23
SPI_PORT = 0
SPI_DEVICE = 0
DEVICE_BUS = 1

DEVICE_ADDR  = 0x17
PROTECT_VOLT = 3700
SAMPLE_TIME = 2

ina_supply = INA219(0.00725, address=0x40)
ina_supply.configure()
supply_voltage = ina_supply.voltage()
supply_current = ina_supply.current()
supply_power = ina_supply.power()

ina_batt = INA219(0.005, address=0x45)
ina_batt.configure()
batt_voltage = ina_batt.voltage()
batt_current = ina_batt.current()
batt_power = ina_batt.power()


# Beaglebone Black pin configuration:
# RST = 'P9_12'
# Note the following are only used with SPI:
# DC = 'P9_15'
# SPI_PORT = 1
# SPI_DEVICE = 0

# 128x32 display with hardware I2C:
# disp = Adafruit_SSD1306.SSD1306_128_32(rst=RST)　　　####### please comment this line by adding hash tag in front of line #######

# 128x64 display with hardware I2C:  ##########################Please Open following line by removing hash tag ######
disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST)

# Note you can change the I2C address by passing an i2c_address parameter like:
# disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST, i2c_address=0x3C)

# Alternatively you can specify an explicit I2C bus number, for example
# with the 128x32 display you would use:
# disp = Adafruit_SSD1306.SSD1306_128_32(rst=RST, i2c_bus=2)

# 128x32 display with hardware SPI:
# disp = Adafruit_SSD1306.SSD1306_128_32(rst=RST, dc=DC, spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE, max_speed_hz=8000000))

# 128x64 display with hardware SPI:
# disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST, dc=DC, spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE, max_speed_hz=8000000))

# Alternatively you can specify a software SPI implementation by providing
# digital GPIO pin numbers for all the required display pins.  For example
# on a Raspberry Pi with the 128x32 display you might use:
# disp = Adafruit_SSD1306.SSD1306_128_32(rst=RST, dc=DC, sclk=18, din=25, cs=22)

# Initialize library.
disp.begin()

# Clear display.
disp.clear()
disp.display()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
image = Image.new('1', (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0,0,width,height), outline=0, fill=0)

# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = -2
top = padding
bottom = height-padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0


# Load default font.
font = ImageFont.load_default()

# Alternatively load a TTF font.  Make sure the .ttf font file is in the same directory as the python script!
# Some other nice fonts to try: http://www.dafont.com/bitmap.php
# font = ImageFont.truetype('Minecraftia.ttf', 8)

def getBus():
    # i2c bus configure
    print("Obtaining bus")
    bus = smbus2.SMBus(DEVICE_BUS)
    return bus;  # Return tuple, we could also
      

def getBusConfig(bus):
    # i2c bus configure
    try:
        aReceivedBuf = []
        aReceivedBuf.append(0x00)
        for i in range(1, 255):
            aReceivedBuf.append(bus.read_byte_data(DEVICE_ADDR, i))
        print("Obtained bus config")
    except IOError as e:
        #print("------IOError------")
        print ("IOError({0}): {1}".format(e.errno, e.strerror))
        #time.sleep(3)
        #return getBusAndConfig();
        return getBus(), None;

    return bus, aReceivedBuf;  # Return tuple, we could also
      

def getBusAndConfig():
    # i2c bus configure
    bus = getBus();
    bus, aReceivedBuf =  getBusConfig(bus);
    return bus, aReceivedBuf;  # Return tuple, we could also
      


bus, aReceivedBuf = getBusAndConfig()

while True:

    # Draw a black filled box to clear the image.
    draw.rectangle((0,0,width,height), outline=0, fill=0)

    # Shell scripts for system monitoring from here : https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
    #cmd = "hostname -I | cut -d\' \' -f1"
    #cmd = "hostnamectl hostname"
    cmd = "ip address show wlan0 | grep \"inet \" | cut -d\' \' -f6"

    IP = subprocess.check_output(cmd, shell = True )
    cmd = "top -bn1 | grep load | awk '{printf \"CPU Load: %.2f\", $(NF-2)}'"
    CPU = subprocess.check_output(cmd, shell = True )
    cmd = "cat /sys/devices/virtual/thermal/thermal_zone0/hwmon0/temp1_input"
    CPUTemp = float(subprocess.check_output(cmd, shell = True )) / 1000
    cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%sMB %.2f%%\", $3,$2,$3*100/$2 }'"
    MemUsage = subprocess.check_output(cmd, shell = True )
    cmd = "df -h | awk '$NF==\"/\"{printf \"Disk: %d/%dGB %s\", $3,$2,$5}'"
    Disk = subprocess.check_output(cmd, shell = True )
    # Write two lines of text.

    # Display image.
    #disp.image(image)
    #disp.display()
    #time.sleep(3)
    
    bus, aReceivedBuf =  getBusConfig(bus);

    batt_voltage = ina_batt.voltage()
    batt_current = ina_batt.current()
    batt_power = ina_batt.power()
    if aReceivedBuf is None:
        charge_port = ''
    elif (aReceivedBuf[8] << 8 | aReceivedBuf[7]) > 4000:
        charge_port = 'Type-C'
    elif (aReceivedBuf[10] << 8 | aReceivedBuf[9]) > 4000:
        charge_port = 'MicroUSB'
    else:
        charge_port = 'Not Charging'
    

    textList = []
    textList.append("IP: " + str(IP.decode('utf-8')))
    textList.append(str(CPU.decode('utf-8')) + " " + str('{:.1f}'.format(CPUTemp)) + "C")
    textList.append(str(MemUsage.decode('utf-8')))
    textList.append(str(Disk.decode('utf-8')))
    textList.append("Voltage: " + str('{:.3f}'.format(batt_voltage)) + " V")
    textList.append("Current: " + str('{:.3f}'.format(batt_current)) + " mA")
    textList.append("Power: " + str('{:.3f}'.format(batt_power)) + " mW")
    textList.append("ChargePort: " + str(charge_port))
    
    draw.rectangle((0,0,width,height), outline=0, fill=0)
    verticalOffset = 0
    for t in textList:
        draw.text((x, top + verticalOffset), t,  font=font, fill=255)
        verticalOffset += 8

    # display UPS information
    disp.image(image)
    disp.display()
    time.sleep(3)
