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
from validate import Validator

import os

import libs


def import_config_spec():
    config_specs = []
    path, file = os.path.split(os.path.realpath(__file__))
    path = os.path.join(path, "plugins")
    for plugin in os.listdir(path):
        if plugin == "__init__.py":
            continue
        if (plugin != "__init__.py"
            and os.path.isdir(os.path.join(path, plugin))
            and os.path.exists(
                os.path.join(path, plugin, "__init__.py"))):
            module = libs.dynamic_import("plugins." + plugin)
            if not hasattr(module, "config"):
                continue
            module_name = "plugins." + plugin + ".config"
            config_module = libs.dynamic_import(module_name)
            if type(config_module.configspec) != ConfigObj:
                continue
            config_spec = config_module.configspec.write()
            section = "[" + module.__name__[len("plugin.") + 1:] + "]"
            config_spec.insert(1, section)
            config_specs.extend(config_spec)
    return config_specs


CONFIGSPEC = """
debug = boolean(default=False)

computer_nickname = string(max=32, default="computer")
user_nickname = string(max=32, default="master")
username = string(max=32, default="pi")
email = string(max=256)

[system]
logfile = string(max=1024, default="log/psittaceous.log")
usr_bin = string(max=1024, default="/usr/bin")
default_path = string(max=1024, default="/home/pi/psittaceous")
db_file = string(max=1024, default="psittaceous.db")
inet_check_max_attempts = integer(1, 10, default=3)
cue = string(max=1024, default="hey ok okay listen")
screen = boolean(default=False)
data_dir = string(max=256, default="data")
have_gps = boolean(default=False)

[sphinx]
corpus_file = string(max=1024, default="corpus.txt")
keyword_corpus_file = string(max=1024, default="keyword_corpus.txt")
combined_corpus_file = string(max=1024, default="combined_corpus.txt")
full_dict_file = string(max=1024, default="full.dict")
full_lm_file = string(max=1024, default="full.lm")
command_dict_file = string(max=1024, default="command.dict")
command_lm_file = string(max=1024, default="command.lm")
name_dict_file = string(max=1024, default="name.dict")
name_lm_file = string(max=1024, default="name.lm")
timeout_sec = integer(10, 255, default=30)
ctlcount = integer(1, 100, default=10)

[addressbook]
file = string(max=1024, default="data/addressbook.csv")

[audio]
has_pulse = boolean(default=False)
out_device = integer(0, 1, default=0)
in_device = string(max=256, default="plughw:0,0")
sample_rate = integer(16000, 48000, default=48000)
min_volume = float(0.0, 10.0, default=0.005)
idle_duration = float(1.0, 5.0, default=1.5)
take_order_duration = float(2.0, 10.0, default=5.0)
param_terminator = string(max=256, default="over")
"""

configspec = CONFIGSPEC.split("\n")
configspec.extend(import_config_spec())
configfilename = "config.ini"
configdir = os.path.dirname(__file__)
config_infile = os.path.join(configdir, configfilename)

config = ConfigObj(config_infile, encoding="UTF8", configspec=configspec)
config.validate(Validator())
