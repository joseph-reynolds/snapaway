#!/usr/bin/python
# Adapted from: http://picamera.readthedocs.io/en/release-1.10/api_array.html#pimotionanalysis

"""
snapaway3 aka try-pimotionanalysis -- take pics with the Pi Camera

This is part of the snapaway project: ???tbd

Issues:
 - Start automatically when plugged in
 - Log events
 - Show dashboard: running, uptime, %full
 - prune old pics
 - Continue numbering pics between restarts
 - Expose a web interface
 - Battery powered interface
 - Can configure camera from workstation
 - Can set up Raspbian from workstation with python-numpy, etc
"""

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import division

import datetime
import io
import logging
import logging.handlers
import numpy as np
import os
import picamera
import picamera.array
import platform
import re
import signal
import sys
import syslog
import time

mylogger = logging.getLogger("snapaway")
mylogger.setLevel(logging.DEBUG)
mylogger.addHandler(logging.handlers.SysLogHandler(address='/dev/log'))


def mkdir_p(path):
    """make path like mkdir -p"""
    try:
        os.makedirs(path) # , exist_ok=True
    except OSError:
        pass

#try:
#    PICS = os.environ["PICS"]
#except KeyError:
#    PICS = os.environ["HOME"] + "/pics"
PICS = "/home/pi/pics"
# print("Using PICS =", PICS)
PICS_SAVED = PICS + "/saved"

parms = {
    'camera': {
        'rotation': 0
    },
    'motion': {
        'sensitivity': 50,
        'threshold': 2
    },
    'pics': {
        'dir': PICS_SAVED,
        'max_bytes': 4 * 1024 * 1024 * 1024
    }
}
#''' OLD - DELETEME:
parms["camera"] = {}
parms["camera"]["rotation"] = 0
parms["motion"] = {}
parms["motion"]["sensitivity"] = 50
parms["motion"]["threshold"] = 2
parms["pics"] = {}
parms["pics"]["dir"] = PICS_SAVED
parms["pics"]["max_bytes"] = 4 * 1024 * 1024 * 1024
# Where
#   motion.sensitivity is threshold the magnitude of each motion vector individually
#   motion.threshold is the numebr iof vectors that have to change

HOSTNAME = platform.node()
if HOSTNAME == "raspi0":
    parms["camera"]["rotation"] = 0
elif HOSTNAME == "raspi2":
    parms["camera"]["rotation"] = 270
    parms["motion"]["sensitivity"] = 35
    parms["motion"]["threshold"] = 10
elif HOSTNAME == "raspi3":
    parms["camera"]["rotation"] = 180

mkdir_p(parms["pics"]["dir"])



# Program termination
keep_going = True
def handle_TERM(s, t):
    "Handle SIGTERM; initiate clean termination"
    print("Exiting (caught signal %d)" % s)
    global keep_going
    keep_going = False

def GetHighestNumberedPic():
    "Scan the saved pics directory for the highest numbered pic"
    savedfiles = os.listdir(parms["pics"]["dir"])
    highest = 0
    for filename in savedfiles:
        if re.match("^image(\d+).jpg$", filename):
            n = int(filename[5:-4])
            highest = max(highest, n)
    return highest

def ReclaimSpace():
    "Reclaim file system space by removing old pics"
    # determine space used by saved pictures
    savedfiles = os.listdir(parms["pics"]["dir"])
    totalsize = 0   # bytes
    filedata = []   # tuple(filename, st_size, st_mtime)
    for filename in savedfiles:
        if filename.startswith("image"):
            statinfo = os.lstat(parms.pic_dir + "/" + filename)
            filedata.append((filename, statinfo.st_size, statinfo.st_mtime))
            totalsize += statinfo.st_size
    if totalsize > prune_to_size:
        # print("Removing saved pics to save space")
        # sort saved pics: oldest first
        filedata.sort(key = lambda fileinfo: fileinfo[2], reverse = True)
        # Remove files (oldest first) until we saved enough space
        while (totalsize > allowedsize) and len(filedata) > 0:
            # Remove the oldest file
            syslog.syslog("Removing saved pic: %s" % filedata[-1][0])
            os.remove(parms.pic_dir + "/" + filedata[-1][0])
            totalsize -= filedata[-1][1]
            del filedata[-1]


motion_detected = False
motion_was_detected = False  #  Oops, thread safe?
class DetectMotion(picamera.array.PiMotionAnalysis):
    """Detect motion per PiCam h264 motion data"""
    def analyse(self, a):
        a = np.sqrt(
            np.square(a['x'].astype(np.float)) +
            np.square(a['y'].astype(np.float))
            ).clip(0, 255).astype(np.uint8)
        # If enough motion vectors with enough magnitude,
        # then say we've detected motion
        global parms
        b = (a > parms["motion"]["sensitivity"]).sum()
        global motion_detected
        global motion_was_detected
        motion_detected = (b > parms["motion"]["threshold"])
        motion_was_detected |= motion_detected
        #print(b, '', end='')
        #sys.stdout.flush()
        #if b > 2:
        #    print('Motion detected!')

# Frame grabber - write some frames associated with motion
class WriteFramesWithMotion(object):
    """Grab frames from PiCam"""
    def __init__(self, starting_frame_num = 0):
        self.frame_num = starting_frame_num
        self.previous_picture_time = 0
        self.output = None
    def do_flush(self):
        if self.output:
            self.output.flush()
            self.output.close()
            self.output = None
            self.frame_num += 1
            os.rename(
                parms["pics"]["dir"] + "/newpic",
                parms["pics"]["dir"] + "/image%d.jpg" % self.frame_num)
    def write(self, buf):
        # At this point, there is frame data to write
        if buf.startswith(b'\xff\xd8'):
            # At this point, we are writing the start of a frame
            if self.output:
                self.do_flush()
            global motion_was_detected
            current_time = time.time()
            if (motion_was_detected and
                current_time >= self.previous_picture_time + 1):
                # At this point, motion is detected AND enough time has passed
                self.previous_picture_time = current_time
                self.output = io.open(
                    parms["pics"]["dir"] + "/newpic",
                    'wb')
                syslog.syslog("writing frame %d" % (self.frame_num + 1))
            motion_was_detected = False
        if self.output:
            self.output.write(buf)
    def flush(self):
        # Called for the end of the video stream
        self.do_flush()


# main code
signal.signal(signal.SIGTERM, handle_TERM)
signal.signal(signal.SIGINT, handle_TERM)
highest_numbered_pic = GetHighestNumberedPic()
syslog.syslog("Starting with pic %d" % highest_numbered_pic)
try:
    with picamera.PiCamera() as camera:
        time.sleep(2)  # camera warm up
        with DetectMotion(camera) as output:
            camera.resolution = (640, 480)
            camera.annotate_text_size = 16
            camera.rotation = parms["camera"]["rotation"]
            camera.start_recording(
                '/dev/null',
                format = 'h264',
                motion_output = output)
            camera.start_recording(
                WriteFramesWithMotion(highest_numbered_pic),
                format = 'mjpeg',
                splitter_port = 2)
            syslog.syslog("Motion detection started...camera.revision=%s" % camera.revision)
            while keep_going:
                camera.annotate_text = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                camera.wait_recording(0.1)
                # TO DO: Remove oldest images to reclaim space
            camera.stop_recording()
except picamera.exc.PiCameraMMALError:
    syslog.syslog("Could not connect to camera!")
    exit(5)
    # raise
