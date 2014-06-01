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

from models import CommandNickname


class CoreCommands(object):

    def __init__(self, app):
        self.app = app

    def register_commands(self):
        core_commands = {
            "exit program": ("exit program", self.exit_program, False),
            "reboot": ("reboot", self.reboot, False),
            "shut down": ("shut down", self.shutdown, False),
            "shutdown": ("shut down", self.shutdown, False),
            "go to sleep": ("go to sleep", self.app.go_to_sleep, False),
            "wake up": ("wake up", self.app.wake_up, True),
            "add corpus": ("add corpus", self.app.add_corpus, False),
            "update corpus": ("update corpus", self.app.update_corpus, False),
            "learn new words": ("update corpus", self.app.update_corpus, False),
            "switch audio": ("switch audio", self.switch_audio, False),
            "what is local ip": ("local ip", self.local_ip, False),
            "status report": ("status report", self.status_report, False),
            "status update": ("status report", self.status_report, False),
            "turn on": ("turn on", self.turn_on, False),
            "switch on": ("turn on", self.turn_on, False),
            "turn off": ("turn off", self.turn_off, False),
            "switch off": ("turn off", self.turn_off, False),
            "previous page": ("screen back", self.screen_back, False),
            "next page": ("screen forward", self.screen_forward, False),
            "repeat": ("repeat command", self.repeat_command, False),
            "repeat the last command": ("repeat command", self.repeat_command, False),
            "nickname the last command as": ("nickname command", self.nickname_command, False),
            "nickname the last command": ("nickname command", self.nickname_command, False),
            "where am i": ("current address", self.current_address, False)
        }

        for command in core_commands:
            sig, func, at_sleep = core_commands[command]
            self.app.register_command([command], sig, func, at_sleep)

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
        if self.app.config.get("audio")["out_device"] == 0:
            self.app.config.get("audio")["out_device"] = 1
        else:
            self.app.config.get("audio")["out_device"] = 0
        self.app.config.write()
        self.app.say("Switched audio output hardware")

    def local_ip(self):
        self.app.say(self.app.get_ip())

    def status_report(self):
        self.app.say(
            "Current noise level is %.1f" % self.app.vol_average
            + ". Your voice is %.1f" % self.app.current_volume)

    def turn_on(self, param):
        message = "I don't know how to turn on %s" % param
        if param.lower() == "vnc server":
            self.app.system(
                os.path.join(self.app.usr_bin_path, "vncserver") + " :1")
            message = "VNC server is on"
        elif ("debug mode" in param.lower() or
                "debugging mode" in param.lower()):
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

    def repeat_command(self):
        self.app.execute_order(self.app.last_command)

    def nickname_command(self, param):
        if not param:
            self.app.say("What nickname?")
            param = self.app.record_content(duration=5.0)
        nickname = param.strip().lower()
        cn = CommandNickname.select().where(CommandNickname.nickname==nickname)
        if cn.count() == 0:
            CommandNickname.create(
                nickname=nickname, command=self.app.last_command)
            self.app.say("Nickname is created for %s" % self.app.last_command)
            return
        self.app.say("The nickname %s is already taken." % nickname)
        if not self.app.confirm("Do you want to replace?"):
                self.app.say("Canceled")
                return
        cn[0].nickname = nickname
        cn[0].command = self.app.last_command
        cn[0].save()
        self.app.say(
            "The nick name is replaced with %s" % self.app.last_command)

    def current_address(self):
        addr = self.app.get_current_address()
        if not addr:
            return
        self.app.say("You are near %s" % addr["formatted_address"])
