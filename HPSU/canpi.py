#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# v 0.0.3 by Vanni Brutto (Zanac)

import sys
import getopt
import time
import configparser
import logging
try:
    import can
except Exception:
    pass

class CanPI(object):
    hpsu = None
    timeout = None
    retry = None
    def __init__(self, hpsu=None):
        self.hpsu = hpsu
        try:
            # TODO evaluate can.ThreadSafeBus
            self.bus = can.interface.Bus(channel='can0', bustype='socketcan')
        except Exception:
            self.hpsu.logger.exception('Error opening bus can0')
            sys.exit(os.EX_CONFIG)
            
        config = configparser.ConfigParser()
        iniFile = '%s/%s.conf' % (self.hpsu.pathCOMMANDS, "pyhpsu")
        config.read(iniFile)
        self.timeout = float(self.get_with_default(config=config, section="CANPI", name="timeout", default=0.05))
        self.retry = float(self.get_with_default(config=config, section="CANPI", name="retry", default=15))
            
    
    def get_with_default(self, config, section, name, default):
        if "config" not in config.sections():
            return default
        if config.has_option(section,name):
            return config.get(section,name)
        else:
            return default
            
    def __del__(self):
        pass
        """try:
            self.bus.shutdown()
        except Exception:
            self.hpsu.logger.exception('Error shutdown canbus')"""
    
    def sendCommandWithID(self, cmd, setValue=None, priority=1):
        if setValue:
            receiver_id = 0x680
        else:
            receiver_id = int(cmd["id"], 16)
        command = cmd["command"]

        if setValue:
            command = command[:1] + '2' + command[2:]
            if command[6:8] != "FA":
                command = command[:3]+"00 FA"+command[2:8]
            command = command[:14]
            """ if cmd["unit"] == "deg":
                setValue = int(setValue)
                if setValue < 0:
                    setValue = 0x10000+setValue
                command = command+" %02X %02X" % (setValue >> 8, setValue & 0xff)"""
            if cmd["type"] == "longint" :
                setValue = int(setValue)
                command = command+" 00 %02X" % (setValue) 
            if cmd["type"] == "int":
                setValue = int(setValue)
                command = command+" %02X 00" % (setValue)
            if cmd["type"] == "float":
                setValue = int(setValue)
                if setValue < 0:
                    setValue = 0x10000+setValue
                command = command+" %02X %02X" % (setValue >> 8, setValue & 0xff)
            if cmd["type"] == "value":
                setValue = int(setValue)
                command = command+" %02X %02X" % (setValue >> 8, setValue & 0xff)
            
        msg_data = [int(r, 16) for r in command.split(" ")]
        notTimeout = True
        i = 0
        #print("sent: " + str(command))
        try:
            msg = can.Message(arbitration_id=receiver_id, data=msg_data, is_extended_id=False, dlc=7)
            self.bus.send(msg)
            self.hpsu.logger.debug("CanPI, %s sent: %s" % (cmd['name'], msg))

        except Exception:
            self.hpsu.logger.exception('Error sending msg')

        if setValue:
            return "OK"

        while notTimeout:
            i += 1
            timeout = self.timeout
            rcBUS = None
            try:
                rcBUS = self.bus.recv(timeout)
                
            except Exception:
                self.hpsu.logger.exception('Error recv')

            if rcBUS:
                if (msg_data[2] == 0xfa and msg_data[3] == rcBUS.data[3] and msg_data[4] == rcBUS.data[4]) or (msg_data[2] != 0xfa and msg_data[2] == rcBUS.data[2]):
                    rc = "%02X %02X %02X %02X %02X %02X %02X" % (rcBUS.data[0], rcBUS.data[1], rcBUS.data[2], rcBUS.data[3], rcBUS.data[4], rcBUS.data[5], rcBUS.data[6])
                    notTimeout = False
                    self.hpsu.logger.debug("CanPI %s, got: %s" % (cmd['name'], str(rc)))
                else:
                    self.hpsu.logger.warning('CanPI %s, SEND: %s' % (cmd['name'], str(msg_data)))
                    self.hpsu.logger.warning('CanPI %s, RECV: %s' % (cmd['name'], str(rcBUS.data)))
            else:
                self.hpsu.logger.warning('CanPI %s, Not aquired bus' % cmd['name'])

            if notTimeout:
                self.hpsu.logger.warning('CanPI %s, msg not sync, retry: %s' % (cmd['name'], i))
                if i >= self.retry:
                    self.hpsu.logger.error('CanPI %s, msg not sync, timeout' % cmd['name'])
                    notTimeout = False
                    rc = "KO"
        
        return rc
