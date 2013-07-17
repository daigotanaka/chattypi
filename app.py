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
import os
from pydispatch import dispatcher
import re
import socket
import subprocess
import urllib


from addressbook import AddressBook
import libs
from listener import Listener
import plugins
from speech2text import Speech2Text


class Application(object):

    def __init__(self):
        self.usr_bin_path = config.get("system")["usr_bin"]
        self.default_path = config.get("system")["default_path"]

        # Voice command to event dispatch singnal table
        # See register_command method
        self.command2signal = {}
 
        self.sleep = False
        self.exist_now = False
        self.nickname = config.get("nickname")
        self.user = config.get("user")
        self.threshold = config.get("audio")["threshold"]
        self.min_volume = config.get("audio")["min_volume"]
        self.sample_rate = config.get("audio")["sample_rate"]
        self.idle_duration = config.get("audio")["idle_duration"]
        self.take_order_duration = config.get("audio")["take_order_duration"]
        self.my_phone = config.get("twilio")["from_phone"]
        self.my_email = config.get("email")
        self.flac_file = "/tmp/noise.flac"
        self.vol_samples = 5
        self.vol_total = 5
        self.vol_average = 1.0
        self.sound_proc = None
        self.is_mic_down = False

        self.audio_in_device = str(config.get("audio")["in_device"])

        self.clean_files()

        self.addressbook = AddressBook(user=self.user, file=config.get("addressbook")["file"])
        self.listener = Listener(user=self.user, sample_rate=self.sample_rate)
        self.speech2text = Speech2Text(user=self.user, sample_rate=self.sample_rate)

        self.import_plugins()

        core_commands = {
            "wake up": ("wake up", self.wakeup),
            "exit program": ("exit program", self.exit_program)
        }

        for command in core_commands:
            sig, func = core_commands[command]
            self.register_command([command], sig, func)

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
        for command in voice_commands:
            if command in self.command2signal:
                raise Exception("Voice command %s already registered"
                    % command)
            self.command2signal[command] = signal
            dispatcher.connect(func, signal=signal, sender=dispatcher.Any)
            print ("Registered '%s' command with '%s' singnal"
                % (command, signal))


    def run(self):
        self.loop()

    def loop(self):
        self.exit_now = False
        self.listen_once(duration=self.idle_duration)
        while not self.exit_now:
           self.checkin()

    def checkin(self):
        vol = self.get_volume(duration=self.idle_duration)
        print "vol=%.1f avg=%.1f" % (vol, self.vol_average)
        if not self.is_loud(vol):
            self.update_noise_level(vol)
            return

        print "!"

        text = self.get_text_from_last_heard()

        if not text:
            print "I thought I heard something..."
            self.update_noise_level(vol)
            return
        print "You said, %s" % text

        if not self.is_cue(text):
            return

        if self.sleep:
            print "Zzz..."

        else:
            print "yes?"
            self.play_sound("wav/yes_q.wav")

        text = self.listen_once(duration=self.take_order_duration, acknowledge=True)
        if not text:
            print "?"
            return

        print "Excecuting order..."
        self.execute_order(text)

        return

    def exit_program(self):
        message = "Voice command off"
        self.say(message, nowait=True)
        self.clean_files()
        self.exit_now = True
 
    def wakeup(self):
        message = "Good morning"
        print message
        self.say(message)
        self.sleep = False

    def execute_order(self, text):
        for command in self.command2signal:
            if not self.is_command(text, command):
                continue
            sig = self.command2signal[command]
            param = self.get_param(text, command)
            print "Dispatching signal: %s" % sig
            kwargs = {"param": param}
            dispatcher.send(signal=sig, **kwargs)
            return
        message = "Did you say, %s?" % text
        self.say(message)

        return

        if text.lower() in ["go to sleep", "sleep"]:
            message = "Good night"
            self.sleep = True
 
        elif text.lower() == "reboot":
            message = "Rebooting..."
            self.clean_files()
            os.system("sudo reboot")
  
        elif text.lower() in ["shutdown", "shut down"]:
            message = "Shutting down..."
            self.clean_files()
            os.system("sudo shutdown -h now")

        elif text.lower() == "switch audio":
            message = "Switched audio output hardware"
            config.get("audio")["out_device"] = 0 if config.get("audio")["out_device"] == 1 else 1
            config.write()

        elif self.is_command(text, ["turn on"]):
            message = "I did not understand."
            rest =  self.strip_command(text, "turn on")

            if rest.lower() == "vnc server":
                self.system(os.path.join(self.usr_bin_path, "vncserver") + " :1")
                message = "VNC server is on"

        elif text.lower() == "what is local ip":
            message = self.get_ip()

        elif text.lower() in ["status update", "status report"]:
            message = ("Current noise level is %.1f" % self.vol_average
                + ". Your voice is %.1f" % self.current_volume)

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
 
        elif self.is_command(text, ["tweet"]):
            status = self.strip_command(text, "tweet")
            self.tweet(status)
            return

        elif text.lower() == "add contact":
            self.add_contact()
            return

        elif self.is_command(text, ["send text to"]):
            nickname = self.strip_command(text, "send text to")
            self.send_message("sms", nickname)
            return

        elif self.is_command(text, ["send email to"]):
            nickname = self.strip_command(text, "send email to")
            self.send_message("email", nickname)
            return

        else:
            commands = ["search", "what is", "what's", "who is", "where is"]
            command = self.is_command(text, commands)
            if command:
                self.search(command, text)
                return
 
        print message 
        self.say(message)

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
        print text
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

        print "Heard at volume = %.2f" % vol
        if acknowledge:
            self.play_sound("wav/click_x.wav", nowait=True)
        text = self.get_text_from_last_heard()

        if text:
            return text.strip(" ")
        return None

    def update_noise_level(self, vol):
        self.vol_total += vol
        self.vol_samples += 1
        self.vol_average = self.vol_total / self.vol_samples

        if self.vol_samples == 6:
            if not self.get_ip():
                self.play_sound("wav/down.wav")

            self.say(self.nickname + ". At your service.")
        elif self.vol_samples > 20:
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
        print message
        self.say(message)
        text = self.listen_once(duration=3.0)
        print text
        count = 0
        while (count < 2
            and (not text or (text.lower() != "yes" and text.lower() != "no"))):
            count += 1
            print message
            self.say("Sorry, I could not catch that." + message)
            text = self.listen_once(duration=3.0)
            print text
        if text and text.lower() == "yes":
            return True
        return False

    def system(self, cmd):
        return libs.system(user=self.user, command=cmd)


    def search(self, command, text):
        message = "You asked, %s" % text
        self.say(message, nowait=True)
        print message
        query = self.strip_command(text, command)
        answer = self.wolframalpha.search(query)
        print "Answer: %s" % answer

        for sentences in re.split(r" *[\?\(!|\n][\'\"\)\]]* *", answer):
            for sentence in sentences.split(". "):
                self.say(sentence)

    def tweet(self, status):
        if not self.confirm("The status, " + status + " will be tweeted. Is that OK?"):
            self.say("Cancelled")
        self.say("Tweeted," + status)
        self.twitter.tweet(status)

    def add_contact(self):
        self.say("This feature is currently unsupported")

        """
        self.say("What is the contact's nick name?")
        nickname = self.listen_once(duration=7.0)
        print nickname
        if not nickname:
            self.say("Sorry, I could not understand. Try again.")
            nickname = self.listen_once(duration=7.0)
            print nickname
            if not nickname:
                self.say("Sorry.")
                return
        self.say("What is the number for " + nickname + "?")
        number = self.listen_once(duration=10.0)
        number = re.sub(r"\D", "", number)
        print number
        phone_validator = re.compile(r"^\d{10}$")
        if phone_validator.match(number) is None:
            self.say("Sorry, I could not understand. Try again.")
            number = self.listen_once(duration=10.0)
            number = re.sub(r"\D", "", number)
            print number
            if number is None or phone_validator.match(number) is None:
                self.say("Sorry.")
                return
        self.addressbook.add(nickname, number)
        self.say("The phone number " + " ".join(number) + " for " + nickname + " was added.")
        """

    def send_message(self, via, nickname):
        to_ = (self.addressbook.get_primary_phone(nickname.lower())
            if via == "sms" else self.addressbook.get_primary_email(nickname.lower()))
        if not to_:
            self.say("Sorry, I cannot find the contact")
            return
        print to_
        self.say("What message do you want me to send?")
        body = self.listen_once(duration=7.0)
        print body
        if not body:
            self.say("Sorry, I could not understand. Try again.")
            body = self.listen_once(duration=7.0)
            print body
            if not body:
                self.say("Sorry.")
                return
        to_verbal = " ".join(to_) if via == "sms" else to_
        name = self.addressbook.get_fullname(nickname)
        self.say("Your said, " + body)
        if not self.confirm("The message will be sent to " + (name or nickname) + " " + to_verbal + ". Is that OK?"):
            self.say("Cancelled")
            return
        try:
            if via == "sms":
                self.twilio.send_sms(to_=to_, from_=self.my_phone, body=body)
            else:
                to_email = name + "<" + to_ + ">" if name else to_
                self.mailgun.send_email(to_=to_email, from_=self.my_email, body=body)
        except Exception, err:
            self.say("I got an error sending message")
            return
        self.say("The message was sent")

if __name__ == "__main__":
    app = Application()
    app.run()
