import os

class Os(object):
    def __init__(self, user):
        self.user = user

    def system(self, cmd):
        if self.user:
            cmd = "sudo -u " + self.user + " " + cmd
        os.system(cmd)
