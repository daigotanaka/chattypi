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
from multiprocessing import Process
from pydispatch import dispatcher
from server import start_server
from time import sleep

import logging
import os
import re
import socket
import subprocess
import urllib
import urllib2

from addressbook import AddressBook
from core import CoreCommands
from listener import Listener
from models import connect_db, CommandNickname
from speech2text import Speech2Text

import libs
import plugins


class Application(object):

    def __init__(self):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(config.get("system")["logfile"])
        if config.get("debug") == True:
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            self.logger.addHandler(ch)
            fh.setLevel(logging.DEBUG)
        else:
            fh.setLevel(logging.INFO)

        self.logger.addHandler(fh)

        self.usr_bin_path = config.get("system")["usr_bin"]
        self.default_path = config.get("system")["default_path"]
        self.greeted = False
        self.exist_now = False
        self.nickname = config.get("computer_nickname")
        self.user_nickname = config.get("user_nickname")
        self.user = config.get("user")
        self.min_volume = config.get("audio")["min_volume"]
        self.sample_rate = config.get("audio")["sample_rate"]
        self.idle_duration = config.get("audio")["idle_duration"]
        self.take_order_duration = config.get("audio")["take_order_duration"]
        self.my_email = config.get("email")
        self.screen_on = config.get("system")["screen"]
        self.flac_file = "/tmp/noise.flac"
        self.vol_samples = 5
        self.vol_total = 5
        self.vol_average = 0.5
        self.prev_idle_vol = 1.0
        self.sound_proc = None
        self.is_mic_down = False
        self.inet_check_attempts = 0

        self.audio_in_device = str(config.get("audio")["in_device"])

        connect_db()

        self.clean_files()

        self.addressbook = AddressBook(user=self.user, file=config.get("addressbook")["file"])
        self.listener = Listener(user=self.user, sample_rate=self.sample_rate)
        self.speech2text = Speech2Text(user=self.user, sample_rate=self.sample_rate)

        # Voice command to event dispatch singnal table
        self.command2signal = {}
        self.core = CoreCommands(self)
        self.core.register_commands()
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
            self.logger.debug("Registered '%s' command with '%s' singnal"
                % (command, signal))

    def run(self, args=None):
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
                self.logger.info("%s: The internet is down" % self.nickname)
                self.play_sound("sound/down.wav")

                # Make the computer greet again when the internet is back
                self.greeted = False

                self.inet_check_attempts += 1
                if self.inet_check_attempts <= config.get("system")["inet_check_max_attempts"]:
                    sleep(10)
                    return

                self.logger.info("%s: ?" % self.nickname)
                self.play_sound("sound/bloop_x.wav")
                exit()

            # We have the internet
            self.inet_check_attempts = 0

            if not self.greeted:
                self.logger.info("%s: Voice command ready" % self.nickname)
                self.play_sound("sound/voice_command_ready.mp3")
                self.greeted = True

        vol = self.get_volume(duration=self.idle_duration)
        self.logger.debug("vol=%.4f avg=%.2f" % (vol, self.vol_average))

        if vol < self.min_volume:
            self.prev_idle_vol = vol
            return
        if not self.is_loud(vol) and self.prev_idle_vol > self.min_volume:
            self.prev_idle_vol = vol
            self.update_noise_level(vol)
            return

        self.logger.debug("!")

        # If the mic was muted previously and turned on, prompt for command
        text = self.get_text_from_last_heard() if self.prev_idle_vol > self.min_volume else self.nickname
        self.prev_idle_vol = vol

        if not text:
            self.logger.debug("I thought I heard something...")
            self.update_noise_level(vol)
            return
        self.logger.info("%s: %s" % (self.user_nickname, text))

        if not self.is_cue(text):
            return

        self.logger.info("%s: yes?" % self.nickname)
        self.play_sound("sound/yes.mp3")

        self.take_order(acknowledge=True)

    def take_order(self, acknowledge=True):
        text = self.listen_once(duration=self.take_order_duration, acknowledge=acknowledge)
        if not text:
            self.logger.debug("?")
            if acknowledge:
                self.play_sound("sound/bloop_x.wav")
            return

        self.logger.debug("Excecuting order...")
        self.execute_order(text)

    def execute_order(self, text):
        nickname = CommandNickname().select().where(CommandNickname.nickname==text.lower())
        if nickname.count():
            text = nickname[0].command
        for command in self.command2signal:
            if not self.is_command(text, command):
                continue
            sig = self.command2signal[command]
            if not sig in ["repeat command", "nickname command"]:
                self.last_command = text
            param = self.get_param(text, command)
            self.logger.debug("Dispatching signal: %s" % sig)
            kwargs = {"param": param}
            dispatcher.send(signal=sig, **kwargs)
            break
        else:
            message = "Did you say, %s?" % text
            self.say(message)
        if not self.exit_now:
            self.take_order(acknowledge=False)

        return

        # TODO(daigo): Clean up the code below
        if text.lower() == "reset recording level":
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
        cues = config.get("system")["cue"].split(" ")
        cues.append(self.nickname)
        for cue in cues:
            if cue in text.lower():
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
        if not text.strip(" "):
            return
        words = text.split(" ")
        if len(words) > 10:
            index = 0
            while index < len(words):
                block = " ".join(words[index:index + 10])
                self.say(block, nowait)
                index += 10
            return

        self.logger.info("%s: %s" % (self.nickname, text))
        try:
            param = urllib.urlencode({"tl": "en", "q": text})
        except UnicodeEncodeError:
            return

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
        if self.min_volume < vol and (self.vol_average * 1.5 < vol):
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
            self.play_sound("sound/click_x.wav", nowait=True)
        text = self.get_text_from_last_heard()
        self.logger.info("%s: %s" % (self.user_nickname, text))
        if text:
            return text.strip(" ")
        return None

    def record_content(self, duration=10.0):
        content = self.listen_once(duration=duration)
        if content:
            return content

        self.logger.info("%s: Sorry, I could not catch that. Please try again." % self.nickname)
        self.play_sound("sound/try_again.mp3")
        content = self.listen_once(duration=duration)
        self.logger.debug(content)
        if content:
            return content

        self.logger.info("%s: Sorry" % self.nickname)
        self.play_sound("sound/sorry.mp3")
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

    def confirm(self, message=None):
        if message:
            self.say(message)
        else:
            self.logger.info("%s: Is that OK?" % self.nickname)
            self.play_sound("sound/is_that_ok.mp3")
        text = self.listen_once(duration=3.0)
        self.logger.debug(text)
        count = 0
        while (count < 2
            and (not text or not ("yes" in text.lower() or "no" in text.lower()))):
            count += 1
            self.logger.debug(message)
            self.logger.info("%s: Please answer by yes or no" % self.nickname)
            self.play_sound("sound/yes_or_no.mp3")
            text = self.listen_once(duration=3.0)
            self.logger.debug(text)
        if text and "yes" in text.lower():
            return True
        return False

    def system(self, cmd):
        return libs.system(user=self.user, command=cmd)

    def update_screen(self, html=None):
        if not self.screen_on:
            return
        url = "http://0.0.0.0:8000/update/"
        user_agent = "Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)"
        values = {
            "html" : html }
        headers = { "User-Agent" : user_agent }
        data = urllib.urlencode(values)
        req = urllib2.Request(url, data, headers)
        try:
            response = urllib2.urlopen(req)
        except urllib2.HTTPError, err:
            self.logger.info(err)
            return
        the_page = response.read()

if __name__ == "__main__":
    app = Application()

    if app.screen_on:
        process = Process(target=start_server, args=(None,))
        process.start()

    try:
        app.run()
    except Exception, err:
        app.logger.error(err)
        raise

    if app.screen_on:
        process.terminate()
