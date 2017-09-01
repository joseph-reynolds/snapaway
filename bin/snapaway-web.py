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

import flask
import os
import re
import time

app = flask.Flask(__name__)

@app.route('/')
def hello_world():
    s = """<h1>Hello!</h1>"""
    s += """<a href="/list">[ list ]</a> """
    s += "<hr />"
    return s

@app.route('/logs')
def logs():
    return 'this is the log'

@app.route('/list')
def list():
    pics = get_pics()
    s = "Pictures: <br>"
    s += '''<ul style="list-style-type:disc">'''
    for pic in pics:
        s += ('''<li> <a href="/pic/%d">%s - %d</a></li>'''
             % (pic[0], pic[1], pic[0]))
    s += '''</ul>'''
    return s

@app.route('/pic/<int:picnum>')
def pic(picnum):
    picname = "/pics/saved/image%d.jpg" % picnum
    s = """<h1>Image %d</h1>""" % picnum
    s += """<a href="/list">[ list ]</a> """
    s += """<a href="/pic/%d">[ prev ]</a> """ % (picnum - 1)
    s += """<a href="/pic/%d">[ next ]</a> """ % (picnum + 1)
    s += "<hr />"
    s += """<img src="%s" alt="image %s">""" % (picname, picnum)
    return s

@app.route('/pics/saved/<string:picname>')
def picfile(picname):
    picname = "/home/pi/pics/saved/" + picname
    return flask.send_file(picname, mimetype='image/jpeg')


def get_pics():
    """list saved pics"""
    savedfiles = os.listdir("pics/saved")
    pics = []   # tuple(picnum, st_mtime)
    for filename in savedfiles:
        if filename.startswith("image"):
            if re.match("^image(\d+).jpg$", filename):
                n = int(filename[5:-4])
                statinfo = os.lstat("pics/saved/" + filename)
                pics.append((n, time.asctime(time.localtime(statinfo.st_mtime))))
    pics.sort(key = lambda pic: pic[0])
    return pics

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

