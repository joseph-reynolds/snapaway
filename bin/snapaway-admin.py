#!/usr/bin/python
# Python2.7
# snapaway-admin.py

"""snapaway-admin Administrate snapaway camera devices

This is a tool to help set up the camera devices.
The main idea is that we'll have a camera device (RasPi with camera)
with the Raspbian operating system freshly installed, configured for 
the WiFi network and ssh. This tool then configures the rest.

The basic user stories for the camera administrator are:
    Rename the camera device (its hostname) and give it a description.
    Loading and updating software packages (apt)
    Load the camera device's code ("snapaway")
    Set up the camera to start automatically (systemctl snapaway.service)
    Check camera operation and start and stop it.
    Safely shut down the camera.
    Future: create and work with security certificates

I am thinking of a command-line tool because that is what I am familiar with.
At some point, I would like to change these to be "reborn in the cloud", that is,
have a web application with REST APIs to perform these functions.
But for now, a command-line tool.

Ideas for commands to manage devices:
    add-device hostname user pswd description camera-parms
    remove-device hostname
    update-device hostname description camera-parms
    list-devices
    select-device hostname

Commands to work with devices.
These work with a specific device. Use "use" before using these:
    update-packages
    install-snapaway
    systemctl [start, stop, enable, disable, status]

Commands to work with device's saved images:
    ls-pics
    remove-all-pics
    get-pic

Limited scope: This is NOT intended to be the way to get pictures from the camera. Two ideas are: (1) short term, create a web application server on each camera to serve pictures, and (2) create a REST API on each camera to serve pictures to a web application hosted on a workstation that connects to many different cameras.
"""

import cmd
import os
import paramiko
import socket
import sys

# Credentials for signing into the camera device
# TO DO: Replace with ssh keys: ssh-keygen, ssh-copy-id
username = "pi"
password = "*********"

# Idea:
camera_devices = [
    ("raspi0", "Upstairs"),
    ("raspi1", "Workbench"),
    ("raspi2", "Main level"),
    ("raspi3", "Basement"),
]

setup_initial_config = [  # NOT YET USED
    # Use sudo raspi-config to set these:
    "hostname",
    "locale",
    "timezone",
    "keyboard layout",
    "i2c",
    "enable camera",
    "sudo reboot now",
]

# each operation is either:
#   a command to execute via ssh, or
#   a tuple for sftp (from,to), where
#      from - is relative to: $(the path of this exec)/..
#      to - is relative to the directory ssh starts in (normally $HOME, e.g., "/home/pi")

setup_refresh = [
    "mkdir -p $HOME/bin",
    "mkdir -p $HOME/services",
    ("bin/snapaway-cam.py", "bin/snapaway-cam.py"),
    ("bin/snapaway-web.py", "bin/snapaway-web.py"),
    ("services/snapaway-cam.service", "services/snapaway-cam.service"),
    ("services/snapaway-web.service", "services/snapaway-web.service"),
    "chmod +x $HOME/bin/snapaway-cam.py",
    "chmod +x $HOME/bin/snapaway-web.py",
    "sudo cp services/snapaway-cam.service /etc/systemd/system/snapaway-cam.service",
    "sudo cp services/snapaway-web.service /etc/systemd/system/snapaway-web.service",
    "sudo chmod 664 /etc/systemd/system/snapaway-cam.service",
    "sudo chmod 664 /etc/systemd/system/snapaway-web.service",
    "sudo systemctl daemon-reload",
    "sudo systemctl stop snapaway-cam",
    "sudo systemctl stop snapaway-web",
    "sudo systemctl start snapaway-cam",
    "sudo systemctl start snapaway-web",
    "sudo systemctl enable snapaway-cam",
    "sudo systemctl enable snapaway-web",
]
setup_operations = [
    "sudo apt-get update --assume-yes",
    "sudo apt-get upgrade --assume-yes",
    "sudo apt-get install python-numpy --assume-yes",
    "sudo apt-get install python-picamera --assume-yes",
    "sudo apt-get install python-pip --assume-yes",
    "sudo pip install Flask",
] + setup_refresh

show_settings = [
    "sudo systemctl status snapaway-cam",
    "sudo journalctl _SYSTEMD_UNIT=snapaway-cam.service",
    "sudo systemctl status snapaway-web",
    "sudo journalctl _SYSTEMD_UNIT=snapaway-web.service",
]

remove_pics = [
    "rm pics/saved/image*.jpg"
]

shutdown_steps = [
    "sudo systemctl stop snapaway-cam",
    "sudo systemctl stop snapaway-web",
    "sudo shutdown now",
]

class SnapawayAdmin(cmd.Cmd):
    intro = 'Welcome to the snapaway admin tool.  Type help or ? to list commands.\n'
    prompt = 'snapaway> '
    devicename = ''

    def do_exit(self, arg):
        return True
    def set_prompt(self):
        if self.devicename:
            self.prompt = "snapaway %s> " % self.devicename
        else:
            self.prompt = "snapaway> "
    def postcmd(self, stop, line):
        self.set_prompt()
        return stop        
    def do_use(self, arg):
        "Select the snapaway device to operate on"
        self.devicename = str(arg)
        print("Using camera device: %s" % self.devicename)
    def do_setup(self, arg):
        "Set up prereq software on the camera device"
        self.perform_operations(setup_operations)
    def do_refresh(self, arg):
        "Set up snapaway on the camera device"
        self.perform_operations(setup_refresh)
    def do_diagnose(self, arg):
        "Show snapaway diagnostic settings on the camera device"
        self.perform_operations(show_settings)
    def do_rmpics(self, arg):
        "Delete saved pictures on the camera device"
        self.perform_operations(remove_pics)
    def do_shutdown(self, arg):
        "Safely shut down the camera device"
        self.perform_operations(shutdown_steps)
    def perform_operations(self, operations):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print("Connect to %s" % self.devicename)
        try:
            ssh.connect(
                    self.devicename + ".local",
                    username=username,
                    password=password)
        except socket.gaierror:
            print("Cannot connect via ssh")
            return
        except paramiko.ssh_exception.AuthenticationException:
            print("Authentication failed")
            print("Try this:")
            print("  ssh-keygen")
            print("  ssh-copy-id %s" % self.devicename + ".local")
            print("Then try the command again.  Goodbye!")
            raise
        ftp = None
        try:
            for oper in operations:
                if isinstance(oper, str):
                    cmd = oper
                    print("Running command: %s" % cmd)
                    stdin, stdout, stderr = ssh.exec_command(cmd)
                    print("Result:\n", stdout.readlines())
                elif isinstance(oper, tuple):
                    filenames = oper
                    if not ftp:
                        print("Starting sftp connection")
                        ftp = ssh.open_sftp()
                    print("Putting file %s" % filenames[1])
                    ftp.put(mypath + "/" + filenames[0], filenames[1])
                else:
                    raise RuntimeError
        finally:
            ssh.close()
            if ftp:
                ftp.close()
     

if __name__ == '__main__':
    mypath = os.path.dirname(os.path.abspath(__file__)) + "/.."
    SnapawayAdmin().cmdloop()


