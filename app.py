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
from gps import gps, WATCH_ENABLE
from multiprocessing import Process
from pydispatch import dispatcher
from threading import Thread
from time import sleep

import logging
import os
import Queue
import re
import requests
import simplejson
# import shlex
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
# import update_corpus


class Application(object):

    def __init__(self):
        self.config = config
        self.messages = Queue.Queue()
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(config.get("system")["logfile"])
        if config.get("debug"):
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            self.logger.addHandler(ch)
            fh.setLevel(logging.DEBUG)
        else:
            fh.setLevel(logging.INFO)

        self.logger.addHandler(fh)

        self.usr_bin_path = config.get("system")["usr_bin"]
        self.default_path = config.get("system")["default_path"]
        self.data_path = os.path.join(
            self.default_path,
            config.get("system")["data_dir"])
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
        self.flac_file = "/tmp/noise%d.flac"
        self.vol_samples = 5
        self.vol_total = 5
        self.vol_average = 0.5
        self.prev_idle_vol = 1.0
        self.sound_proc = None
        self.is_mic_down = False
        self.inet_check_attempts = 0
        self.exit_now = False

        self.audio_in_device = str(config.get("audio")["in_device"])

        connect_db()

        self.clean_files()

        self.addressbook = AddressBook(
            user=self.user,
            file=config.get("addressbook")["file"])
        self.listener = Listener(user=self.user, sample_rate=self.sample_rate)
        self.speech2text = Speech2Text(
            user=self.user,
            sample_rate=self.sample_rate)

        # Voice command to event dispatch singnal table
        self.command2signal = {}
        self.core = CoreCommands(self)
        self.core.register_commands()
        self.import_plugins()

        all_commands = ""
        for key in self.command2signal.keys():
            all_commands += self.nickname + " " + key + "\n"
        corpus_file = os.path.join(self.data_path, "command_corpus.txt")
        with open(corpus_file, "w") as f:
            f.write(all_commands)

        self.listener_thread = None

        self._sphinx = None
        os.system(self.default_path + "/bin/killps")

        if config.get("system")["have_gps"]:
            self.gps = gps(mode=WATCH_ENABLE)
        else:
            self.gps = None

    @property
    def sphinx(self):
        if self._sphinx is None or self._sphinx.poll() is not None:
            # Make sure mic is working and unmuted when starting sphinx
            vol = 0
            while vol < self.min_volume:
                self.record_once()
                vol = self.get_volume()
            self.logger.debug("Restarting sphinx")
            os.system(self.default_path + "/bin/killps")
            # For a reason directly executing pocketsphinx_continous results
            # in lack of lm and dic files
            # cmd = (
            #     "pocketsphinx_continuous -lm " +
            #     self.default_path +
            #     "/data/sample.lm -dict " +
            #     self.default_path +
            #     "/data/sample.dic")
            # args = shlex.split(cmd)
            self._sphinx = subprocess.Popen(
                [self.default_path + "/bin/runps"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=True)
        return self._sphinx

    @property
    def audio_out_device(self):
        out_device = str(config.get("audio")["out_device"])
        return (
            "pulse::" + out_device if config.get("audio")["has_pulse"]
            else "alsa:device=hw=" + out_device + ",0")

    def import_plugins(self):
        path, file = os.path.split(os.path.realpath(__file__))
        path = os.path.join(path, "plugins")
        for plugin in os.listdir(path):
            if plugin == "__init__.py":
                continue
            if (plugin != "__init__.py" and
                    os.path.isdir(os.path.join(path, plugin)) and
                    os.path.exists(os.path.join(path, plugin, "__init__.py"))):
                module = libs.dynamic_import("plugins." + plugin)
                module.register(self)

    def register_command(self, voice_commands, signal, func):
        if type(voice_commands) == str:
            voice_commands = [voice_commands]
        for command in voice_commands:
            if command in self.command2signal:
                raise Exception(
                    "Voice command %s already registered"
                    % command)
            self.command2signal[command] = signal
            dispatcher.connect(func, signal=signal, sender=dispatcher.Any)
            self.logger.debug(
                "Registered '%s' command with '%s' singnal"
                % (command, signal))

    def add_corpus(self, text):
        if not text:
            return
        text = re.sub(r"[^\w]", " ", text).strip()
        with open(self.config.get("sphinx")["corpus_file"], "a") as f:
            f.write(text + "\n")

    def run(self, args=None):
        if self.listener_thread is None or not self.listener_thread.is_alive():
            self.listener_thread = Thread(target=self.listen)
            self.listener_thread.start()
        self.loop()

    def loop(self):
        self.rotation = 0
        while not self.exit_now:
            message = self.get_one_message()
            head = message.find(self.nickname)
            if head == -1:
                self.logger.debug(message)
                continue
            self.logger.info("%s: %s" % (self.user_nickname, message))
            message = message[head + len(self.nickname):].strip()
            if message:
                self.execute_order(message)
        self.listener_thread.join(1.0)
        if self.listener_thread.is_alive():
            self.listener_thread._Thread__stop()
        self.sphinx.kill()
        self.logger.debug("Terminated Sphinx")
        return

    def execute_order(self, text):
        nickname = CommandNickname().select().where(
            CommandNickname.nickname == text)
        if nickname and nickname.count():
            text = nickname[0].command

        for command in self.command2signal:
            if not self.is_command(text, command):
                continue
            sig = self.command2signal[command]
            if sig not in ["repeat command", "nickname command"]:
                self.last_command = text
            param = self.get_param(text, command)
            self.logger.debug("Dispatching signal: %s" % sig)
            kwargs = {"param": param}
            dispatcher.send(signal=sig, **kwargs)
            break
        else:
            message = "Did you say, %s?" % text
            self.say(message)

    def strip_command(self, text, command):
        return text[len(command):].strip(" ")

    def is_cue(self, text):
        cues = config.get("system")["cue"].split(" ")
        cues.append(self.nickname)
        for cue in cues:
            if cue in text:
                return True
        return False

    def is_command(self, text, command):
        if text[0:len(command)] == command:
            return True
        return False

    def get_param(self, text, command):
        return text.strip(" ")[len(command):].strip(" ")

    def clean_files(self):
        files = [
            self.flac_file,
            "/tmp/stt.txt",
            "/tmp/volume.txt"
        ]
        for file in files:
            if os.path.exists(file):
                os.remove(file)

    def play_sound(self, file="", url="", nowait=False):
        file = (
            os.path.join(self.default_path, file) if not url
            else "\"" + url + "\"")
        if self.sound_proc:
            self.sound_proc.wait()

        cmd = (
            os.path.join(self.usr_bin_path, "mplayer") + " -ao " +
            self.audio_out_device + " -really-quiet " + file)

        if nowait:
            self.sound_proc = subprocess.Popen((cmd).split(" "))
            return

        os.system(cmd)

    def recite(self, sentences):
        for sentence in sentences:
            self.say(sentence)
            if self.nickname + " stop" in self.get_one_message():
                self.logger.debug("Stopped reciting")
                break

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

    def is_loud(self, vol):
        if self.min_volume < vol and (self.vol_average * 1.5 < vol):
            return True
        return False

    def get_text_from_last_heard(self, rotation=0):
        self.listener.playing = rotation
        while self.listener.recording == self.listener.playing:
            sleep(0.5)
        text = self.speech2text.convert_flac_to_text(
            infile=self.flac_file % rotation)
        text = text.replace("\n", " ").strip(" ")
        self.listener.playing = None
        return text

    def record_once(self, duration=1.0):
        if os.path.exists(self.flac_file % 0):
            os.remove(self.flac_file % 0)
        self.listener.record_flac(
            file=self.flac_file % 0,
            hw=self.audio_in_device,
            duration=duration)

    def get_volume(self, rotation=0):
        vol = self.listener.get_volume(file=self.flac_file, rotation=rotation)
        if vol < 0:
            if not self.is_mic_down:
                self.say("Microphone is busy or down")
                self.is_mic_down = True
            return 0.0
        if self.is_mic_down:
            self.say("Microphone is up")
            self.is_mic_down = False
        return vol

    def get_one_message(self):
        message = ""
        try:
            message = self.messages.get()
        except Queue.Empty:
            pass
        message = re.sub(r"[^\w]", " ", message)
        return message.lower().strip()

    def listen(self):
        self.on_mute = False
        while not self.exit_now:
            output = self.sphinx.stdout.readline()
            if self.on_mute:
                continue
            if "READY" in output and not self.greeted:
                self.greeted = True
                self.play_sound("sound/voice_command_ready.mp3")

            m = re.search(r"\d{9}: .*", output)
            if m:
                message = m.group(0)[11:]
                self.messages.put(message)

    def record_content(self, duration=10.0):
        content = self.get_one_message()
        if content:
            return content

        self.logger.info(
            self.nickname +
            ": Sorry, I could not catch that. Please try again.")
        self.play_sound("sound/try_again.mp3")
        content = self.get_one_message(duration=duration)
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
        text = self.get_one_message()
        self.logger.debug(text)
        count = 0
        while (
            count < 2 and
                (not text or not ("yes" in text or "no" in text))):
            count += 1
            self.logger.debug(message)
            self.logger.info("%s: Please answer by yes or no" % self.nickname)
            self.play_sound("sound/yes_or_no.mp3")
            text = self.get_one_message()
            self.logger.debug(text)
        if text and "yes" in text:
            return True
        return False

    def system(self, cmd):
        return libs.system(user=self.user, command=cmd)

    def update_screen(self, html=None):
        if not self.screen_on:
            return
        url = "http://0.0.0.0:8000/update/"
        user_agent = "Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)"
        values = {"html": html}
        headers = {"User-Agent": user_agent}
        data = urllib.urlencode(values)
        req = urllib2.Request(url, data, headers)
        try:
            response = urllib2.urlopen(req)
        except urllib2.HTTPError, err:
            self.logger.info(err)
            return
        response.read()

    def get_lat_long(self):
        if not self.gps:
            return None, None
        for i in range(0, 10):
            value = self.gps.next()
            if value and hasattr(value, "lat"):
                break
        else:
            return None, None
        return value.lat, value.lon

    def get_current_address(self):
        lat, lng = self.get_lat_long()
        if lat is None:
            return None
        response = requests.get(
            "http://maps.googleapis.com/maps/api/geocode/json?" +
            "latlng=%s,%s&sensor=false" % (lat, lng))
        address = simplejson.loads(response.content)["results"]
        return address[0]


if __name__ == "__main__":
    app = Application()

    if app.screen_on:
        from server import start_server
        process = Process(target=start_server, args=(None,))
        process.start()

    while not app.exit_now:
        try:
            app.run()
        except Exception, err:
            app.logger.error(err)

    if app.screen_on:
        process.terminate()
