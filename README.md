# chattypi

Voice command on Raspberry Pi

## Requirements

### Install system level requirements

    sudo apt-get install libavcodec-extra-53
    sudo apt-get install libav-tools
    sudo apt-get sox

### Install python requirements

    source cp-venv/bin/activate
    pip install -r requirements.txt

### For using websocket

    libevent-dev (for gevent)

## Running chattypi

    python app.py

