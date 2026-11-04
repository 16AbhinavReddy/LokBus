#!/bin/bash
set -e
pip install -r requirements.txt
playwright install 
sudo apt update
sudo apt install -y libnspr4 libnss3
python -m playwright install chromium
