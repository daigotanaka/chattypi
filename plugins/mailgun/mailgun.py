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
import sys


class Mailgun(object):

    def __init__(self, api_key, mailgun_domain, mailgun_url="https://api.mailgun.net/v2"):
        self.api_key = api_key
        self.mailgun_domain = mailgun_domain
        self.mailgun_url = mailgun_url

    def send_email(self, to_, from_, subject, body):
        params = {
            "to": to_,
            "from": from_,
            "subject": subject,
            "text": body
        }
        response = requests.post(
            self.mailgun_url + "/" + self.mailgun_domain + "/" + "messages",
            auth=("api", self.api_key), params=params)
        return response

if __name__ == "__main__":
    import getopt

    def show_usage():
        print "--to=<email> --from=<email> --subject=<subject> --body=<body> --api_key=<api key> --mailgun_domain=<mailgun domain> [--help]"

    try:
        opts, args = getopt.getopt(sys.argv[1:], "", ["to=", "from=", "subject=", "body=", "api_key=", "mailgun_domain=", "mailgun_url=", "help"])
    except getopt.GetoptError as err:
        print str(err)
        show_usage()
        sys.exit(2)

    to_ = ""
    from_ = ""
    subject = ""
    body = ""
    api_key = ""
    mailgun_domain = ""

    if not opts:
        show_usage()
        sys.exit(1)

    for o, a in opts:
        if o == "--help":
            show_usage()
            sys.exit(0)
        elif o == "--to":
            to_ = a
        elif o == "--from":
            from_ = a
        elif o == "--subject":
            subject = a
        elif o == "--body":
            body = a
        elif o == "--api_key":
            apikey = a
        elif o == "--mailgun_domain":
            mailgun_domain = a

    mailgun = Mailgun(
        api_key=api_key,
        mailgun_domain=mailgun_domain)
    try:
        response = mailgun.send_email(to_=to_, from_=from_, subject=subject, body=body)
    except Exception, err:
        print err
    print response.text
