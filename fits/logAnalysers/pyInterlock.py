#!/usr/bin/env python

"""Arduino Interlock monitor
 * pyInterlock.py
 * Python module for the Arduino Interlock Box
 *
 * Author: Akos Hoffmann <akos.hoffmann@gmail.com>
 * 
 * 
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details. 
"""
 
__version__ = '1.0.0'
__date__ = '2015-11-13'
__all__ = ["ArdInterlock"]

import socket
import sys
import struct
import time

class ARD_Interlock:
    """Use this class to communicate with the Arduino Interlock Box"""
    
    
    def __init__(self, HOST='192.168.19.84', PORT = 8888, DEBUG = False):
        self.host = HOST
        self.port = PORT
        self.timeout = 5
        self.debug = DEBUG
        #self.sock=''
        
    def calcCrc16Str(self,inputstring):
        """Adapted from MinimalModbus"""
        POLY = 0xA001                  # Constant for MODBUS CRC-16
        register = 0xFFFF              # Preload a 16-bit register with ones
        for character in inputstring:
            register = register ^ ord(character)           # XOR with each character
            for i in range(8):                             # Rightshift 8 times, and XOR with polynom if carry overflows
                carrybit = register & 1
                register = register >> 1
                if carrybit == 1:
                    register = register ^ POLY
        result = struct.pack('<H', register)
        return result
        
    def SendUDP(self, function=chr(128), data='\xff\xff\x00\x00'): 
        try:
            message = function + data 
            message = self.calcCrc16Str(message) + message  
            if self.debug:
                print 'DEBUG>>> '+ 'Sending "%s"' % ':'.join(hex(ord(x))[2:] for x in message)
                print "UDP target IP:", self.host
                print "UDP target port:", self.port
            
            sock = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP
            sock.sendto(message, (self.host, self.port))     
        except:
           print 'error'

    def SendAndReceiveUDP(self, function=chr(128), data='\xff\xff\x00\x00', timeout=2.50): 
        try:
            message = function + data 
            message = self.calcCrc16Str(message) + message  
            if self.debug:
                print 'DEBUG>>> '+ 'Sending "%s"' % ':'.join(hex(ord(x))[2:] for x in message)
                print "UDP target IP:", self.host
                print "UDP target port:", self.port
            
            sock = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP
            #sock.bind((self.host, self.port))         
            sock.settimeout(timeout)      
            sock.sendto(message, (self.host, self.port))
            data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
            if self.debug:
               print "received message:", data
        except socket.timeout:
            print "Write timeout on socket"
            
        except:
           print 'error'
        return data   
                       
    def SetSubnetMask(self, ip='255.255.0.0'): 
        return self.SendAndReceiveUDP(function=chr(128), data= ''.join([chr(int(x)) for x in ip.split('.')]))      

    def SetIP(self, ip='192.168.1.99'): 
        return self.SendAndReceiveUDP(function=chr(129), data= ''.join([chr(int(x)) for x in ip.split('.')]))
        
    def SetGW(self, ip='0.0.0.0'): 
        return self.SendAndReceiveUDP(function=chr(130), data= ''.join([chr(int(x)) for x in ip.split('.')]))

    def SetDNS(self, ip='0.0.0.0'): 
        return self.SendAndReceiveUDP(function=chr(131), data= ''.join([chr(int(x)) for x in ip.split('.')]))
        
    def SetMAC(self, mac='90-A2-DA-0F-46-EE'): 
        return self.SendAndReceiveUDP(function=chr(132), data= ''.join([chr(int('0x'+x,16)) for x in mac.split('-')]))
        
    def SetPort(self, p=8888): 
        return self.SendAndReceiveUDP(function=chr(135), data=struct.pack('H',p))     

    def SetSerialNum(self, s=1): 
        return self.SendAndReceiveUDP(function=chr(133), data= struct.pack('l', s))  

    def DebugOn(self): 
        return self.SendAndReceiveUDP(function=chr(140), data='')  

    def DebugOff(self): 
        return self.SendAndReceiveUDP(function=chr(141), data='')  

    def Reset(self):
        return self.SendAndReceiveUDP(function=chr(136), data='')  
        
    def Write_New_Config(self):
        return self.SendAndReceiveUDP(function=chr(137), data='')  
          
    def SetName(self, name='Interlock Box 1'): 
        return self.SendAndReceiveUDP(function=chr(134), data= name+chr(0))

    def SetThreshold(self, ch=0, value=900): 
        return self.SendAndReceiveUDP(function=chr(3), data=struct.pack('<Bh',ch,value))

    def GetThreshold(self, ch=0): 
        return self.SendAndReceiveUDP(function=chr(2), data=chr(ch))
        
    def SetChName(self, ch=0, name='Unused'): 
        return self.SendAndReceiveUDP(function=chr(5), data=struct.pack('B10s',ch,name))

    def GetChName(self, ch=0): 
        return self.SendAndReceiveUDP(function=chr(4), data=chr(ch))

    def GetTemp(self, ch=0): 
        return self.SendAndReceiveUDP(function=chr(1), data=chr(ch))

    def GetChStatus(self, ch=0): 
        return self.SendAndReceiveUDP(function=chr(6), data=chr(ch))

    def GetAlarm(self): 
        return self.SendAndReceiveUDP(function=chr(7), data='')
        
    def PleaseSilent(self): 
        return self.SendAndReceiveUDP(function=chr(8), data='')        
        
    def isAlarm(self,ch=0):
        """returns true if channel is alarm high, false otherwise """
        try:
            binaryOutput = int(self.GetAlarm())
        except ValueError:
            binaryOutput = 0
        return (binaryOutput&(2**ch)!=0)

if __name__ == '__main__':
#    import argparse
#    parser = argparse.ArgumentParser()
#    parser.add_argument("-ip",  help="the IP (default: 192.168.19.84)", default="192.168.19.84")
#    parser.add_argument("-port", type=int, help="the UDP port (default: 8888)", default=8888)
#    args = parser.parse_args()
#    print args
    #ILB = ARD_Interlock( HOST=args.ip, PORT = args.port, DEBUG=True)
    #ILB = ARD_Interlock( HOST=args.ip, PORT = args.port, DEBUG=False)
    ILB = ARD_Interlock( HOST='192.168.16.23', PORT = 8888, DEBUG=False)
   
    
    print 'Fired Channels: {}'.format(bin(int(ILB.GetAlarm())))
    for i in range(15):
       print 'Ch.Nr.:{:3d} Name: \'{:16s}\' Threshold: {:3s} Status: {:4s} Temp. {:7s}'.format(i, ILB.GetChName(i), ILB.GetThreshold(i), ILB.GetChStatus(i), ILB.GetTemp(i)) 

    time.sleep(0.1)
    for i in range(15):
       print i
       print ILB.GetChName(i)
       print ILB.GetThreshold(i)
       print ILB.GetChStatus(i)
       print ILB.GetTemp(i)

#    ILB.PleaseSilent()


    """Use this part to write the config parameters in the EEPROM of a new hardware.

    #ILB = ARD_Interlock( HOST='192.168.19.84', PORT = 8888, DEBUG=True)  #the original IP is '192.168.19.84'
    ILB.SetIP(         ip='192.168.16.22')
    ILB.SetSubnetMask( ip='255.255.0.0')
    ILB.SetGW(         ip='0.0.0.0')
    ILB.SetDNS(        ip='0.0.0.0')
    ILB.SetMAC(        mac='90-A2-DA-0F-46-EE')
    ILB.SetPort(       p=8888)
    ILB.SetSerialNum(  s=1)
    ILB.SetName(       name='Interlock Box 1')
    Thresholds = [40, 40, 40, 40, 40, 50, 50, 50, 50, 50, 60, 60, 70, 70, 70, 70]
    ChNames = [ "FB Bot 1",
                "FB Bot 2",
                "FB Bot 3",
                "FB Top 1",
                "FB Top 2",
                "L2 Top",
                "MOT Bot",
                "MOT Top",
                "BZS 1",
                "BZS 2",
                "SZS 1",
                "SZS 2",
                "Unused 1",
                "Unused 2",
                "Unused 3",
                "Unused 4"]
    for i in range(len(Thresholds)):
        ILB.SetThreshold( ch = i, value = Thresholds[i] )
        ILB.SetChName( ch = i, name = ChNames[i])
    ILB.Write_New_Config()
    ILB.Reset()
    """



    

    


