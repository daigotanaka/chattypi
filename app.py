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

import datetime
import logging
import os
import re
import requests
import simplejson
import socket
import subprocess
import time
import urllib
import urllib2

from config import config
from gps import gps, WATCH_ENABLE
from multiprocessing import Process, Queue
from pydispatch import dispatcher
from threading import Thread

from addressbook import AddressBook
from core import CoreCommands
from listener import Listener
from models import connect_db, CommandNickname
from speech2text import Speech2Text

import libs


message_queue = Queue()

class Application(object):

    def __init__(self):
        global message_queue
        self.config = config
        self.messages = message_queue
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

        self.inet_check_attempts = 0
        self.is_mic_down = False
        self.ready = False
        self.sleeping = False
        self.exit_now = False

        self.nickname = config.get("computer_nickname")
        self.user_nickname = config.get("user_nickname")
        self.user = config.get("user")
        self.my_email = config.get("email")

        self.screen_on = config.get("system")["screen"]
        self.audio_in_device = str(config.get("audio")["in_device"])

        self.min_volume = config.get("audio")["min_volume"]
        self.sample_rate = config.get("audio")["sample_rate"]
        self.idle_duration = config.get("audio")["idle_duration"]
        self.take_order_duration = config.get("audio")["take_order_duration"]
        self.flac_file = "/tmp/noise%d.flac"
        self.vol_samples = 5
        self.vol_total = 5
        self.vol_average = 0.5
        self.prev_idle_vol = 1.0
        self.sound_proc = None

        self.links = []
        self.periodic_tasks = {}

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
        self.signals_at_sleep = []
        self.command2signal = {}
        self.core = CoreCommands(self)
        self.core.register_commands()
        self._import_plugins()

        all_commands = ""
        for key in self.command2signal.keys():
            all_commands += self.nickname + " " + key + "\n"
        all_commands += self.nickname + " stop\n"
        for name in self.addressbook.book.keys():
            all_commands += name + "\n"
        corpus_file = os.path.join(self.data_path, "keyword_corpus.txt")
        with open(corpus_file, "w") as f:
            f.write(all_commands)

        self.listener_thread = None

        self.sphinx_timeout = config.get("sphinx")["timeout_sec"]
        self.listening_since = None
        self._sphinx = None
        self._kill_sphinx()

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
                vol = self._get_volume()
            self.logger.debug("Restarting sphinx")
            os.system(os.path.join(self.default_path, "bin/killps"))
            args = (
                "pocketsphinx_continuous",
                "-lm",
                os.path.join(
                    self.data_path,
                    self.config.get("sphinx")["lm_file"]),
                "-dict",
                os.path.join(
                    self.data_path,
                    self.config.get("sphinx")["dict_file"])
            )
            self._sphinx = subprocess.Popen(
                " ".join(args),
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

    def register_command(self, voice_commands, signal, func, at_sleep=False):
        if type(voice_commands) == str:
            voice_commands = [voice_commands]
        if at_sleep:
            self.signals_at_sleep.append(signal)
            self.logger.debug("Added %s as a valid command while sleeping:" %
                signal)
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

    def schedule_task(self, interval, func):
        self.logger.debug("Scheduled %s with %d sec interval" %
            (func, interval))
        tasks = self.periodic_tasks.setdefault(str(interval), [])
        tasks.append(func)

    def run(self, args=None):
        if self.listener_thread is None or not self.listener_thread.is_alive():
            self.listener_thread = Thread(target=self._listen)
            self.listener_thread.start()
        self._loop()

    def execute_order(self, text):
        nickname = CommandNickname().select().where(
            CommandNickname.nickname == text)
        if nickname and nickname.count():
            text = nickname[0].command

        for command in self.command2signal:
            if not self.is_command(text, command):
                continue
            sig = self.command2signal[command]

            if self.sleeping and sig not in self.signals_at_sleep:
                return

            if sig not in ["repeat command", "nickname command"]:
                self.last_command = text
            param = self._get_param(text, command)
            self.logger.debug("Dispatching signal: %s" % sig)
            kwargs = {"param": param}
            self.play_sound("sound/ok.wav")
            dispatcher.send(signal=sig, **kwargs)
            break
        else:
            message = "Did you say, %s?" % text
            self.say(message)

    def is_command(self, text, command):
        if text[0:len(command)] == command:
            return True
        return False

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

    def recite(self, sentences, corpus=False):
        for sentence in sentences:
            if not self.say(sentence):
                self.logger.debug("Stopped reciting")
                return
        if corpus:  # Add to corpus all at once instead of sentence by sentence
            self.app.add_corpus(message)

    def say(self, text, corpus=False, nowait=False):
        try:
            self.logger.info("%s: %s" % (self.nickname, text))
            self.update_screen(self._insert_href(text))
        except Exception, e:
            self.logger.error(e)

        text = self._cut_link(text)
        text = text.replace("#", "")
        words = text.split(" ")
        index = 0
        cont = True
        while index < len(words):
            block = " ".join(words[index:index + 10])
            if block.strip():
                self._say(block, nowait=nowait)
            index += 10

            if self.nickname + " stop" in self.get_one_message(wait=False):
                cont = False
                break

        if corpus:
            self.add_corpus(text)

        return cont

    def record_once(self, duration=1.0):
        if os.path.exists(self.flac_file % 0):
            os.remove(self.flac_file % 0)
        self.listener.record_flac(
            file=self.flac_file % 0,
            hw=self.audio_in_device,
            duration=duration)

    def get_one_message(self, wait=True):
        message = ""
        try:
            message = self.messages.get(wait)
        except Exception, err:
            pass
        return message.lower().strip()

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

    def record_content(self, duration=10.0):
        content = self.get_one_message()
        if content:
            return content

        self.logger.info(
            self.nickname +
            ": Sorry, I could not catch that. Please try again.")
        self.play_sound("sound/try_again.mp3")
        content = self.get_one_message()
        self.logger.debug(content)
        if content:
            return content

        self.logger.info("%s: Sorry" % self.nickname)
        self.play_sound("sound/sorry.mp3")
        return None

    def update_corpus(self):
        self.on_mute = True
        self._kill_sphinx()
        args = [
            os.path.join(self.default_path, "bin/updatecorpus"),
            self.default_path,
            os.path.join(
                self.data_path,
                self.config.get("sphinx")["corpus_file"]),
            os.path.join(
                self.data_path,
                self.config.get("sphinx")["keyword_corpus_file"]),
            os.path.join(
                self.data_path,
                self.config.get("sphinx")["combined_corpus_file"]),
            os.path.join(
                self.data_path,
                self.config.get("sphinx")["dict_file"]),
            os.path.join(
                self.data_path,
                self.config.get("sphinx")["lm_file"])
        ]
        cmd = " ".join(args)
        os.system(" ".join(args))
        self.on_mute = False
        self.say("Updated vocabulary")

    def add_corpus(self, param):
        text = self._remove_link(param)
        self.logger.debug("Adding corpus: " + text)
        if not text:
            return
        text = re.sub(r"[^\w]", " ", text).strip()
        corpus_file = os.path.join(
            self.data_path,
            self.config.get("sphinx")["corpus_file"])
        with open(corpus_file, "a") as f:
            f.write(text + "\n")

    def pop_link(self):
        return self.links.pop() if self.links else None

    def mute(self):
        self.on_mute = True
        self._kill_sphinx()

    def unmute(self):
        self.on_mute = False

    def wake_up(self):
        self.say("Hello again")
        self.sleeping = False

    def go_to_sleep(self):
        self.sleeping = True
        self.say("Bye for now")

    def get_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("google.com", 0))
        except:
            return None
        return s.getsockname()[0]

    def system(self, cmd):
        return libs.system(user=self.user, command=cmd)

    def _loop(self):
        while not self.exit_now:
            if self.ready and not self.sleeping:
                self._execute_periodic_tasks()
            if (self.listening_since and
                    time.time() - self.listening_since >
                    self.sphinx_timeout):
                self.logger.debug("Sphinx timeout")
                self.listening_since = None
                self._kill_sphinx()
                continue

            message = self.get_one_message(wait=False)
            if not message:
                continue
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
        self._kill_sphinx()
        return

    def _get_volume(self, rotation=0):
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

    def _import_plugins(self):
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

    def _execute_periodic_tasks(self):
        current_time = int(time.time())
        for interval in self.periodic_tasks.keys():
            if current_time % int(interval) > 0:
                continue
            for task in self.periodic_tasks[interval]:
                try:
                    task()
                except Exception, e:
                    self.logger.exception(e)

    def _get_param(self, text, command):
        text = text[len(command):]
        endpos = text.find(self.config.get("audio")["param_terminator"])
        if endpos > -1:
            text = text[:endpos]
        return text.strip()

    def _say(self, text, nowait):
        try:
            param = urllib.urlencode({"tl": "en", "q": text})
        except UnicodeEncodeError:
            return
        url = "http://translate.google.com/translate_tts?" + param
        self.play_sound(url=url, nowait=nowait)

    def _remove_link(self, text):
        return self._cut_link(text, remember=False)

    def _cut_link(self, text, replace="", remember=True):
        text = text + " "
        if remember:
            for item in re.findall(r"(http[s]*:\/\/[^\s]+)", text):
                self.links.append(item)
        text = re.sub(r"http[s]*:\/\/[^\s]+", replace, text)
        return text

    def _insert_href(self, text):
        text = text + " "
        text = re.sub(r"(http[s]*:\/\/[^\s]+)", r'<a href="\1">link</a>', text)
        return text

    def _listen(self):
        self.on_mute = False
        while not self.exit_now:
            if self.on_mute:
                continue
            output = self.sphinx.stdout.readline()
            # self.logger.debug(output)
            if "READY" in output and not self.ready:
                self.play_sound("sound/voice_command_ready.mp3")
                self.ready = True
            if "Listening..." in output:
                self.logger.debug(
                    "Started to listen at %s" % datetime.datetime.now())
                self.listening_since = time.time()

            m = re.search(r"\d{9}: .*", output)
            if m:
                message = m.group(0)[11:]
                message = re.sub(r"[^\w]", " ", message)
                duration = 0
                if self.listening_since:
                    duration = time.time() - self.listening_since
                self.logger.debug("Listened for %d seconds" % int(duration))
                self.listening_since = None
                self.messages.put(message)

    def _kill_sphinx(self):
        os.system(self.default_path + "/bin/killps")
        if self._sphinx:
            self._sphinx = None
        self.logger.debug("Terminated Sphinx")

    # Requires Flask server
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

    # Requires GPS
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
        process = Process(target=start_server, args=(message_queue,))
        process.start()

    while not app.exit_now:
        try:
            app.run()
        except Exception, err:
            app.logger.error(err)

    if app.screen_on:
        process.terminate()
