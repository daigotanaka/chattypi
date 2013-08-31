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

import sys

import wolframalpha

from plugins import Plugin
from plugins.wolframalpha.config import config


def register(app):
    if not config.get("active"):
        return
    global wra_plugin
    wra_plugin = WolfRamAlphaPlugin(app)
    app.register_command(["search", "question", "what is", "what's", "who is", "where is"], "search", wra_plugin.search)
    app.register_command(["search by spelling"], "search by spelling", wra_plugin.search_by_spelling)


class WolfRamAlphaPlugin(Plugin):
    def __init__(self, app):
        self.wolframalpha = WolfRamAlphaSearch(app_id=config.get("app_id"))
        super(WolfRamAlphaPlugin, self).__init__(app)

    def search(self, param):
        if not param:
            param = self.get_query()
        if not param:
            return
        query = param
        self.app.say("Searching: " + query, nowait=True)
        answer = self.wolframalpha.search(query)
        self.app.logger.debug("Answer: %s" % answer)

        self.app.say(answer)

    def search_by_spelling(self):
        self.app.logger.info("%s: Please spell the search keyword" % self.app.nickname)
        raw = self.get_query()
        words = raw.split(" ")
        query = ""
        for word in words:
            query += word[0]
        if query:
            self.search(query.lower())

    def get_query(self):
        self.app.logger.info("%s: What do you want to search?" % self.app.nickname)
        self.app.play_sound("sound/what_question.mp3")
        query = self.app.record_content(duration=7.0)
        if not query:
            return
        return query


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
    app_id = config.get("app_id")
    wa = WolfRamAlphaSearch(app_id=app_id)
    print wa.search("Population of United States")
