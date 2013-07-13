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

import wolframalpha
import sys


class WolfRamAlphaSearch(object):
    def __init__(self, app_id):
        self.client = wolframalpha.Client(app_id)

    def search(self, query):
        response = self.client.query(query)
        
        if len(response.pods) > 0:
            texts = ""
            pod = response.pods[1]
            if pod.text:
                texts = pod.text
            else:
                texts = "I have no answer for that"
            # to skip ascii character in case of error
            texts = texts.encode('ascii', 'ignore')
        else:
            texts = "Sorry, I am not sure."

        return texts

if __name__ == "__main__":
    from config import config
    app_id = config.get("wolframalpha")["app_id"]
    wa = WolfRamAlphaSearch(app_id=app_id)
    print wa.search("Population of United States")
