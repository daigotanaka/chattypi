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
from twilio.rest import TwilioRestClient

from plugins.twilio.config import config
from plugins import Plugin


def register(app):
    if not config.get("active"):
        return
    global twilio_plugin
    twilio_plugin = TwilioPlugin(app)
    app.register_command(["send an sms to", "send sms to", "send a text message to", "send text message to", "send a text to", "send text to"], "send text", twilio_plugin.send_sms)
    app.register_command(["read sms", "read text messages", "read text message", "read texts", "read text"], "read sms", twilio_plugin.read_out_sms)

class TwilioPlugin(Plugin):
    def __init__(self, app):
        self.twilio = Twilio(
            account_sid=config.get("account_sid"),
            auth_token=config.get("auth_token")
        )
        self.my_phone = config.get("my_phone")
        super(TwilioPlugin, self).__init__(app)

    def send_sms(self, param):
        nickname = param
        to_ = self.app.addressbook.get_primary_phone(nickname.lower())
        if not to_:
            self.app.say("Sorry, I cannot find the contact")
            return
        self.app.logger.debug(to_)
        self.app.play_sound("sound/what_message.mp3")
        body = self.app.listen_once(duration=7.0)
        self.app.logger.debug(body)
        if not body:
            self.app.play_sound("wav/try_again.mp3")
            body = self.app.listen_once(duration=7.0)
            self.app.logger.debug(body)
            if not body:
                self.app.play_sound("sound/sorry.mp3")
                return
        to_verbal = " ".join(to_)
        name = self.app.addressbook.get_fullname(nickname)
        self.app.say("Your said, " + body)
        if not self.app.confirm("The message will be sent to " + (name or nickname) + " " + to_verbal + ". Is that OK?"):
            self.app.play_sound("sound/cancelled.mp3")
            return
        try:
            self.twilio.send_sms(to_=to_, from_=self.my_phone, body=body)
        except Exception, err:
            self.app.say("I got an error sending message")
            self.app.logger.error(err)
            return
        self.app.play_sound("sound/message_sent.mp3")

    def read_out_sms(self):
        messages = self.twilio.fetch_received()
        count = 0
        for message in messages:
            if message.status != "received":
                continue
            count += 1
            self.app.say("Message %d" % count)
            self.app.say(message.body)
        if count == 0:
            self.app.say("No messages today")
        else:
            self.app.say("End of messages")


class Twilio(object):

    def __init__(self, account_sid, auth_token):
        self.account_sid = account_sid
        self.account_token = auth_token
        self.client = TwilioRestClient(account_sid, auth_token)

    def send_sms(self, to_, from_, body):
        self.client.sms.messages.create(to=to_, from_=from_, body=body)

    def fetch_received(self):
        return self.client.sms.messages.list(date_sent=datetime.datetime.today(), status="received")


if __name__ == "__main__":
    twilio = Twilio(account_sid=config.get("account_sid"),
        auth_token=config.get("auth_token"))
    try:
        twilio.send_sms(to_="0000000000", from_="1111111111", message="test")
    except Exception, err:
        print err
