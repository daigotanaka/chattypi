import pjsua as pj
import sys

from twilio.rest import TwilioRestClient

pj_lib = None
pj_current_call = None
pj_outgoing_call = None


class PjTwilio(object):

    def __init__(
            self,
            my_number,
            sip_domain,
            sip_username,
            sip_password,
            twilio_account_sid,
            twilio_auth_token,
            twilml_url,
            incoming_call_callback=None,
            pre_session_callback=None,
            post_session_callback=None,
            error_callback=None):
        self.my_number = my_number
        self.sip_domain = sip_domain
        self.sip_username = sip_username
        self.sip_password = sip_password
        self.twilio_account_sid = twilio_account_sid
        self.twilio_auth_token = twilio_auth_token
        self.twilml_url = twilml_url
        self.incoming_call_callback = incoming_call_callback
        self.pre_session_callback = pre_session_callback
        self.post_session_callback = post_session_callback
        self.error_callback = error_callback

        self.pj_outgoing_call = None
        self.pj_current_call = None
        self.log_callback = None

        self._twilio_client = None

    def _call_log_cb(self, level, string, length):
            if self.log_callback:
                self.log_callback(string)
            else:
                print string

    @property
    def twilio_client(self):
        if not self._twilio_client:
            self._twilio_client = TwilioRestClient(self.twilio_account_sid,
                self.twilio_auth_token)
        return self._twilio_client

    def start(self):
        global pj_lib
        pj_lib = pj.Lib()
        ua_cfg = pj.UAConfig()
        ua_cfg.nameserver = ["8.8.8.8", "8.8.4.4"] # Example: Google Public DNS
        media_cfg = pj.MediaConfig()
        media_cfg.clock_rate = 8000
        media_cfg.ec_tail_len= 0
        pj_lib.init(
            ua_cfg=ua_cfg,
            log_cfg=pj.LogConfig(level=4, callback=self._call_log_cb),
            media_cfg=media_cfg)

        transport_in = pj_lib.create_transport(pj.TransportType.TLS, pj.TransportConfig(port=5060))
        # Create UDP transport which listens to any available port
        transport_out = pj_lib.create_transport(pj.TransportType.UDP, pj.TransportConfig(0))

        pj_lib.start()
        account_cfg = pj.AccountConfig()
        account_cfg.id = "sip:%s@%s" % (self.sip_username, self.sip_domain)
        account_cfg.reg_uri = "sip:%s;transport=tls" % self.sip_domain
        account_cfg.auth_cred = [pj.AuthCred(
            realm=self.sip_domain,
            username=self.sip_username,
            passwd=self.sip_password,
        )]
        acc_cb = SipAccountCallback(
            account_cfg,
            self.incoming_call_callback,
            self.pre_session_callback,
            self.post_session_callback)
        self.account = pj_lib.create_account(account_cfg, cb=acc_cb)

    def terminate(self):
        global pj_lib
        self.transport_in = None
        self.transport_out = None
        self.account.delete()
        self.account = None
        pj_lib.destroy()
        pj_lib = None

    def make_sip_call(self, uri):
        """Function to make call"""
        global pj_current_call
        try:
            print "Making call to", uri
            pj_current_call = self.account.make_call(uri, cb=SipCallCallback(post_session_callback=self.post_session_callback))
        except pj.Error, e:
            print "Exception: " + str(e)
            return None

    def make_twilio_call(self, to_number):
        global pj_outgoing_call
        pj_outgoing_call = self.twilio_client.calls.create(
            url=self.twilml_url,
            to=to_number,
            from_=self.my_number,
            timeout=20,
            if_machine="Hangup")

    def answer(self):
        global pj_current_call
        if not pj_current_call:
            if self.error_callback:
                self.error_callback("No one is calling")
            return
        if self.pre_session_callback:
            self.pre_session_callback()
        pj_current_call.answer(200)

    def hangup(self):
        global pj_current_call
        global pj_outgoing_call
        if pj_current_call:
            pj_current_call.hangup()
            pj_current_call = None
        if pj_outgoing_call:
            self.twilio_client.calls.update(pj_outgoing_call.sid,
                status="completed")
            pj_outgoing_call = None

    def command_line_loop(self):
        global pj_current_call
        global pj_outgoing_call
        # Menu loop
        while True:
            # print "My SIP URI is", my_sip_uri
            print "Menu:  m=make call, h=hangup call, a=answer call, q=quit"

            input = sys.stdin.readline().rstrip("\r\n")
            if input == "m":
                if pj_current_call:
                    print "Already have another call"
                    continue
                print "Enter destination URI to call: ",
                to_number = sys.stdin.readline().rstrip("\r\n")
                if input == "":
                    continue
                # lck = lib.auto_lock()
                # pj_current_call = make_sip_call(acc_out, input)
                # del lck
                self.make_twilio_call(to_number)

            elif input == "h":
                if not pj_current_call:
                    print "There is no call"
                    continue
                self.hangup()

            elif input == "a":
                if not pj_current_call:
                    print "There is no call"
                    continue
                self.answer()

            elif input == "q":
                break
        self.terminate()


# Callback to receive events from Call
class SipCallCallback(pj.CallCallback):
    def __init__(self, call=None, post_session_callback=None):
        self.post_session_callback = post_session_callback
        pj.CallCallback.__init__(self, call)

    # Notification when call state has changed
    def on_state(self):
        global pj_current_call
        global pj_outgoing_call
        print "Call with", self.call.info().remote_uri,
        print "is", self.call.info().state_text,
        print "last code =", self.call.info().last_code,
        print "(" + self.call.info().last_reason + ")"

        if self.call.info().state == pj.CallState.DISCONNECTED:
            pj_outgoing_call = None
            pj_current_call = None
            if self.post_session_callback:
                self.post_session_callback()
            else:
                print 'Current call is', pj_current_call

    # Notification when call's media state has changed.
    def on_media_state(self):
        global pj_lib
        if self.call.info().media_state == pj.MediaState.ACTIVE:
            # Connect the call to sound device
            call_slot = self.call.info().conf_slot
            pj_lib.conf_connect(call_slot, 0)
            pj_lib.conf_connect(0, call_slot)
            print "Media is now active"
        else:
            print "Media is inactive"


class SipAccountCallback(pj.AccountCallback):
    def __init__(
            self,
            account=None,
            incoming_call_callback=None,
            pre_session_callback=None,
            post_session_callback=None):
        self.incoming_call_callback = incoming_call_callback
        self.pre_session_callback = pre_session_callback
        self.post_session_callback = post_session_callback
        pj.AccountCallback.__init__(self, account)

    def on_incoming_call(self, call):
        global pj_current_call
        global pj_outgoing_call

        if pj_current_call:
            call.answer(486, "Busy")
            return

        if pj_outgoing_call:
            pj_current_call = call
            call_cb = SipCallCallback(call=pj_current_call, post_session_callback=self.post_session_callback)
            pj_current_call.set_callback(call_cb)
            if self.pre_session_callback:
                self.pre_session_callback()
            call.answer(200)
            return

        pj_current_call = call

        call_cb = SipCallCallback(pj_current_call, post_session_callback=self.post_session_callback)
        pj_current_call.set_callback(call_cb)

        pj_current_call.answer(180)

        if self.incoming_call_callback:
            self.incoming_call_callback(call.info().remote_uri)
        else:
            print "Incoming call from ", call.info().remote_uri
            print "Press 'a' to answer"

    def on_reg_state(self):
        print "Registration complete, status=", self.account.info().reg_status, \
              "(" + self.account.info().reg_reason + ")"


if __name__ == "__main__":
    my_number = "+18881231234"
    sip_domain = "mysipdomain.com"
    sip_username = "mysipusername"
    sip_password = "mysippassword"
    twilio_account_sid = "My Twilio account SID"
    twilio_auth_token = "My Twilio Auth Token"
    twilml_url = "http://mytwiml.com/twiml_to_dial_sip"

    pjt= PjTwilio(
        my_number,
        sip_domain,
        sip_username,
        sip_password,
        twilio_account_sid,
        twilio_auth_token,
        twilml_url)
    pjt.start()
    pjt.command_line_loop()
