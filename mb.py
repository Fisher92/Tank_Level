#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Modbus/TCP server with start/stop schedule

import argparse
import time
from pyModbusTCP.server import ModbusServer, DataBank
# need https://github.com/dbader/schedule
import schedule


import MCP342x
import smbus
bus = smbus.SMBus(1)
drv = MCP342x.MCP342x(bus,0x68,device='MCP3424',channel=0,gain=1,resolution=16, continuous_mode=True, scale_factor=1.0, offset=0.0)
drv.configure()



# word @0 = second since 00:00 divide by 10 to avoid 16 bits overflow
def alive_word_job():
    DataBank.set_words(0, [int(time.time()) % (24*3600) // 10])
    test=1.1
    test = abs(drv.read())*1000
    DataBank.set_words(1,[int(test)])

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
    schedule.every().day.at("18:00").do(server.stop)
    schedule.every().day.at("06:00").do(server.start)
    # update life word at @0
    schedule.every(1).seconds.do(alive_word_job)
    # main loop
    while True:
        schedule.run_pending()
        time.sleep(1)
	print 'running'
