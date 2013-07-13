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

class Speech2Text(object):

    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate

    def convertToFlac(self, infile="/tmp/noise.wav", outfile="/tmp/noise.flac"):
        cmd = "/usr/bin/avconv "
        cmd += "-loglevel 0 "
        cmd += ("-i " + infile + " -ar " + str(self.sample_rate) + " " + outfile)
        os.system(cmd)

    def convertFlacToText(self, infile="/tmp/noise.flac", outfile="/tmp/stt.txt"):
        url = "http://www.google.com/speech-api/v1/recognize?lang=en-us&client=chromium"
        cmd = "/usr/bin/wget -q -U \"Mozilla/5.0\" --post-file " + infile + " --header \"Content-Type: audio/x-flac; rate=" + str(self.sample_rate) + "\" -O - \"" + url +  "\"| /usr/bin/cut -d\\\" -f12  > " + outfile

        os.system(cmd)

        f = open(outfile) 
        text = f.read()

        return text

    def convertWavToText(self, infile="/tmp/noise.wav"):
        self.convertToFlac(infile=infile)
        return self.convertFlacToText()

if __name__ == "__main__":
    if os.path.exists("/tmp/stt.txt"):
        os.remove("/tmp/stt.txt")
    stt = Speech2Text()
    print stt.convertFlacToText()
