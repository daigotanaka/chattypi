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

import os


class CoreCommands(object):

    def __init__(self, app):
        self.app = app

    def register_commands(self):
        core_commands = {
            "exit program": ("exit program", self.exit_program),
            "reboot": ("reboot", self.reboot),
            "shut down": ("shut down", self.shutdown),
            "shutdown": ("shut down", self.shutdown),
            "switch audio": ("switch audio", self.switch_audio),
            "what is local ip": ("local ip", self.local_ip),
            "status report": ("status report", self.status_report),
            "status update": ("status report", self.status_report),
            "turn on": ("turn on", self.turn_on),
            "switch on": ("turn on", self.turn_on),
            "turn off": ("turn off", self.turn_off),
            "switch off": ("turn off", self.turn_off),
            "previous page": ("screen back", self.screen_back),
            "next page": ("screen forward", self.screen_forward)
        }

        for command in core_commands:
            sig, func = core_commands[command]
            self.app.register_command([command], sig, func)

    def exit_program(self):
        self.app.logger.info("%s: Voice command off" % self.app.nickname)
        self.app.play_sound("sound/voice_command_off.mp3")
        self.app.clean_files()
        self.app.exit_now = True

    def reboot(self):
        self.app.logger.info("%s: Rebooting..." % self.app.nickname)
        self.app.play_sound("sound/rebooting.mp3")
        self.app.clean_files()
        os.system("sudo reboot")
 
    def shutdown(self):
        self.app.logger.info("%s: Shutting down..." % self.app.nickname)
        self.app.play_sound("sound/shutting_down.mp3")
        self.app.clean_files()
        os.system("sudo shutdown -h now")

    def switch_audio(self):
        self.app.config.get("audio")["out_device"] = 0 if self.app.config.get("audio")["out_device"] == 1 else 1
        self.app.config.write()
        self.app.say("Switched audio output hardware")

    def local_ip(self):
        self.app.say(self.app.get_ip())

    def status_report(self):
        self.app.say("Current noise level is %.1f" % self.app.vol_average
            + ". Your voice is %.1f" % self.app.current_volume)

    def turn_on(self, param):
        message = "I don't know how to turn on %s" % param
        if param.lower() == "vnc server":
            self.app.system(os.path.join(self.app.usr_bin_path, "vncserver") + " :1")
            message = "VNC server is on"
        elif "debug mode" in param.lower() or "debugging mode" in param.lower():
            if self.app.config.get("debug"):
                message = "Debug mode is already on"
            else:
                self.app.config.set("debug", True)
                message = "Turned on debug mode"
        self.app.say(message)

    def turn_off(self, param):
        message = "I don't know how to turn off %s" % param
        if "debug mode" in param.lower() or "debugging mode" in param.lower():
            if not self.app.config.get("debug"):
                message = "Debug mode is already off"
            else:
                self.app.config["debug"] = False
                self.app.config.write()
                message = "Turned off debug mode"
        self.app.say(message)

    def screen_back(self):
        self.app.update_screen(html="<back>")

    def screen_forward(self):
        self.app.update_screen(html="<forward>")
