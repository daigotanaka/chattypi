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
DEBUG = boolean(default=True)

nickname = string(max=32, default="computer")
username = string(max=32, default="pi")
email = string(max=256)

[system]
usr_bin = string(max=1024, default="/usr/bin")
default_path = string(max=1024, default="/home/pi/chattypi")

[addressbook]
file = string(max=1024, default="/home/pi/chattypi/addressbook.csv")

[audio]
has_pulse = boolean(default=False)
out_device = integer(0, 1, default=0)
in_device = string(max=256, default="plughw:1,0")
sample_rate = integer(16000, 48000, default=8000)
threshold = float(0.0, 20.0, default=0)
min_volume = float(0.0, 10.0, default=0)
idle_duration = float(1.0, 5.0, default=2.0)
take_order_duration = float(2.0, 10.0, default=6.0)

[mailgun]
api_key = string(max=256)
mailgun_url = string(max=256, default="https://api.mailgun.net/v2")
mailgun_domain = string(max=256)

[twilio]
account_sid = string(max=256)
auth_token = string(max=256)

[twitter]
consumer_key = string(max=256)
consumer_secret = string(max=256)
access_key = string(max=256)
access_secret= string(max=256)

[wolframalpha]
api_id = string(max=256)
"""

configspec = CONFIGSPEC.split("\n")
configfilename = "config.ini"
configdir = os.path.dirname(__file__)
config_infile = os.path.join(configdir, configfilename)

config = ConfigObj(config_infile, encoding="UTF8", configspec=configspec)
config.validate(Validator())
