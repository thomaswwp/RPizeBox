import RPi.GPIO as GPIO
import os
import time
import logging
import wiringpi2 as wp		    # to control display

#set up logging
logging.basicConfig(filename='/home/pi/scripts/buttonwatch.log',level=logging.DEBUG,format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

#some messages          = "123456789ABCDEF0", "123456789ABCDEF0"
shutdownMessage        = ["Shutting down...", "  ...bye bye.   "]
rebootMessage          = ["Rebooting -     ", " Back in a mo..."]


# set up the display - 4 bit to save pins - apparently slower but marginal
# https://projects.drogon.net/raspberry-pi/wiringpi/lcd-library/
wp.wiringPiSetup();
lcd = wp.lcdInit (2, 16, 4,  11,10 , 0,1,2,3,0,0,0,0)

#delay 30 seconds to let things settle down!
logging.debug('Starting 30 second delay to let GPIO settle down...')
time.sleep(30)
logging.debug('...and continuing...')

#where the button is plugged in
buttonPin = 4

#time limits
accidental = 0.2
shutdown = 3

#set up GPIO
GPIO.setmode(GPIO.BCM)

# don't need ground lead?
GPIO.setup(buttonPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.add_event_detect(buttonPin, GPIO.RISING)  # add rising edge detection on a channel

try:
    while True:
        
        # stop it trashing the CPU
        time.sleep(0.1)
        
        elapsed_time = 0
        if GPIO.event_detected(buttonPin):
            start_time = time.time()
            
            while (GPIO.input(buttonPin)):
                time.sleep(0.2)
                elapsed_time = time.time() - start_time
                if (elapsed_time > shutdown):
                    logging.info('Shutting down... (Elapsed time: ' + str(elapsed_time)[:4] + ')')
                    os.system("kill $(pgrep -f RPizeBox.py)")
                    wp.lcdClear(lcd)
                    wp.lcdPosition(lcd, 0, 0)
                    wp.lcdPuts(lcd,shutdownMessage[0][:16])
                    wp.lcdPosition(lcd, 0, 1)
                    wp.lcdPuts(lcd,shutdownMessage[1][:16]) 
                    os.system("shutdown -h now +1")
                    break
            
            #ignore knocks but reboot if proper press
            if (elapsed_time > accidental and elapsed_time <= shutdown):
                logging.info('Rebooting... (Elapsed time: ' + str(elapsed_time)[:4] + ")")
                os.system("kill $(pgrep -f RPizeBox.py)")
                wp.lcdClear(lcd)
                wp.lcdPosition(lcd, 0, 0)
                wp.lcdPuts(lcd,rebootMessage[0][:16])
                wp.lcdPosition(lcd, 0, 1)
                wp.lcdPuts(lcd,rebootMessage[1][:16])  
                os.system("reboot")
            #break
            elif (elapsed_time > 0 and elapsed_time <= accidental):
                logging.info('Button Pressed: Nothing to do. (Elapsed time: ' + str(elapsed_time)[:4] + ')')
        
        
                
except KeyboardInterrupt:
    GPIO.cleanup()