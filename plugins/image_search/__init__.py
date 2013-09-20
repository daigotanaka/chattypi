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

from plugins import Plugin
from plugins.image_search.config import config


def register(app):
    if not config.get("active"):
        return
    global image_search_plugin
    image_search_plugin = ImageSearchPlugin(app)
    app.register_command(["show me the image of", "show me the images of", "image search"], "image search", image_search_plugin.search)


class ImageSearchPlugin(Plugin):
    def search(self, param, **kwargs):
        query = param
        self.app.say("Searching the image of %s" % query)
        self.app.update_screen(html="<iframe src=\"http://www.google.com/search?hl=en&site=imghp&tbm=isch&q=%s\" style=\"width:100%%; height:600px\"></iframe>" % query)
