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
    if not app.config.get("twilio")["active"]:
        return
    global twilio_plugin
    twilio_plugin = TwilioPlugin(app)
    app.register_command(["send an sms to", "send sms to", "send a text message to", "send text message to", "send a text to", "send text to"], "send text", twilio_plugin.send_sms)
    app.register_command(["read sms", "read text messages", "read text message", "read texts", "read text"], "read sms", twilio_plugin.read_out_sms)

class TwilioPlugin(Plugin):
    def __init__(self, app):
        self.twilio = Twilio(
            account_sid=app.config.get("twilio")["account_sid"],
            auth_token=app.config.get("twilio")["auth_token"],
        )
        self.my_phone = app.config.get("twilio")["my_phone"]

        interval = app.config.get("twilio")["check_interval_sec"]
        if interval > 0:
            app.schedule_task(interval, self.check_sms)

        self.last_checked = datetime.datetime(year=1970, month=1, day=1)

        super(TwilioPlugin, self).__init__(app)

    def send_sms(self, param):
        nickname = param
        to_ = self.app.addressbook.get_primary_phone(nickname.lower())
        if not to_:
            self.app.say("Sorry, I cannot find the contact")
            return
        self.app.logger.debug(to_)
        self.app.say("What message do you want to send?")
        body = self.app.record_content(duration=7.0)
        if not body:
            return
        to_verbal = to_[0:3] + "-" + to_[3:6] + "-" + to_[6:]
        name = self.app.addressbook.get_fullname(nickname)
        self.app.say("Your said, " + body)
        if not self.app.confirm("The message will be sent to " + (name or nickname) + " " + to_verbal + ". Is that OK?"):
            self.app.say("cancelled")
            return
        try:
            self.twilio.send_sms(to_=to_, from_=self.my_phone, body=body)
        except Exception, err:
            self.app.say("I got an error sending message")
            self.app.logger.error(err)
            return
        self.app.say("Message sent")

    def read_out_sms(self):
        self.check_sms(quiet=False, repeat=True)

    def check_sms(self, quiet=True, repeat=False):
        messages = self.twilio.fetch_received()
        sentences = []
        for message in messages:
            if (message.status != "received" or
                (not repeat and message.date_sent <= self.last_checked)):
                continue
            from_ = message.from_
            from_ = from_[2:5] + "-" + from_[5:8] + "-" + from_[8:12]
            sentences.append("Message from " + from_)
            sentences.append(message.body)
        if sentences:
            sentences.append("End of messages")
            self.app.recite(sentences)
        elif not quiet:
            self.app.say("No messages today")
        self.last_checked = datetime.datetime.now()

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
