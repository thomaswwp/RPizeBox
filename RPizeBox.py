#!/usr/bin/python
#
#    pyLirc, lirc (remote control) module for python
#    Copyright (C) 2003 Linus McCabe <pylirc.linus@mccabe.nu>
#
#    pylms
#    https://github.com/jingleman/PyLMS
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 3.0 of the License, or (at your option) any later version.
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
#    You'll also need:
#       - Logitech Media Server (http://www.mysqueezebox.com/download)
#         or http://thomas.w-p.me.uk/blog/2013/01/raspberry-pi-as-squeezebox-server-logitech-media-server-with-spotify/
#         if you want spotify premium
#       - SqueezeLite  (https://code.google.com/p/squeezelite/)
#       - lirc set up with your remote as the lirc.conf from - http://lirc.sourceforge.net/remotes/
#
#
###################################################################################
# 
# This is the code to show the display, check whether the IR has been pressed
# and see if we need a smooth reboot or shutdown
#
# 0.0.1  Initial release, playing around with git
#
###################################################################################



#######################################################################
#                       import modules                                #
#######################################################################
import logging
import wiringpi2 as wp		    # to control display - https://github.com/Gadgetoid/WiringPi2-Python
import time, datetime           # for delays and date
import pylirc, time             # to talk to remote control
import sys, os                  # to talk to the RPi
import commands                 # to get the IP address
import fcntl, socket, struct    # to get the mac address

# need the directory for logging
currDir = os.path.dirname(os.path.realpath(__file__))

#set up logging
logging.basicConfig(filename=currDir+'/RPizeBox.log',level=logging.DEBUG,format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

# Originals at https://github.com/jingleman/PyLMS but I made minor change to allow accented characters in server.py
# import the pylms modules
from pylms.server import Server # to talk to LMS server
from pylms.player import Player # to talk to LMS player


#login details for the LMS (SqueezeLite)
scPort = 9090               # default LMS port for CLI
scUser = ""                 # CLI user
scPassword = ""             # CLI password
logInWait = 5               # time in seconds to wait between LMS login attempts
loggedin = False            # assume we are not logged in...
whatToShow = 0              # 0 = Artist, 1 = Album, 2 = Position/Length
bottomLineCycleDelay = 3    # time in seconds for bottom line rotation

#for pylirc
blocking = 0;                       # no idea what this does, but in the demo code!
configFile = "/remoteCodes.conf"    # has the codes we'll respond to
pylircReadDelay = 0.1               # how long to wait between responses

#some messages          = "123456789ABCDEF0"
welcomeMessage1         = "   Welcome to   "
welcomeMessage2         = "TWW-P's RPizeBox"


#######################################################################
#                            FUNCTIONS                                #
#######################################################################


# to get the mac address
#http://stackoverflow.com/questions/159137/getting-mac-address
def getHwAddr(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', ifname[:15]))
    return ''.join(['%02x:' % ord(char) for char in info[18:24]])[:-1]
    
# to get the IP address
# http://stackoverflow.com/questions/6243276/how-to-get-the-physical-interface-ip-address-from-an-interface
# I could use 127.0.0.1 but I like this better
def getExternalIP(ifname):
    intf = 'eth0'
    intf_ip = commands.getoutput("ip address show dev " + intf).split()
    intf_ip = intf_ip[intf_ip.index('inet') + 1].split('/')[0]
    return intf_ip


#######################################################################
#                          END FUNCTIONS                              #
#                                                                     #


    
#######################################################################
#                            INITIALISE                               #
#######################################################################
#                                                                     #


# set up the 16x2 display - 4 bit to save pins - apparently slower but marginal
# https://projects.drogon.net/raspberry-pi/wiringpi/lcd-library/
wp.wiringPiSetup();
lcd = wp.lcdInit (2, 16, 4,  11,10 , 0,1,2,3,0,0,0,0)
wp.lcdClear(lcd)		    # clear the lcd
wp.lcdPosition(lcd, 0, 0)	# cursor to start of row
    
# connect to the LMS
sc = Server(hostname=getExternalIP("eth0"), port=scPort, username=scUser, password=scPassword)
    
# log in to the LMS server - can't do much until that has happened.
while loggedin != True:
    try:
        sc.connect()    #throws ugly error if LMS not there
        loggedin = sc.logged_in
        logging.debug('Logged in to LMS.')
    except:
        logging.debug('LMS not there.  Trying again in %i seconds.' % logInWait)
        wp.lcdPosition(lcd, 0, 0)
        wp.lcdPuts(lcd,welcomeMessage1[:16])
        wp.lcdPosition(lcd, 0, 1)
        wp.lcdPuts(lcd,welcomeMessage2[:16])        
        time.sleep(logInWait)

        
# connected to server, now set up the player
# we know it is the RPi because we nab the local H/W address
sl = sc.get_player(getHwAddr("eth0"))	# http://stackoverflow.com/questions/159137/getting-mac-address
logging.debug('Logged in to player.')

#######################################################################
#                          END INITIALISE                             #
#                                                                     #
    
# no idea what blocking is
pylircConfigFile = "/remoteCodes.conf"


# start looking for remote control calls
if(pylirc.init("pylirc", currDir + pylircConfigFile, blocking)):
    elapsed_time = 0
    start_time = time.time()  
    
    code = {"config" : ""}
    while(code["config"] != "quit"):

        # Very intuitive indeed :: TWWP - not my comment, think I should know what blocking means!
        if(not blocking):
            # how long since we started
            elapsed_time = time.time() - start_time
            if (sl.get_mode() == 'play'):
                waitCount = 0 
                try:
                    #logging.debug('Elapsed time: %f' % elapsed_time)
                    wp.lcdPosition(lcd, 0, 1)
                    # no switch in python!
                    if(whatToShow == 0 and elapsed_time >= bottomLineCycleDelay and elapsed_time < (bottomLineCycleDelay * 2)):
                        wp.lcdPuts(lcd,(sl.get_track_artist() + " "*16)[:16])
                        
                    elif(whatToShow == 1 and elapsed_time >= (bottomLineCycleDelay * 2) and elapsed_time < (bottomLineCycleDelay * 3)):
                        wp.lcdPuts(lcd,(sl.get_track_album() + " "*16)[:16])
                        
                    elif(whatToShow == 2 and  elapsed_time >= (bottomLineCycleDelay * 3) and elapsed_time < (bottomLineCycleDelay * 4)):
                        wp.lcdPosition(lcd, 0, 1)  
                        elapsed = sl.get_time_elapsed()
                        total = sl.get_track_duration()
                        progress = int(9 * elapsed / total)
                        wp.lcdPuts(lcd,">" + ">"*(progress+1)+"-"*(8-progress) + " " + str(datetime.timedelta(seconds=int(total)))[-5:])    
                        start_time = time.time()   
                        
                    whatToShow += 1
                    if (whatToShow == 3):
                        whatToShow = 0
                except:
                    wp.lcdPuts(lcd,"      -++-      "[:16])          
                # title scrolling



            # Delay between reads?
            time.sleep(pylircReadDelay)

            
            
            
        #######################################################################
        #                          RESPOND TO REMOTE                          #
        #######################################################################    
        
        # Read next code
        s = pylirc.nextcode(1)

        # Loop as long as there are more on the queue
        # (dont want to wait pylircReadDelay if the user pressed many buttons...)
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
                
        #######################################################################
        #                       END RESPOND TO REMOTE                         #
        #                                                                     #
           

    # Clean up lirc
    pylirc.exit()

