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
import simplejson

class AddressBook(object):

    def __init__(self, username, file):
        self.file = file
        self.username = username
        self.book = {}
        if os.path.exists(file):
            with open(file, "r") as f:
                self.book = simplejson.loads(f.read())

    def get_by_nickname(self, nickname):
        return self.book.get(nickname, None)

    def add(self, nickname, phone, email=""):
        self.book[nickname] = {"phone": phone, "email": email}
        if os.path.exists(self.file):
            os.system("sudo -u " + self.username + " cp " + self.file + " " + self.file + "_bak")
        with open(self.file, "w") as f:
            f.write(simplejson.dumps(self.book))

 
if __name__ == "__main__":
    addressbook = AddressBook("pi", "./addressbook.json")
    addressbook.add("monkey", "9999999999", "monkey@monkey.com")
    info = addressbook.get_by_nickname("monkey")
    print info
