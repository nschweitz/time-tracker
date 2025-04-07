#!/bin/bash
cd ~/src/track
. venv/bin/activate
python -u check.py 30 > /tmp/track.log 2>&1
