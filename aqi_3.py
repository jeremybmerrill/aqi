#!/usr/bin/python3
# coding=utf-8
# "DATASHEET": http://cl.ly/ekot
# https://gist.github.com/kadamski/92653913a53baf9dd1a8
from __future__ import print_function
import serial
import struct, sys, time, json
from os.path import realpath, dirname, join
from datetime import datetime
#from display_letters import Flyover
import interface

DEBUG = False
SEND_STUFF_TO_INFLUXDB=False
CMD_MODE = 2
CMD_QUERY_DATA = 4
CMD_DEVICE_ID = 5
CMD_SLEEP = 6
CMD_FIRMWARE = 7
CMD_WORKING_PERIOD = 8
MODE_ACTIVE = 0
MODE_QUERY = 1

OUTPUT_FILENAME = join(dirname(realpath(__file__)), 'aqi-'+str(datetime.now())[0:19].replace(":", "_").replace(" ", "_")+'.json')
SLEEP_SECS = 60 # Oddly, with set to `20`, the script freezes inexplicably after 26 or 27 readings.
                # set to `60` it goes indefinitely


if SEND_STUFF_TO_INFLUXDB:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS

    # You can generate a Token from the "Tokens Tab" in the UI
    token = "y8ZpOwggwlkuHhkXmJieikx-s9d77ePlqq-X6lW03kURTv53tTsSGB12lQkQaXMSN1md4QwJ62KF3AemGETDoQ=="
    org = "influxdb@jeremybmerrill.com"
    bucket = "influxdb's Bucket"

    client = InfluxDBClient(url="https://us-east-1-1.aws.cloud2.influxdata.com", token=token)
    write_api = client.write_api(write_options=SYNCHRONOUS)

ser = serial.Serial(timeout=0)
ser.port = "/dev/ttyUSB0"
ser.baudrate = 9600

ser.open()
ser.flushInput()

byte, data = 0, ""


def dump(d, prefix=''):
    print(prefix + ' '.join(x for x in d))

def construct_command(cmd, data=[]):
    assert len(data) <= 12
    data += [0,]*(12-len(data))
    checksum = (sum(data)+cmd-2)%256
    ret = b"\xaa\xb4" + bytes([cmd])
    ret += b''.join(bytes([x]) for x in data)
    ret += b"\xff\xff" + bytes([checksum]) + b"\xab"

    if DEBUG:
        dump(ret, '> ')
    return ret

def process_data(d):
    r = struct.unpack('<HHxxBB', d[2:])
    pm25 = r[0]/10.0
    pm10 = r[1]/10.0
    checksum = sum(v for v in d[2:8])%256
    return [pm25, pm10]
    #print("PM 2.5: {} μg/m^3  PM 10: {} μg/m^3 CRC={}".format(pm25, pm10, "OK" if (checksum==r[2] and r[3]==0xab) else "NOK"))

def process_version(d):
    r = struct.unpack('<BBBHBB', d[3:])
    checksum = sum(v for v in d[2:8])%256
    print("Y: {}, M: {}, D: {}, ID: {}, CRC={}".format(r[0], r[1], r[2], hex(r[3]), "OK" if (checksum==r[4] and r[5]==0xab) else "NOK"))

def read_response():
    byte = 0
    counter = 9600
    while byte != b"\xaa":
        byte = ser.read(size=1)
        counter -= 1
        if counter <= 0:
            return None

    d = ser.read(size=9)

    if DEBUG:
        dump(d, '< ')
    return byte + d

def cmd_set_mode(mode=MODE_QUERY):
    ser.write(construct_command(CMD_MODE, [0x1, mode]))
    read_response()

def cmd_query_data():
    ser.write(construct_command(CMD_QUERY_DATA))
    d = read_response()
    values = []
    if d and d[1] == b"\xc0"[0]:
        values = process_data(d)
    return values

def cmd_set_sleep(sleep=1):
    mode = 0 if sleep else 1
    ser.write(construct_command(CMD_SLEEP, [0x1, mode]))
    read_response()

def cmd_set_working_period(period):
    ser.write(construct_command(CMD_WORKING_PERIOD, [0x1, period]))
    read_response()

def cmd_firmware_ver():
    ser.write(construct_command(CMD_FIRMWARE))
    d = read_response()
    process_version(d)

def cmd_set_id(id):
    id_h = (id>>8) % 256
    id_l = id % 256
    ser.write(construct_command(CMD_DEVICE_ID, [0]*10+[id_l, id_h]))
    read_response()


if __name__ == "__main__":
    try:
        interface = interface.RpiInterface()

        past_values = []
        while True:
            print("starting over")
            cmd_set_sleep(0)
            cmd_set_mode(1);

            recent_2_5 = []
            recent_10 = []

            for t in range(15):
                values = cmd_query_data();
                if values and values != [0,0]:
                    print("PM2.5: {} μg/m³, PM10: {} μg/m³".format(values[0], values[1]))
                    recent_2_5.append(values[0])
                    recent_10.append(values[1])
                    time.sleep(2)

            if len(recent_10) and len(recent_2_5):
                avg_2_5 = sum(recent_2_5) / len(recent_2_5)
                avg_10  = sum(recent_10)  / len(recent_10)

                if SEND_STUFF_TO_INFLUXDB:
                    # for some reason, it fails if I send floats
                    # I can't reproduce in the REPL.
                    point = Point("mem")\
                      .tag("host", "aqi")\
                      .field("2.5μg/m³", int(avg_2_5))\
                      .time(datetime.utcnow(), WritePrecision.S)
                    try:
                        write_api.write(bucket, org, point)
                        print("wrote to influxdb {}".format(avg_2_5))
                    except Exception:
                        print("couldn't send to influxdb,ignoring")
                    # for some reason, it fails if I send floats
                    # I can't reproduce in the REPL.
                    point = Point("mem")\
                      .tag("host", "aqi")\
                      .field("10μg/m³", int(avg_10))\
                      .time(datetime.utcnow(), WritePrecision.S)
                    try:
                        write_api.write(bucket, org, point)
                        print("wrote to influxdb {}".format(avg_10))
                    except Exception:
                        print("couldn't send to influxdb,ignoring")
                print()
                print("PM2.5: {} μg/m³ (avg), PM10: {} μg/m³ (avg)".format(round(avg_2_5,3), round(avg_10,3)))
                print()


            # check if length is more than 100 and delete first element
            if len(past_values) > 100:
                past_values.pop(0)

            if len(values) >= 2:
                # append new values
                past_values.append({'pm25': values[0], 'pm10': values[1], 'time': time.strftime("%d.%m.%Y %H:%M:%S")})

            # save it
            with open(OUTPUT_FILENAME, 'w') as outfile:
                json.dump(past_values, outfile)

            print("Going to sleep for {}:{}...".format(SLEEP_SECS/60, '{0:02d}'.format(SLEEP_SECS%60)))
            cmd_set_mode(0);
            cmd_set_sleep(1)
            if len(recent_10) and len(recent_2_5):
                print("trying to literally show .{:3d}".format(int(round(avg_2_5))))
                print("trying to literally show |{:3d}".format(int(round(avg_10))))
                interface.render_main(int(round(avg_2_5)), int(round(avg_10)))
                time.sleep(SLEEP_SECS)
            else:
                time.sleep(SLEEP_SECS)
    except Exception as e:
        ser.close()
        raise e
else:
    print("name not main", __name__)
