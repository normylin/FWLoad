import sys, time, os
import power_control
from config import *
from pymavlink import mavutil

class FirmwareLoadError(Exception):
    '''firmload exception class'''
    def __init__(self, msg):
        Exception.__init__(self, msg)
        self.message = msg

def show_tail(logstr):
    '''show last lines of a log'''
    ofs = logstr.tell()
    logstr.seek(0)
    lines = logstr.readlines()
    n = 20
    if len(lines) < n:
        n = len(lines)
    for i in range(n):
        print(lines[len(lines)-n+i].rstrip())
    logstr.seek(ofs)

def show_error(test, ex, logstr):
    '''display an error then exit'''
    show_tail(logstr)
    raise(FirmwareLoadError("FAILED: %s" % test))

def wait_devices(devices, timeout=10):
    '''wait for devices to appear'''
    start_time = time.time()
    missing = []
    while start_time+timeout >= time.time():
        missing = []
        all_exist = True
        for dev in devices:
            if not os.path.exists(dev):
                all_exist = False
                missing.append(dev)
        if all_exist:
            return True
        time.sleep(0.1)
    print("Missing devices: %s" % missing)
    return False

def power_wait_devices(devices):
    '''wait for all needed JTAG devices'''
    retries = 5
    while retries > 0:
        retries -= 1
        power_control.power_cycle()
        print("Waiting for power up")
        if wait_devices(devices):
            time.sleep(1)
            return True
    failure("Failed to power up devices")
    return False

def failure(msg):
    '''show a failure msg and raise an exception'''
    print(msg)
    raise(FirmwareLoadError(msg))

def wait_field(refmav, msg_type, field):
    '''wait for a field value'''
    msg = None
    # get the latest available msg
    while True:
        msg2 = refmav.recv_match(type=msg_type, blocking=(msg==None))
        if msg2 is None:
            break
        msg = msg2
    return getattr(msg, field)

def param_value(test, pname):
    '''get a param value given a mavproxy connection'''
    test.send('param show %s\n' % pname)
    test.expect('%s\s+(-?\d+\.\d+)\r\n' % pname)
    return float(test.match.group(1))

def param_set(test, pname, value):
    '''get a param value given a mavproxy connection'''
    test.send('param set %s %f\n' % (pname, value))
    test.expect('>')

def set_servo(mav, servo, value):
    '''set a servo to a value'''
    mav.mav.command_long_send(0, 0,
                              mavutil.mavlink.MAV_CMD_DO_SET_SERVO, 0,
                              servo, value,
                              0, 0, 0, 0, 0)

def discard_messages(mav):
    '''discard any buffered messages'''
    while True:
        msg = mav.recv_msg()
        if msg is None:
            return

def wait_prompt(test):
    '''wait for mavproxy prompt, coping with multiple modes'''
    test.expect(IDLE_MODES)
