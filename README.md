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

Mongodb isn't distributed by some later linux distributions, so you will need to download and install the MongoDB Community Server from mongodb.com.

No further database configuration is needed.

    git clone https://gitea.mmmoxford.uk/dvolk/lo2
    cd lo2
    virtualenv env
    source env/bin/activate
    pip3 install -r requirements.txt
    mkdir static

Now install yt-dl from https://github.com/yt-dlp/yt-dlp/releases/

rename the binary to youtube-dl and mark it as executable:

    mv yt-dlp youtube-dl
    chmod a+x youtube-dl

## Running

    python3 lo2.py serve

Open browser at http://127.0.0.1:5555/
