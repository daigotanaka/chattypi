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

import requests

from plugins import Plugin
from plugins.mailgun.config import config


def register(app):
    if not config.get("active"):
        return
    global mailgun_plugin
    mailgun_plugin = MailgunPlugin(app)
    app.register_command("send email to", "send email", mailgun_plugin.send) 

class MailgunPlugin(Plugin):
    def __init__(self, app):
        self.mailgun = Mailgun(
            api_key=config.get("api_key"),
            mailgun_domain=config.get("mailgun_domain"))
        super(MailgunPlugin, self).__init__(app)

    def send(self, param):
        nickname = param
        to_ = self.app.addressbook.get_primary_email(nickname.lower())
        if not to_:
            self.app.say("Sorry, I cannot find the contact")
            return
        print to_
        self.app.say("What message do you want me to send?")
        body = self.app.listen_once(duration=7.0)
        print body
        if not body:
            self.app.say("Sorry, I could not understand. Try again.")
            body = self.app.listen_once(duration=7.0)
            print body
            if not body:
                self.app.say("Sorry.")
                return
        name = self.app.addressbook.get_fullname(nickname)
        self.app.say("Your said, " + body)
        if not self.app.confirm("The message will be sent to " + (name or nickname) + " " + to_ + ". Is that OK?"):
            self.app.say("Cancelled")
            return
        try:
            to_email = name + "<" + to_ + ">" if name else to_
            self.mailgun.send_email(to_=to_email, from_=self.app.my_email, body=body)
        except Exception, err:
            self.app.say("I got an error sending message")
            return
        self.app.say("The message was sent")


class Mailgun(object):

    def __init__(self, api_key, mailgun_domain, mailgun_url="https://api.mailgun.net/v2"):
        self.api_key = api_key
        self.mailgun_domain = mailgun_domain
        self.mailgun_url = mailgun_url

    def send_email(self, to_, from_, body):
        params = {
            "to": to_,
            "from": from_,
            "subject": body,
            "text": body
        }
        response = requests.post(
            self.mailgun_url + "/" + self.mailgun_domain + "/" + "messages",
            auth=("api", self.api_key), params=params)
        return response

if __name__ == "__main__":
    mailgun = Mailgun(
        api_key=config.get("api_key"),
        mailgun_domain=config.get("mailgun_domain"),
        mailgun_url=config.get("mailgun_url"))
    try:
        response = mailgun.send_email(to_="x@xxx.com", from_="y@yyy.com", message="Don't forget to check your spam folder if you did not receive email")
    except Exception, err:
        print err
    print response.text
