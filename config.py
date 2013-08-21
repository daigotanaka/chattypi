# The MIT License (MIT)
# 
# Copyright (c) 2013 Daigo Tanaka (@daigotanaka)
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from configobj import ConfigObj
import os
from validate import Validator


CONFIGSPEC = """
debug = boolean(default=False)

computer_nickname = string(max=32, default="computer")
user_nickname = string(max=32, default="master")
username = string(max=32, default="pi")
email = string(max=256)

[system]
logfile = string(max=1024, default="/home/pi/chattypi/chattypi.log")
usr_bin = string(max=1024, default="/usr/bin")
default_path = string(max=1024, default="/home/pi/chattypi")
inet_check_max_attempts = integer(1, 10, default=3)
cue = string(max=1024, default="hey ok okay listen")

[addressbook]
file = string(max=1024, default="/home/pi/chattypi/data/addressbook.csv")

[audio]
has_pulse = boolean(default=False)
out_device = integer(0, 1, default=0)
in_device = string(max=256, default="plughw:1,0")
sample_rate = integer(16000, 48000, default=8000)
min_volume = float(0.0, 10.0, default=0.1)
idle_duration = float(1.0, 5.0, default=2.0)
take_order_duration = float(2.0, 10.0, default=6.0)
"""

configspec = CONFIGSPEC.split("\n")
configfilename = "config.ini"
configdir = os.path.dirname(__file__)
config_infile = os.path.join(configdir, configfilename)

config = ConfigObj(config_infile, encoding="UTF8", configspec=configspec)
config.validate(Validator())
