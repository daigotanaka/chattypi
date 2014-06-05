<!--markdown-->
## Psittaceous: Voice operating wearable computer

![psittaceous](http://farm6.staticflickr.com/5548/9330154869_72b8d882b2_b.jpg)

### Introduction

I have been developing a voice operating Raspberry Pi. The code is designed
for easily add plugin applications around the core. Both hardware and software
components are put together so I can easily carry it with me and use it while
I am on the move.

#### Core functionality

* Listen to the voice, and convert it to text
* Read out the text informations
* Shutdown & reboot Raspberry Pi via voice commands
* Use desktop, mobile phone, or tablet in the local network as displays
* Location based applications with Raspberry Pi GPS module

#### Plugins

The app is extendable with plugin programs. So far I've developed,

* Search for short answers via WolfRamAlpha
* Make or receive phone calls via pjsip + Twilio
* Email via Mailgun
* SMS via Twilio
* Twitter read & write
* Google Talk and xmpp messenger

Though not in code repository yet, I also developed,

* Voice operate Roomba
* JIRA plugin (Opens dashboard on web browser)
* Phabricator plugin

It is also planned to be integrated with my life log API project.

### Hardware

* Raspberry Pi
* Wifi USB dongle
* Raspberry Pi case

I bought a set called <a href="http://www.adafruit.com/products/1410">"Onion Pi" pack sold by Adafruit</a>. (Yes, setting up a Raspberry Pi as a Tor proxy was my first project with it.) This pack is indeed convenient for any project that requires wifi access. I liked it because this pack also comes with a console cable and an AC adapter that I use almost everyday for development.

To "wear" Raspberry Pi, you will also need, these.

* Wireless headset: I bought <a href="http://www.amazon.com/gp/product/B0058OA0BW/ref=as_li_ss_tl?ie=UTF8&amp;camp=1789&amp;creative=390957&amp;creativeASIN=B0058OA0BW&amp;linkCode=as2&amp;tag=daigoexpresse-20">Platronics W440</a>. It's not bluetooth, so it worked out of box with no configuration. And it's sleek.</li>
* Battery: I am using <a href="http://www.amazon.com/gp/product/B008YRG5JQ/ref=as_li_ss_tl?ie=UTF8&amp;camp=1789&amp;creative=390957&amp;creativeASIN=B008YRG5JQ&amp;linkCode=as2&amp;tag=daigoexpresse-20">EasyAcc 12000mAh External Battery Charger 4 USB Power Bank</a>. It runs my Raspberry Pi 12 hours per full-charge</li>

### How to set up

#### Basic Raspberry Pi settings

I recommend simply following these Adafruit's lessons:

* [Adafruit's Raspberry Pi Lesson 1. Preparing an SD Card for your Raspberry P](http://learn.adafruit.com/adafruit-raspberry-pi-lesson-1-preparing-and-sd-card-for-your-raspberry-pi)
* [Adafruit's Raspberry Pi Lesson 2. First Time Configuration](http://learn.adafruit.com/adafruits-raspberry-pi-lesson-2-first-time-configuration)
* [Adafruit's Raspberry Pi Lesson 3. Network Setup](http://learn.adafruit.com/adafruits-raspberry-pi-lesson-3-network-setup)
* [Adafruit's Raspberry Pi Lesson 5. Using a Console Cable](http://learn.adafruit.com/adafruits-raspberry-pi-lesson-5-using-a-console-cable)(Optional if you have a console cable)</li>
* [Adafruit's Raspberry Pi Lesson 6. Using SSH](http://learn.adafruit.com/adafruits-raspberry-pi-lesson-6-using-ssh)
* [Adafruit's Raspberry Pi Lesson 7. Remote Control with VNC](http://learn.adafruit.com/adafruit-raspberry-pi-lesson-7-remote-control-with-vnc)

From here, I assume you are logged into Raspberry Pi as the user "pi", and Raspberry Pi is connected to the internet.

#### Set up audio device

Set up microphone device as the primary audio device.

    apt-get install rpi-update
    apt-get install git-core
    rpi-update
  
Connect a headset or a microphone to USB port. Reboot the Raspi.
    
Open /etc/modprobe.d/alsa-base.conf with an editor, and change this:

    options snd-usb-audio index=-2

To:

    options snd-usb-audio index=0

Close the file and reload alsa:

    alsa force-reload

#### Set up voice recognition program 

psittaceous uses CMU Sphinx for voice recognition

    wget http://sourceforge.net/projects/cmusphinx/files/sphinxbase/0.8/sphinxbase-0.8.tar.gz/download
    mv download sphinxbase-0.8.tar.gz
    wget http://sourceforge.net/projects/cmusphinx/files/pocketsphinx/0.8/pocketsphinx-0.8.tar.gz/download
    mv download pocketsphinx-0.8.tar.gz
    tar -xzvf sphinxbase-0.8.tar.gz
    tar -xzvf pocketsphinx-0.8.tar.gz

    apt-get install bison
    apt-get install libasound2-dev

    cd sphinxbase-0.8
    ./configure --enable-fixed
    make
    make install

    cd ../pocketsphinx-0.8/
    ./configure
    make
    sudo make install

#### Set up git

You will need to set up github account in Raspberry Pi.

#### The code

Some where under pi home directory you want to keep the source code, type:

    git clone: git@github.com:daigotanaka/psittaceous.git

It will create a directory called psittaceous and fetch all the source code.

Change into psittaceous directory, and type:

    virtualenv env --distribute
    source env/bin/activate
    pip install -r requirement.txt

This will install all the necessary dependency for psittaceous to the virtual environment.

### How to use psittaceous

#### Hook up headset

Turn off your Raspberry Pi by "sudo shutdown -h now" and connect USB headset or the USB dongle for the wireless headset. Turn on Raspberry Pi.

#### Adjust audio

(To be written)

alsamixer

#### Configure the app

(To be written)

Edit config.ini

#### Run the app

Go to psittaceous directory, and type:

	python app.py
