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

from twilio.rest import TwilioRestClient


def register():
    from config import config
    global twilio
    twilio = Twilio(
        account_sid=config.get("twilio")["account_sid"],
        auth_token=config.get("twilio")["auth_token"]
    )


class Twilio(object):

    def __init__(self, account_sid, auth_token):
        self.account_sid = account_sid
        self.account_token = auth_token
        self.client = TwilioRestClient(account_sid, auth_token)

    def send_sms(self, to_, from_, body):
        self.client.sms.messages.create(to=to_, from_=from_, body=body)

if __name__ == "__main__":
    from config import config
    twilio = Twilio(account_sid=config.get("twilio")["account_sid"],
        auth_token=config.get("twilio")["auth_token"])
    try:
        twilio.send_sms(to_="0000000000", from_="1111111111", message="test")
    except Exception, err:
        print err
