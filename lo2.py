import json
import os
import logging
import subprocess
import threading
import time
from enum import Enum
import datetime as dt
from pathlib import Path
import shlex

import argh
import flask
import flask_mongoengine as fm
import humanize

logging.basicConfig(level=logging.DEBUG)

APP = flask.Flask(__name__)
APP.config["SEND_FILE_MAX_AGE_DEFAULT"] = dt.timedelta(hours=24)
APP.secret_key = "secret"
APP.config["MONGODB_DB"] = "lo2-1"
db = fm.MongoEngine(APP)


class Status(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    OK = "ok"
    ERROR = "error"


class Queue(db.Document):
    url = db.StringField()
    added_epochtime = db.IntField()
    youtube_dl_optional_arg = db.StringField()
    finished_epochtime = db.IntField()
    lastplayed_epochtime = db.IntField()
    status = db.EnumField(Status, default=Status.QUEUED)
    thumbnail_url = db.StringField()
    youtube_dl_json = db.DynamicField()
    meta = {"indexes": ["added_epochtime"]}


def or_404(arg):
    if not arg:
        return flask.abort(404)
    return arg


def icon(name):
    return f'<i class="fa fa-{name} fa-fw"></i>'


try:
    cmd = "git describe --tags --always --dirty"
    version = subprocess.check_output(shlex.split(cmd)).decode().strip()
except:
    version = ""


youtube_dl_optional_args = ["", "-f 18", "-f 22", "--audio-format best -f 18"]


def run_youtube_dl(url, opt):
    cmd = f"./youtube-dl {opt} --ignore-errors -o './%(uploader)s_%(uploader_id)s/%(title)s_%(id)s.%(ext)s' --write-description --write-info-json --write-annotations --write-all-thumbnails --restrict-filenames --all-subs --print-json {url}"
    logging.info(cmd)
    try:
        out = subprocess.check_output(cmd, shell=True).decode()
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return dict()
    out = out.split("\n")
    return json.loads(out[0])


def downloader():
    while True:
        q = Queue.objects(status=Status.QUEUED).first()
        if q:
            q.status = Status.RUNNING
            q.save()
            r = run_youtube_dl(q.url, q.youtube_dl_optional_arg)
            if r:
                q.status = Status.OK
                q.youtube_dl_json = r
                th = ""
                if r.get("_filename"):
                    th = make_thumbnail(r.get("_filename"))
                elif r.get("filename"):
                    th = make_thumbnail(r.get("filename"))
                q.thumbnail_url = th
            else:
                q.status = Status.ERROR
            q.finished_epochtime = int(time.time())
            q.save()
        time.sleep(5)


def add_url_to_queue(url):
    q = Queue(url=url, status=Status.QUEUED, added_epochtime=int(time.time()))
    q.save()


def add_url_from_xclip():
    url = subprocess.check_output("xclip -o", shell=True).decode("utf-8").split("\n")[0]
    add_url_to_queue(url)


@APP.context_processor
def inject_globals():
    return {
        "icon": icon,
        "version": version,
    }


@APP.route("/play/<video_id>")
def play(video_id):
    vid = Queue.objects(id=video_id).first_or_404()
    logging.info(vid)
    filename = vid.youtube_dl_json.get("_filename")
    logging.info(filename)
    if not Path(filename).is_file():
        filename = str(Path(filename).with_suffix(".mkv"))
        if not Path(filename).is_file():
            return flask.abort(404)
    logging.info(f"playing {filename}")
    cmd = f"nohup mpv --volume=30 --mute {filename} &"
    logging.info(cmd)
    os.system(cmd)
    vid.lastplayed_epochtime = int(time.time())
    vid.save()
    return flask.Response(
        """
    <html>
        <body>
            <script type="text/javascript">
                window.close();
            </script>
        </body>
    </html>
    """,
        mimetype="text/html",
    )


def make_thumbnail(fp: str):
    if not fp:
        return ""
    f = Path(fp)
    if not f.is_file():
        if not f.with_suffix(".mkv").is_file():
            logging.warning("can't find file")
            return ""
    cmd = ""
    thumb_file = ""

    thumb_try1 = f.with_suffix(".jpg")
    if Path(thumb_try1).is_file():
        cmd = f"ln -s ../{thumb_try1} static/{thumb_try1.name}"
        thumb_file = f"static/{thumb_try1.name}"
    thumb_try2 = Path(str(f) + "_0.jpg")
    if Path(thumb_try2).is_file():
        os.system(f"ln -s ../{thumb_try2} static/{thumb_try2.name}")
        thumb_file = f"static/{thumb_try2.name}"
    thumb_try3 = f.with_suffix(".0.jpg")
    if Path(thumb_try3).is_file():
        cmd = f"ln -s ../{thumb_try3} static/{thumb_try3.name}"
        thumb_file = f"static/{thumb_try3.name}"
    thumb_try4 = f.with_suffix(".webp")
    if Path(thumb_try4).is_file():
        cmd = f"ln -s ../{thumb_try4} static/{thumb_try4.name}"
        thumb_file = f"static/{thumb_try4.name}"

    if cmd:
        logging.info(cmd)
        os.system(cmd)
    else:
        logging.warning("couldn't find thumbnail file")
    return thumb_file


def fix_thumbnails():
    for q in Queue.objects(youtube_dl_json__filename__exists=True):
        q.thumbnail_url = make_thumbnail(q.youtube_dl_json["filename"])
        q.save()


def remove_disk_missing():
    """Remove database entries that aren't on disk any more."""
    for q in Queue.objects(youtube_dl_json__filename__exists=True):
        f = Path(q.youtube_dl_json["filename"])
        print(f)
        if not f.parent.is_dir():
            q.delete()
        else:
            if not f.is_file():
                q.delete()


@APP.route("/collage", methods=["GET", "POST"])
def collage():
    queue = Queue.objects.order_by("-added_epochtime").all()
    return flask.render_template(
        "gallery.jinja2",
        title="lo2",
        queue=queue,
    )


@APP.route("/", methods=["GET", "POST"])
def index():
    time_now = int(time.time())
    page = int(flask.request.args.get("page", 1))
    if flask.request.method == "GET":

        def nice_duration(t):
            return humanize.naturaldelta(dt.timedelta(seconds=t)).capitalize()

        def nice_time(t2):
            return humanize.naturaltime(
                dt.timedelta(seconds=(time_now - t2))
            ).capitalize()

        queue = Queue.objects.order_by("-added_epochtime").paginate(
            page=page, per_page=1000
        )
        queue_count = Queue.objects.count()
        return flask.render_template(
            "index.jinja2",
            title="lo2",
            queue=queue,
            Status=Status,
            youtube_dl_optional_args=youtube_dl_optional_args,
            nice_time=nice_time,
            nice_duration=nice_duration,
            page=page,
            queue_count=queue_count,
        )
    if flask.request.method == "POST":
        if flask.request.form.get("Submit") == "Submit_add_url":
            unsafe_url = flask.request.form.get("new_url")
            youtube_dl_optional_arg = flask.request.form.get("youtube_dl_optional_arg")
            new_item = Queue(
                url=unsafe_url,
                status=Status.QUEUED,
                added_epochtime=int(time.time()),
                youtube_dl_optional_arg=youtube_dl_optional_arg,
            )
            new_item.save()
        return flask.redirect(flask.url_for("index"))


@APP.route("/info/<queue_id>")
def info(queue_id):
    item_json = json.dumps(
        json.loads(Queue.objects(id=queue_id).first_or_404().to_json()), indent=4
    )
    return flask.render_template("info.jinja2", queue_id=queue_id, item_json=item_json)


@APP.route("/delete/<queue_id>")
def delete(queue_id):
    q = Queue.objects(id=queue_id).first_or_404()
    q.delete()
    return flask.redirect(flask.url_for("index"))


def enqueue_from_file(filename):
    import pathlib

    links = pathlib.Path(filename).read_text().split("\n")
    for link in links:
        if not link or not link.strip():
            continue
        if Queue.objects(url=link).first():
            print(f"already exists: {link}")
            continue

        new_item = Queue(
            url=link,
            status=Status.QUEUED,
            added_epochtime=int(time.time()),
            youtube_dl_optional_arg="",
        )
        new_item.save()


def show_urls():
    for q in Queue.objects:
        print(q.url)


def dedupe():
    seen = []
    for q in Queue.objects().order_by("-id"):
        filename = q.youtube_dl_json["filename"]
        if filename in seen:
            print("deleting")
            q.delete()
        else:
            seen.append(filename)


def serve():
    for q in Queue.objects:
        if q.status == Status.RUNNING:
            q.status = Status.ERROR
            q.save()
        if q.status == Status.ERROR:
            logging.info(f"deleting entry with url: {q.url} due to error state")
            q.delete()

    threading.Thread(target=downloader).start()
    APP.run(port=5555, debug=True)


if __name__ == "__main__":
    argh.dispatch_commands(
        [
            serve,
            make_thumbnail,
            fix_thumbnails,
            remove_disk_missing,
            enqueue_from_file,
            show_urls,
            dedupe,
        ]
    )
