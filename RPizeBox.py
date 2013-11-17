#!/usr/bin/python
#
#    pyLirc, lirc (remote control) module for python
#    Copyright (C) 2003 Linus McCabe <pylirc.linus@mccabe.nu>
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this library; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
##
#
#     This is a small and quite bad testprogram for the lirc module but
#     it's getting better...
#
#  $Id: pylirc_test.py,v 1.8 2003/02/22 22:51:01 mccabe Exp $
#  $Log: pylirc_test.py,v $
#  Revision 1.8  2003/02/22 22:51:01  mccabe
#  Previous, accidental commit:
#  Added Brian J. Murrell's code to fetch repeatcount
#
#  This commit:
#  Changed Brians code to return a dictionary instead of a list.
#  Removed lirc_nextcode_ext() and merged it with lirc_nextcode() - new optional argument controls return type. Old programs should work as
#  before and new programs can benefit the new behaviour by passing true as first argument.
#
#  Revision 1.7  2003/02/22 22:12:40  mccabe
#  Testprogram to test pylirc in multiple threads
#
#  Revision 1.6  2002/12/21 20:30:26  mccabe
#  Added id and log entries to most files
#
import logging

#set up logging
logging.basicConfig(filename='./remoteWatch.log',level=logging.DEBUG,format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')


import pylirc, time
import sys, os
#sys.path.append('/home/pi/PyLMS/')

from pylms.server import Server # to talk to LMS server
from pylms.player import Player # to talk to LMS player
scPort = 9090               # default LMS port for CLI
scUser = ""                 # CLI user
scPassword = ""             # CLI password
loggedin = False

# get the IP address
import commands
intf = 'eth0'
intf_ip = commands.getoutput("ip address show dev " + intf).split()
intf_ip = intf_ip[intf_ip.index('inet') + 1].split('/')[0]

# connect to the squeezebox
sc = Server(hostname=intf_ip, port=scPort, username=scUser, password=scPassword)

import fcntl, socket, struct	# to get mac address
# to get the mac address
def getHwAddr(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', ifname[:15]))
    return ''.join(['%02x:' % ord(char) for char in info[18:24]])[:-1]

while loggedin != True:
    try:
        sc.connect()
        loggedin = sc.logged_in
        #wp.lcdPuts(lcd,str(loggedin))
    except:
        time.sleep(3)
        
# set up the player
sl = sc.get_player(getHwAddr("eth0"))	# http://stackoverflow.com/questions/159137/getting-mac-address


# no idea what blocking is
blocking = 0;
configFile = "/remoteWatch.conf"
currDir = os.path.dirname(os.path.realpath(__file__))
logging.debug('Current working directory: ' + currDir)

#
if(pylirc.init("pylirc", currDir + configFile, blocking)):

   code = {"config" : ""}
   while(code["config"] != "quit"):

      # Very intuitive indeed
      if(not blocking):
         #print "."

         # Delay
         time.sleep(0.1)

      # Read next code
      s = pylirc.nextcode(1)

      # Loop as long as there are more on the queue
      # (dont want to wait a second if the user pressed many buttons...)
      while(s):
         
         # Print all the configs...
         for (code) in s:
         
            #print "Command: %s, Repeat: %d" % (code["config"], code["repeat"])
            
            if(code["config"] == "blocking"):
               blocking = 1
               pylirc.blocking(1)

            elif(code["config"] == "nonblocking"):
               blocking = 0
               pylirc.blocking(0)
               
            elif(code["config"] == "PowerToggle"):
                #print "Toggling!"
                #print sl.get_mode()
                if (sl.get_mode() == 'stop'):
                    logging.debug("Power ON")
                    sl.set_power_state(True)
                else:
                    logging.debug("Power OFF")
                    sl.set_power_state(False)
 
            elif(code["config"] == "Play"):
                logging.debug("Play")
                sl.play()
 
            elif(code["config"] == "Pause"):
                logging.debug("Pause")
                sl.pause() 
                
            elif(code["config"] == "Vol+"):
                logging.debug("Vol+")
                sl.volume_up() 
                
            elif(code["config"] == "Vol-"):
                logging.debug("Vol-")
                sl.volume_down()
                
            elif(code["config"] == "SkipForward" or code["config"] == "Tune+"):
                logging.debug("SkipForward")
                sl.next()
                
            elif(code["config"] == "SkipBackward" or code["config"] == "Tune-"):
                logging.debug("SkipBackward")
                sl.prev()
                
         # Read next code?
         if(not blocking):
            s = pylirc.nextcode(1)
         else:
            s = []

   # Clean up lirc
   pylirc.exit()

   
