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

from config import config
import logging
import os
from pydispatch import dispatcher
import re
import socket
import subprocess
from time import sleep
import urllib


from addressbook import AddressBook
import libs
from listener import Listener
import plugins
from speech2text import Speech2Text


class Application(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(config.get("system")["logfile"])
        fh.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

        self.usr_bin_path = config.get("system")["usr_bin"]
        self.default_path = config.get("system")["default_path"]

        # Voice command to event dispatch singnal table
        # See register_command method
        self.command2signal = {}

        self.config = config

        self.greeted = False
        self.sleep = False
        self.exist_now = False
        self.nickname = config.get("nickname")
        self.user = config.get("user")
        self.threshold = config.get("audio")["threshold"]
        self.min_volume = config.get("audio")["min_volume"]
        self.sample_rate = config.get("audio")["sample_rate"]
        self.idle_duration = config.get("audio")["idle_duration"]
        self.take_order_duration = config.get("audio")["take_order_duration"]
        self.my_email = config.get("email")
        self.flac_file = "/tmp/noise.flac"
        self.vol_samples = 5
        self.vol_total = 5
        self.vol_average = 1.0
        self.sound_proc = None
        self.is_mic_down = False
        self.inet_check_attempts = 0

        self.audio_in_device = str(config.get("audio")["in_device"])

        self.clean_files()

        self.addressbook = AddressBook(user=self.user, file=config.get("addressbook")["file"])
        self.listener = Listener(user=self.user, sample_rate=self.sample_rate)
        self.speech2text = Speech2Text(user=self.user, sample_rate=self.sample_rate)

        core_commands = {
            "wake up": ("wake up", self.wakeup),
            "exit program": ("exit program", self.exit_program),
            "reboot": ("reboot", self.reboot),
            "shut down": ("shut down", self.shutdown),
            "shutdown": ("shut down", self.shutdown),
            "switch audio": ("switch audio", self.switch_audio),
            "what is local ip": ("local ip", self.local_ip),
            "status report": ("status report", self.status_report),
            "status update": ("status report", self.status_report),
            "turn on": ("turn on", self.turn_on),
        }

        for command in core_commands:
            sig, func = core_commands[command]
            self.register_command([command], sig, func)

        self.import_plugins()

    @property
    def audio_out_device(self):
        out_device = str(config.get("audio")["out_device"])
        return ("pulse::" + out_device if config.get("audio")["has_pulse"]
            else "alsa:device=hw=" + out_device + ",0")

    def import_plugins(self):
        path, file = os.path.split(os.path.realpath(__file__))
        path = os.path.join(path, "plugins")
        for plugin in os.listdir(path):
            if plugin == "__init__.py":
                continue
            if (plugin != "__init__.py"
                and os.path.isdir(os.path.join(path, plugin))
                and os.path.exists(
                    os.path.join(path, plugin, "__init__.py")
                    )
                ):
                module = libs.dynamic_import("plugins." + plugin)
                module.register(self)

    def register_command(self, voice_commands, signal, func):
        if type(voice_commands) == str:
            voice_commands = [voice_commands]
        for command in voice_commands:
            if command in self.command2signal:
                raise Exception("Voice command %s already registered"
                    % command)
            self.command2signal[command] = signal
            dispatcher.connect(func, signal=signal, sender=dispatcher.Any)
            self.logger.info("Registered '%s' command with '%s' singnal"
                % (command, signal))


    def run(self):
        self.loop()

    def loop(self):
        self.exit_now = False
        self.listen_once(duration=self.idle_duration)
        while not self.exit_now:
           self.checkin()

    def checkin(self):
        if self.vol_samples == 6:
            if not self.get_ip():
                # The internet is down
                self.play_sound("wav/down.wav")

                # Make the computer greet again when the internet is back
                self.greeted = False

                self.inet_check_attempts += 1
                if self.inet_check_attempts <= config.get("system")["inet_check_max_attempts"]:
                    sleep(10)
                    return

                self.play_sound("wav/bloop_x.wav")
                exit()

            # We have the internet
            self.inet_check_attempts = 0

            if not self.greeted:
                self.say(self.nickname + " " + config.get("system")["greeting"])
                self.greeted = True

        vol = self.get_volume(duration=self.idle_duration)
        self.logger.debug("vol=%.2f avg=%.2f" % (vol, self.vol_average))
        if not self.is_loud(vol):
            self.update_noise_level(vol)
            return

        self.logger.debug("!")

        text = self.get_text_from_last_heard()

        if not text:
            self.logger.debug("I thought I heard something...")
            self.update_noise_level(vol)
            return
        self.logger.info("You said, %s" % text)

        if not self.is_cue(text):
            return

        if self.sleep:
            self.logger.debug("Zzz...")

        else:
            self.logger.info("yes?")
            self.play_sound("wav/yes_q.wav")

        text = self.listen_once(duration=self.take_order_duration, acknowledge=True)
        if not text:
            self.logger.debug("?")
            return

        self.logger.debug("Excecuting order...")
        self.execute_order(text)


        return

    def exit_program(self):
        message = "Voice command off"
        self.say(message, nowait=True)
        self.clean_files()
        self.exit_now = True

    def wakeup(self):
        self.say("Good morning")
        self.sleep = False

    def reboot(self):
        self.say("Rebooting...")
        self.clean_files()
        os.system("sudo reboot")
 
    def shutdown(self):
        self.say("Shutting down...")
        self.clean_files()
        os.system("sudo shutdown -h now")

    def switch_audio(self):
        config.get("audio")["out_device"] = 0 if config.get("audio")["out_device"] == 1 else 1
        config.write()
        self.say("Switched audio output hardware")

    def local_ip(self):
        self.say(self.get_ip())

    def status_report(self):
        self.say("Current noise level is %.1f" % self.vol_average
            + ". Your voice is %.1f" % self.current_volume)

    def turn_on(self, param):
        message = "I did not understand."
        if param.lower() == "vnc server":
            self.system(os.path.join(self.usr_bin_path, "vncserver") + " :1")
            message = "VNC server is on"
        self.say(message)

    def execute_order(self, text):
        for command in self.command2signal:
            if not self.is_command(text, command):
                continue
            sig = self.command2signal[command]
            param = self.get_param(text, command)
            self.logger.info("Dispatching signal: %s" % sig)
            kwargs = {"param": param}
            dispatcher.send(signal=sig, **kwargs)
            return
        message = "Did you say, %s?" % text
        self.say(message)

        return

        # TODO(daigo): Clean up the code below
        if text.lower() in ["go to sleep", "sleep"]:
            message = "Good night"
            self.sleep = True
 
        elif text.lower() == "reset recording level":
            self.min_volume = self.vol_average * 1.5
            message = "Set minimum voice level to %.1f" % self.min_volume
            config.get("audio")["min_volume"] = self.min_volume
            config.write()
 
        elif text.lower() == "set recording level":
            self.min_volume = self.current_volume * 0.75
            message = "Set minimum voice level to %.1f" % self.min_volume
            config.get("audio")["min_volume"] = self.min_volume
            config.write()
 
        elif text.lower() == "add contact":
            self.add_contact()
            return
 
    def strip_command(self, text, command):
        return text[len(command):].strip(" ")

    def is_cue(self, text):
        if text.lower().strip(" ") in [self.nickname, "hey", "ok", "okay", "hey " + self.nickname, "ok " + self.nickname, "okay " + self.nickname]:
            return True
        return False

    def is_command(self, text, command):
        text = text.lower().strip(" ")
        if text[0:len(command)] == command:
            return True
        return False

    def get_param(self, text, command):
        return text.strip(" ")[len(command):].strip(" ")

    def clean_files(self):
        files = [
            "/tmp/noise.flac",
            "/tmp/noise.wav",
            "/tmp/stt.txt",
            "/tmp/volume.txt"
        ]
        for file in files:
            if os.path.exists(file):
                os.remove(file)

    def play_sound(self, file="", url="", nowait=False):
        file = (os.path.join(self.default_path, file) if not url
            else "\"" + url + "\"")
        if self.sound_proc:
            self.sound_proc.wait()

        cmd = os.path.join(self.usr_bin_path, "mplayer") + " -ao " + self.audio_out_device + " -really-quiet " + file

        if nowait:
            self.sound_proc = subprocess.Popen((cmd).split(" "))
            return

        os.system(cmd)

    def say(self, text, nowait=False):
        self.logger.info(text)
        param = urllib.urlencode({"tl": "en", "q": text})
        url = "http://translate.google.com/translate_tts?" + param
        if not nowait:
            self.play_sound(url=url, nowait=nowait)
            return
        return self.play_sound(url=url)

    def get_volume(self, duration=1.0):
        if os.path.exists(self.flac_file):
            os.remove(self.flac_file)

        self.listener.record_flac(hw=self.audio_in_device, duration=duration)
        vol = self.listener.get_volume(file=self.flac_file)
        if vol < 0:
            if self.is_mic_down == False:
                self.say("Microphone is busy or down")
                self.is_mic_down = True
            return 0.0
        if self.is_mic_down == True:
            self.say("Microphone is up")
            self.is_mic_down = False
        return vol

    def is_loud(self, vol):
        if (self.min_volume< vol
            and (0 < self.threshold < vol or 0 < self.vol_average * 1.5 < vol)):
            return True
        return False

    def get_text_from_last_heard(self):
        return self.speech2text.convertFlacToText().replace("\n", " ").strip(" ")

    def listen_once(self, duration=3.0, acknowledge=False):
        text = ""
        if os.path.exists(self.flac_file):
            os.remove(self.flac_file)
        self.listener.record_flac(hw=self.audio_in_device, duration=duration)
        vol = self.listener.get_volume(self.flac_file)
        self.current_volume = vol

        if not self.is_loud(vol):
            return None

        self.logger.debug("Heard at volume = %.2f" % vol)
        if acknowledge:
            self.play_sound("wav/click_x.wav", nowait=True)
        text = self.get_text_from_last_heard()

        if text:
            return text.strip(" ")
        return None

    def update_noise_level(self, vol):
        if vol < 0.01:
            return
        self.vol_total += vol
        self.vol_samples += 1
        self.vol_average = self.vol_total / self.vol_samples

        if self.vol_samples > 20:
            self.vol_total = self.vol_average * 10
            self.vol_samples = 10

        return None

    def get_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("google.com", 0))
        except:
            return None
        return s.getsockname()[0]

    def confirm(self, message):
        self.say(message)
        text = self.listen_once(duration=3.0)
        self.logger.debug(text)
        count = 0
        while (count < 2
            and (not text or (text.lower() != "yes" and text.lower() != "no"))):
            count += 1
            self.logger.debug(message)
            self.say("Sorry, I could not catch that." + message)
            text = self.listen_once(duration=3.0)
            self.logger.debug(text)
        if text and text.lower() == "yes":
            return True
        return False

    def system(self, cmd):
        return libs.system(user=self.user, command=cmd)

    def add_contact(self):
        self.say("This feature is currently unsupported")

        """
        self.say("What is the contact's nick name?")
        nickname = self.listen_once(duration=7.0)
        self.logger.debug(nickname)
        if not nickname:
            self.say("Sorry, I could not understand. Try again.")
            nickname = self.listen_once(duration=7.0)
            self.logger.debug(nickname)
            if not nickname:
                self.say("Sorry.")
                return
        self.say("What is the number for " + nickname + "?")
        number = self.listen_once(duration=10.0)
        number = re.sub(r"\D", "", number)
        self.logger.debug(number)
        phone_validator = re.compile(r"^\d{10}$")
        if phone_validator.match(number) is None:
            self.say("Sorry, I could not understand. Try again.")
            number = self.listen_once(duration=10.0)
            number = re.sub(r"\D", "", number)
            self.logger.debug(number)
            if number is None or phone_validator.match(number) is None:
                self.say("Sorry.")
                return
        self.addressbook.add(nickname, number)
        self.say("The phone number " + " ".join(number) + " for " + nickname + " was added.")
        """

if __name__ == "__main__":
    app = Application()
    app.run()
