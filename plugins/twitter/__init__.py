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
import os
import oauth2 as oauth
import pretty
import re
import simplejson
import time
import urllib

from plugins import Plugin
from plugins.twitter.config import config


def register(app):
    if not app.config.get("active"):
        return
    global twitter_plugin
    twitter_plugin = TwitterPlugin(app)
    app.register_command(["tweet", "twitter"], "tweet", twitter_plugin.tweet)
    app.register_command(["read tweets by"], "read_tweets", twitter_plugin.read_tweets)

class TwitterPlugin(Plugin):
    def __init__(self, app):
        self.twitter = Twitter(
            consumer_key=app.config.get("twitter")["consumer_key"],
            consumer_secret=app.config.get("twitter")["consumer_secret"],
            access_key=app.config.get("twitter")["access_key"],
            access_secret=app.config.get("twitter")["access_secret"]
        )
        super(TwitterPlugin, self).__init__(app)

    def tweet(self):
        self.app.logger.info("%s: What do you want to tweet?" % self.app.nickname)
        self.app.play_sound("sound/what_tweet.mp3")
        status = self.app.record_content(duration=7.0)
        if not status:
            return
        self.app.say("The status, " + status + " will be tweeted.")
        if not self.app.confirm():
            self.app.logger.info("%s: Cancelled" % self.app.nickname)
            self.app.play_sound("sound/cancelled.mp3")
            return
        self.app.logger.info("%s: Tweeted" % self.app.nickname)
        self.app.play_sound("sound/tweeted.mp3")
        self.twitter.tweet(status)

    def read_tweets(self, param):
        nickname = param
        username = self.app.addressbook.get_twitter_username(nickname.lower())
        if not username:
            self.app.say("Sorry, I cannot find the twitter username")
            return
        statuses = self.twitter.get_tweets(username)

        for status in statuses:
            text = status["text"] + " "
            text = re.sub("http:\/\/.* ", "", text)
            # Twitter returns GMT time in the format like this:
            # Mon Sep 16 06:57:38 +0000 2013
            # Python 2.x does not support %z, so converting to "GMT"
            tweeted_at = datetime.datetime.strptime(
                    status["created_at"].replace("+0000", "GMT"),
                    "%a %b %d %H:%M:%S %Z %Y")
            tweeted_at = tweeted_at - datetime.timedelta(seconds=time.timezone - 3600 * time.daylight)
            tweeted_at_pretty = pretty.date(tweeted_at)

            self.app.say(text)
            self.app.say(tweeted_at_pretty)

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
        response, data = self.client.request(
            endpoint,
            method="POST",
            body=urllib.urlencode({"status": status, "wrap_links": True})
        )

    def get_tweets(self, username, count=5, exclude_replies=True):
        if not username:
            return
        endpoint = "https://api.twitter.com/1.1/statuses/user_timeline.json"
        params = urllib.urlencode({
                "screen_name": username,
                "count": count,
                "exclude_replies": exclude_replies
        })
        response, data = self.client.request(
            endpoint + "?" + params,
            method="GET",
        )
        statuses = simplejson.loads(data)
        return statuses


if __name__ == "__main__":
    twitter = Twitter(
        consumer_key=config.get("consumer_key"),
        consumer_secret=config.get("consumer_secret"),
        access_key=config.get("access_key"),
        access_secret=config.get("access_secret")
    )

    twitter.tweet("test tweet")
