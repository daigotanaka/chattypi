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

from threading import Thread
import xmpp

from plugins import Plugin
from config import config

def register(app):
    if not app.config.get("google_talk")["active"]:
        return
    global google_talk_plugin
    google_talk_plugin = GoogleTalkPlugin(app)
    app.register_command(["tell him", "tell her", "tell them"], "gtalk_respond", google_talk_plugin.respond)


class GoogleTalkPlugin(Plugin):
    def __init__(self, app):
        super(GoogleTalkPlugin, self).__init__(app)

        self.last_from = None
        self.gtalk_thread = Thread(target=self.gtalk_loop)
        self.gtalk_thread.start()

    def gtalk_loop(self):
        user = """%s<script type="text/javascript">
        /* <![CDATA[ */
        (function(){try{var s,a,i,j,r,c,l,b=document.getElementsByTagName("script");l=b[b.length-1].previousSibling;a=l.getAttribute('data-cfemail');if(a){s='';r=parseInt(a.substr(0,2),16);for(j=2;a.length-j;j+=2){c=parseInt(a.substr(j,2),16)^r;s+=String.fromCharCode(c);}s=document.createTextNode(s);l.parentNode.replaceChild(s,l);}}catch(e){}})();
        /* ]]> */
        </script>""" % self.app.config.get("google_talk")["email"]
        password = self.app.config.get("google_talk")["password"]
        server="gmail.com"
        
        jid = xmpp.JID(user)
        self.connection = xmpp.Client(server) 
        self.connection.connect(server=("talk.google.com", 5223))
        result = self.connection.auth(jid.getNode(), password, "LFY-client") 
        self.connection.RegisterHandler("message", self.message_handler) 
         
        self.connection.sendInitPresence() 
         
        while not self.app.exit_now and self.connection.Process(1):
            pass
        self.app.logger.debug("Exiting Google Talk plugin")

    def message_handler(self, connect_object, message_node):
        self.last_from = message_node.getFrom()
        message = message_node.getBody()
        self.current_connection = connect_object
        if not message:
            return
        if self.app.nickname + ":" == str(message).strip()[0:len(self.app.nickname) + 1]:
            text =  message.strip().lower()[len(self.app.nickname) + 1:]
            self.app.do_execute_order(text)
            return
        nickname = str(self.last_from)
        nickname = nickname[0:nickname.find("@")]
        self.app.say(nickname + " says: " + message)

    def send_message(self, contact_jid, message):
        self.connection.send(xmpp.Message(contact_jid, message))

    def respond(self, param, **kwargs):
        if not self.last_from:
            return
        self.send_message(self.last_from, param)

 
if __name__ == "__main__":
   pass
