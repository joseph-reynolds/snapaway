# snapaway
Security photos from Raspberry Pi Camera

Purpose of this project:
1. The primary purpose of this project is to showcase my software engineering skills,
   not to provide a full-featured product, so I may choose to provide multiple ways
   of doing things (like web applications using multiple technologies) and not develop
   features within the product thatdo not further this goal.
   In particular, I am getting up to speed on modern web technology, REST APIs, etc.
2. Provide security photos to find out what my kids were doing at 2am.
   The main idea is that cameras pointed at my doors and windows capture activity
   which I can review the next day.

Scope of this project:
Here are some of the parameters of this project:
 - low cost, like $300 USD total (see details below)
 - still pictures are good enough, video is not needed
 - can access surveillance photos from a few days back
 - can access photos from an iPad or iPhone
   and it is okay if we can only access when we are at home
 - cameras are connected to my home WiFi.  Currently: This is
   for the NTP servers and ease of development.  I would like to 
   remove this requirement.
 - security:
   + password protection
   + transport layer security (SSL)
   + (eventually) photos should be encrypted on disk so that can only
     be viewed by authorized users
 
Project difficulty:
This is an intermediate level project.  There are many fine tutorials on
the following topics and I'll assume you can get up to speed as needed:
 - Set up a Raspberry Pi hardware
 - Linux (Debian / Raspbian) operating system
 - Python programming
 - more...
 To re-create the project, you'll have to build devices, load software,
 configure networks, operating systems setting, and software.

Project materials:
The material cost includes:
 - 4 sets of Raspberry Pi computers, each with:
   + Raspberry Pi Zero W
   + Raspberry Pi Camera (with case and connector)
   + 16Gb SanDisk card (micro)
   + 2.1A power supply (USB micro)
 - USB powered hub with USB OTG
 - USB keyboard
 - HDMI monitor with HDMI mini adapter
 - I am currently using a Windows workstation to coordinate everything.

Terminology:
  camera device: The term "camera device" refers to the Raspberry Pi computer
            coupled with its Camera, case, power supply, etc., and loaded
            with the software from this project.

Project management:
  I am the sole contributor to this project.  I intend to use github issues to
  track development and my wish list.
  I am open to contributions, but don't expect any.
  If you have ideas, fixes, or suggestions, please contact me.  But understand that
  my time to work on this project is limited.
  
Current state of development:
 - The basic function of the camera software is working.  It watches the video feed and
   saves images that contain motion.  These are saved on the local storage.
 - I created a Linux systemctl systemd.service to start the camera during boot.
 - Currently: I am creating an admin tool to work with the camera devices: configure,
   update software, etc.
 - Currently: I am creating a simple web-app running on each camera device to access
   the saved pictures.
