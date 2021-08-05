# lo2: Simple youtube-dl web frontend

- Queue up videos to download
- Click on thumbnail to play the video with mpv
- Click on title to see full youtube-dl json info file
- Click on status to open Youtube channel page
- List of optional youtube-dl arguments (video formats: 480p, 720p, etc)
- Extracts thumbnail, title and duration, and tracks when it was added and last watched

## Screenshot

<img src="https://i.imgur.com/aH4XyGA.png" width=400>

## Installation

You will need mongodb:

    apt install mongodb-server

No further database configuration is needed.

    git clone https://gitea.mmmoxford.uk/dvolk/lo2
    cd lo2
    virtualenv env
    source env/bin/activate
    pip3 install -r requirements.txt

## Running

    python3 lo2.py

Open browser at http://127.0.0.1:5555/
