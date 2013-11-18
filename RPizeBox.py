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

###################################################################################
# 
# This is the code to show the display, check whether the IR has been pressed
# and see if we need a smooth reboot or shutdown
#
# 0.0.1     Initial release, playing around with git
#           Issues:
#               - lirc remembers two button presses and shows the volume images 
#               in flashes between the titles
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

# class to hold all the variables
class RPizeBox:
    scrollStepTime = 0.7        # how long to wait between steps when scrolling
    lastStepTime = 0            # when we last stepped
    delayOnLoop = 3             # time to wait when back to start on a scroll   
    scPort = 9090               # default LMS port for CLI
    scUser = ""                 # CLI user
    scPassword = ""             # CLI password
    logInWait = 5               # time in seconds to wait between LMS login attempts
    loggedin = False            # assume we are not logged in...
    whatToShow = 0              # 0 = Artist, 1 = Album, 2 = Position/Length
    bottomLineCycleDelay = 3    # time in seconds for bottom line rotation
    flashChange = 1.0           # time in seconds to show volume change etc.
    scrollPosition = 0          # starting position for the scroll
    current_title = ""          # current_title
    waitBeforeOffMinutes = 10   # time to wait before going to standby

# make an object to hold all these variables.  Not sure why but I suppose it is neater
RPizeBox = RPizeBox()


#for pylirc
# how long to wait between remote actions, check with console command "top"
##################################### 
pylircReadDelay = 0.1               # 0.05 ~ 9% overhead
##################################### 0.1  ~ 6% overhead
blocking = 0;                       # no idea what this does, but in the demo code!
configFile = "/remoteCodes.conf"    # has the codes we'll respond to

#some messages          = "123456789ABCDEF0", "123456789ABCDEF0"
welcomeMessage         = ["   Welcome to   ", "TWW-P's RPizeBox"]



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

######################### reset/reboot button #########################
# Best used in another script since it takes 30s to initialise
# 
os.chdir(os.path.dirname(os.path.realpath(__file__)))
os.system("python buttonWatch.py &")



########################### 16 x 2 display ############################
# set up the 16x2 display - 4 bit to save pins - apparently slower but marginal
# https://projects.drogon.net/raspberry-pi/wiringpi/lcd-library/
wp.wiringPiSetup();
lcd = wp.lcdInit (2, 16, 4,  11,10 , 0,1,2,3,0,0,0,0)
wp.lcdClear(lcd)		    # clear the lcd
wp.lcdPosition(lcd, 0, 0)	# cursor to start of row

################################# LMS ################################    
# connect to the LMS
sc = Server(hostname=getExternalIP("eth0"), port=RPizeBox.scPort, username=RPizeBox.scUser, password=RPizeBox.scPassword)
    
# log in to the LMS server - can't do much until that has happened.
while RPizeBox.loggedin != True:
    try:
        sc.connect()    #throws ugly error if LMS not there
        RPizeBox.loggedin = sc.logged_in
        logging.debug('Success: Logged in to LMS.')
    except:
        logging.debug('LMS not there.  Trying again in %i seconds.' % RPizeBox.logInWait)
        wp.lcdPosition(lcd, 0, 0)
        wp.lcdPuts(lcd,welcomeMessage[0][:16])
        wp.lcdPosition(lcd, 0, 1)
        wp.lcdPuts(lcd,welcomeMessage[1][:16])        
        time.sleep(RPizeBox.logInWait)

        
# connected to server, now set up the player
# we know it is the RPi because we nab the local H/W address
try:
    sl = sc.get_player(getHwAddr("eth0"))	# http://stackoverflow.com/questions/159137/getting-mac-address
    logging.debug('Success: In contact with SqueezeLite.')
except:
    logging.warning('Can\'t contact SqueezeLite!  Check it is running')
#######################################################################
#                          END INITIALISE                             #
#                                                                     #
    
# no idea what blocking is
pylircConfigFile = "/remoteCodes.conf"
track_title = ""

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
            
            # has track has changed
            #logging.debug('RPizeBox.current_title: %s, sl.get_track_title: %s' % (RPizeBox.current_title, sl.get_track_title()))
            if (RPizeBox.current_title != sl.get_track_title()):
                RPizeBox.scrollPosition = -1
                RPizeBox.lastStepTime = time.time()
                RPizeBox.current_title = sl.get_track_title()
                logging.debug('Track changed, now: %s' % RPizeBox.current_title)
                
            if (sl.get_mode() == 'play'):
                #logging.debug('Entered if (sl.get_mode() == \'play\'): loop')
                waitCount = 0 
                try:
                    wp.lcdPosition(lcd,0,0)
                    # scrolling code will go here
                    track_title = sl.get_track_title()
                    if (len(track_title) <= 16):
                        wp.lcdPuts(lcd,(sl.get_track_title() + " "*16)[:16])
                    else:
                        # this is where we scroll
                        track_title += " --- " + track_title[:16]  
                        
                        # cause delay if at start
                        if (RPizeBox.scrollPosition == -1):
                            RPizeBox.lastStepTime += RPizeBox.delayOnLoop 
                            RPizeBox.scrollPosition = 0    
                            wp.lcdPuts(lcd,track_title[RPizeBox.scrollPosition:16+RPizeBox.scrollPosition])
                            wp.lcdPosition(lcd, 0, 1)
                            wp.lcdPuts(lcd,(sl.get_track_artist() + " "*16)[:16])
  
                        if ((time.time() - RPizeBox.lastStepTime) > RPizeBox.scrollStepTime):
                            wp.lcdPuts(lcd,track_title[RPizeBox.scrollPosition:16+RPizeBox.scrollPosition])
                            RPizeBox.scrollPosition += 1
                            RPizeBox.lastStepTime = time.time()
                            
                        if (len(track_title) == 16+RPizeBox.scrollPosition):
                            #back to the start
                            RPizeBox.scrollPosition = -1
                         
                    
                    # move to second row
                    wp.lcdPosition(lcd, 0, 1)
                    # no switch in python so cycle through the bottom line based on timings
                    if(RPizeBox.whatToShow == 0 and elapsed_time >= RPizeBox.bottomLineCycleDelay and elapsed_time < (RPizeBox.bottomLineCycleDelay * 2)):
                        wp.lcdPuts(lcd,(sl.get_track_artist() + " "*16)[:16])
                        
                    elif(RPizeBox.whatToShow == 1 and elapsed_time >= (RPizeBox.bottomLineCycleDelay * 2) and elapsed_time < (RPizeBox.bottomLineCycleDelay * 3)):
                        wp.lcdPuts(lcd,(sl.get_track_album() + " "*16)[:16])
                        
                    elif(RPizeBox.whatToShow == 2 and  elapsed_time >= (RPizeBox.bottomLineCycleDelay * 3) and elapsed_time < (RPizeBox.bottomLineCycleDelay * 4)):
                        wp.lcdPosition(lcd, 0, 1)  
                        elapsed = sl.get_time_elapsed()
                        total = sl.get_track_duration()
                        progress = int(9 * elapsed / total)
                        wp.lcdPuts(lcd,">" + ">"*(progress+1)+"-"*(8-progress) + " " + str(datetime.timedelta(seconds=int(total)))[-5:])    
                        start_time = time.time()   
                        
                    RPizeBox.whatToShow += 1
                    if (RPizeBox.whatToShow == 3):
                        RPizeBox.whatToShow = 0
                except:
                    wp.lcdPosition(lcd, 0, 1)
                    wp.lcdPuts(lcd,"      -++-      "[:16])          
                # title scrolling
                
            # deal with pause/stop
            elif (sl.get_mode() == 'pause' or (sl.get_mode() == 'stop' and sl.get_power_state())):
                wp.lcdPosition(lcd, 0, 0)
                wp.lcdPuts(lcd,(sl.get_track_artist() + " "*16)[:16])
                wp.lcdPosition(lcd, 0, 1)  
                wp.lcdPuts(lcd,("     PAUSED" + " "*16)[:16])
                elapsed_time = time.time() - start_time
                if (elapsed_time >= (RPizeBox.waitBeforeOffMinutes * 60)): 
                    # send "OFF" message to player
                    sl.set_power_state(False)

            elif (not sl.get_power_state()):
                wp.lcdPosition(lcd, 0, 1)  
                wp.lcdPuts(lcd,"           " + time.strftime("%H:%M", time.gmtime())[:16])
                wp.lcdPosition(lcd, 0, 0)
                wp.lcdPuts(lcd,(datetime.datetime.now().strftime("%A") + " " + datetime.datetime.now().strftime("%d")+ " " + datetime.datetime.now().strftime("%B")[:3] + " "*16)[:16])
                
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
                    logging.debug("Volume is: " + str(sl.get_volume()))
                    # sl.get_volume() gives integer 0-100                   
                    wp.lcdPosition(lcd, 0, 1)
                    wp.lcdPuts(lcd,((chr(255)*int(0.16*sl.get_volume())) + " "*16)[:16])  
                    time.sleep(RPizeBox.flashChange)
                    
                elif(code["config"] == "Vol-"):
                    logging.debug("Vol-")
                    sl.volume_down()
                    logging.debug("Volume is: " + str(sl.get_volume()))
                    # sl.get_volume() gives integer 0-100                   
                    wp.lcdPosition(lcd, 0, 1)
                    wp.lcdPuts(lcd,((chr(255)*int(0.16*sl.get_volume())) + " "*16)[:16]) 
                    time.sleep(RPizeBox.flashChange)
                    
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

