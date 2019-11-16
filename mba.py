#\#!/usr/bin/env python3 -*- coding: utf-8 -*-

# Modbus/TCP server with start/stop schedule

import RPi.GPIO as GPIO

import argparse
import time
from pyModbusTCP.server import ModbusServer, DataBank
# need https://github.com/dbader/schedule
import schedule
toggle =1
toggleled=1
rollinghb=0
level = 0.0

import MCP342x
import smbus
bus = smbus.SMBus(1)
drv = MCP342x.MCP342x(bus,0x68,device='MCP3424',channel=0,gain=1,resolution=16, continuous_mode=True, scale_factor=1.0, offset=0.0)
drv.configure()

from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.virtual import viewport, sevensegment

serial = spi(port=0, device=0, gpio=noop())
device = max7219(serial, cascaded=1)
seg = sevensegment(device)
GPIO.setmode(GPIO.BCM)
GPIO.setup(4, GPIO.OUT)

def Tscale(value,raw_min,raw_max,eng_min,eng_max):
    return (value-raw_min)*(eng_max-eng_min)/(raw_max-raw_min)+eng_min

def show_message_vp(device, msg, delay=0.2):
    # Implemented with virtual viewport
    width = device.width
    padding = " " * width
    msg = padding + msg + padding
    n = len(msg)

    virtual = viewport(device, width=n, height=8)
    sevensegment(virtual).text = msg
    for i in reversed(list(range(n - width))):
        virtual.set_position((i, 0))
        time.sleep(delay)

# word @0 = second since 00:00 divide by 10 to avoid 16 bits overflow
def tled():
    global toggleled
    global rollinghb
    
    
    if toggleled ==1:
        GPIO.output(4, GPIO.HIGH)
        toggleled=0
    else:
        GPIO.output(4, GPIO.LOW)
        toggleled =1

    if rollinghb<9999:
        rollinghb += 1
    else:
        rollinghb =0
    

    DataBank.set_words(0,[abs(rollinghb)])
def ipmsg():
#   show_message_vp(device, "IP ADR 10.0.0.178")
    seg.text="A10.0.0.178"
def alive_word_job():
    global toggle
    global level
#    DataBank.set_words(0, [int(time.time()) % (24*3600) // 10])
    voltage =0.1
    try:
        voltage = abs(drv.read())
        DataBank.set_words(1,[int(voltage*10000)])
        ma=(voltage)/120.0*1000.0
        distance = Tscale(ma,4.0,20.0,350,3000)+8  #8is offset
        DataBank.set_words(2,[int(ma*1000)])
        DataBank.set_words(3,[int(distance)])
        DataBank.set_words(4,[int(2400-distance)])#Level of Water
        level = (2400-distance)/2400 *100.0
        DataBank.set_words(5,[int(level*100)])
    except:
        pass
    if toggle ==1:
        seg.text = 'LVL=%04.1fP' % (level)
        toggle=0
    else:
        seg.text = 'SEN=%01.2fV' % (voltage)
        toggle = 1

#how_message_vp(device,"Voltage "+ str(test))
if __name__ == "__main__":
    # parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("-H", "--host", type=str, default="10.0.0.178", help="Host")
    parser.add_argument("-p", "--port", type=int, default=502, help="TCP port")
    args = parser.parse_args()
    # init modbus server and start it
    server = ModbusServer(host=args.host, port=args.port, no_block=True)
    server.start()
    # init scheduler
    # schedule a daily downtime (from 18:00 to 06:00)
    #schedule.every().day.at("18:00").do(server.stop)
    #schedule.every().day.at("06:00").do(server.start)
    # update life word at @0
    schedule.every(5).seconds.do(alive_word_job)
#    schedule.every(30).seconds.do(ipmsg)
    schedule.every(1).seconds.do(tled)
    # main loop
    while True:
        schedule.run_pending()
        time.sleep(1)
	
