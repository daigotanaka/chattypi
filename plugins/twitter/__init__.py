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
import oauth2 as oauth
import urllib

from plugins import Plugin


def register(app):
    global twitter_plugin
    twitter_plugin = TwitterPlugin(app)
    app.register_command(["tweet"], "tweet", twitter_plugin.tweet)

class TwitterPlugin(Plugin):
    def __init__(self, app):
        from config import config
        self.twitter = Twitter(
            consumer_key=config.get("twitter")["consumer_key"],
            consumer_secret=config.get("twitter")["consumer_secret"],
            access_key=config.get("twitter")["access_key"],
            access_secret=config.get("twitter")["access_secret"]
        )
        super(TwitterPlugin, self).__init__(app)

    def tweet(self, param):
        if not param:
            self.app.say("I don't know what you want me to tweet")

        status = param
        if not self.app.confirm("The status, " + status + " will be tweeted. Is that OK?"):
            self.app.say("Cancelled")
            return
        self.app.say("Tweeted")
        self.twitter.tweet(status)


class Twitter(object):

    def __init__(self, consumer_key, consumer_secret, access_key, access_secret):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_key = access_key
        self.access_secret = access_secret

        self.consumer = oauth.Consumer(key=self.consumer_key, secret=self.consumer_secret)
        self.access_token = oauth.Token(key=self.access_key, secret=self.access_secret)
        self.client = oauth.Client(self.consumer, self.access_token)
 
    def tweet(self, status):
        if not status:
            return

        endpoint = "http://api.twitter.com/1.1/statuses/update.json"
        response, data = self.client.request(endpoint,
            method="POST",
            body=urllib.urlencode({"status": status, "wrap_links": True}))


if __name__ == "__main__":
    from config import config
    twitter = Twitter(
        consumer_key=config.get("twitter")["consumer_key"],
        consumer_secret=config.get("twitter")["consumer_secret"],
        access_key=config.get("twitter")["access_key"],
        access_secret=config.get("twitter")["access_secret"]
    )

    twitter.tweet("test tweet")
