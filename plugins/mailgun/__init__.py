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

from libs import File
from plugins import Plugin
from plugins.mailgun.config import config
from mailgun import Mailgun


def register(app):
    if not app.config.get("mailgun")["active"]:
        return
    global mailgun_plugin
    mailgun_plugin = MailgunPlugin(app)
    app.register_command(["send an email to", "send email to"], "send email", mailgun_plugin.send)
    app.register_command(["email log to"], "email log", mailgun_plugin.send_log)


class MailgunPlugin(Plugin):
    def __init__(self, app):
        self.mailgun = Mailgun(
            api_key=app.config.get("mailgun")["api_key"],
            mailgun_domain=app.config.get("mailgun")["mailgun_domain"])
        super(MailgunPlugin, self).__init__(app)

        ip = self.app.get_ip()
        if ip and app.config.get("mailgun")["send_ip_on_start"]:
            self.mailgun.send_email(to_=self.app.my_email, from_=self.app.my_email, subject="IP address", body="My IP address is %s" % ip)

    def send(self, param, **kwargs):
        nickname = param
        to_ = self.app.addressbook.get_primary_email(nickname.lower())
        if not to_:
            self.app.say("Sorry, I cannot find the contact")
            return
        self.app.logger.debug(to_)

        if not kwargs.get("body"):
            self.app.logger.info("%s: What message do you want to send?" % self.app.nickname)
            self.app.play_sound("sound/what_message.mp3")
            body = self.app.record_content(duration=7.0)
            subject = body
            self.app.say("Your said, " + body)
        else:
            subject = kwargs.get("subject", "Message from %s" % self.app.nickname)
            body = kwargs.get("body")
        if not body:
            return

        name = self.app.addressbook.get_fullname(nickname)
        if not self.app.confirm("The message will be sent to " + (name or nickname) + " " + to_ + ". Is that OK?"):
            self.app.logger.info("%s: Cancelled." % self.app.nickname)
            self.app.play_sound("sound/cancelled.mp3")
            return
        try:
            to_email = name + "<" + to_ + ">" if name else to_
            self.mailgun.send_email(to_=to_email, from_=self.app.my_email, subject=subject, body=body)
        except Exception, err:
            self.app.say("I got an error sending message")
            return
        self.app.logger.info("%s: Message sent." % self.app.nickname)
        self.app.play_sound("sound/message_sent.mp3")

    def send_log(self, param):
        with File(self.app.config.get("system")["logfile"]) as f:
            body = f.tail(self.app.config.get("mailgun")["email_log_lines"])
        self.send(param, body=body, subject="Log from %s" % self.app.nickname)
