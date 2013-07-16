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


class Mailgun(object):

    def __init__(self, api_key, mailgun_domain, mailgun_url="https://api.mailgun.net/v2"):
        self.api_key = api_key
        self.mailgun_domain = mailgun_domain
        self.mailgun_url = mailgun_url

    def send_email(self, to_, from_, message):
        params = {
            "to": to_,
            "from": from_,
            "subject": message,
            "text": message
        }
        response = requests.post(
            self.mailgun_url + "/" + self.mailgun_domain + "/" + "messages",
            auth=("api", self.api_key), params=params)
        return response

if __name__ == "__main__":
    from config import config
    mailgun = Mailgun(
        api_key=config.get("mailgun")["api_key"],
        mailgun_domain=config.get("mailgun")["mailgun_domain"],
        mailgun_url=config.get("mailgun")["mailgun_url"])
    try:
        response = mailgun.send_email(to_="x@xxx.com", from_="y@yyy.com", message="Don't forget to check your spam folder if you did not receive email")
    except Exception, err:
        print err
    print response.text