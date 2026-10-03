# leaving-x
This project provides a set of Python scripts to read a downloaded Twitter archive and publish its content—including text, photos, GIFs and videos—to the Bluesky social network.

Posts are **backdated** to when they were originally Tweeted, so they appear in your Bluesky profile in their original order (2008, 2009, ...) without flooding your followers' feeds. A companion script then brings old Tweets back each day as **"On this day"** posts.

This is running at [snowman-ghost.bsky.social](https://bsky.app/profile/snowman-ghost.bsky.social), which hosts the archive of the @snowman Twitter account.

## Features

* **Backdated posting**: With `--backdate`, each post's `createdAt` is set to the original Tweet time, so the archive reads chronologically on your profile.
* **"On this day" reposts**: `on_this_day.py` reposts Tweets from today's date in earlier years, at their original time of day, with an "On this day in YYYY:" line. Once the new post is up, the previous copy (the backdated one, or last year's "On this day" post) is deleted, so each Tweet lives in one place.
* **Media support**: Uploads and attaches up to four photos per post, plus GIFs and videos. If a media upload fails, the Tweet is skipped (and retried on the next run) rather than posted without its media.
* **Replies with media**: Replies are normally skipped, since the Tweet being replied to isn't in your archive. Replies with photos or video are kept, with their leading @handles moved into a "Replying to @... on Twitter:" line.
* **Restart-safe**: Every post is recorded in `posted_records.json` (Tweet ID → Bluesky post). A stopped run can be restarted and only posts what's missing.
* **Raspberry Pi deployment**: systemd units and a sync script for running everything on a Pi (or any Linux box).
* **Post management utilities**: `delete_posts.py` deletes posts in a time window, optionally only those containing some text.

## Introduction

As a developer, I am no longer interested in working with the Twitter/X API. That's saying a lot from someone who was on the Twitter developer relations team for 8 years (and built with Twitter data for 10). 

There are plenty of reason to move from X, including the paying for verification, the removal of the trust-and-safety team, and the recent change in Block behavior. For developers, the $100/month for hobbyist levels of data access can be hard to justify. 

So, this project started as an exercise to start learning the Bluesky API and the underlying AT Protocol. From the start, I loved the underlying concepts and design for a distributed network. A place where you and your data can be hosted where you want. Overall, the protocol reads like rebuilding the concepts that Twitter evolved to and re-designing them from the ground up. 

For me, the last step for deleting my account was somehow saving the decade of content that I had sometimes curated with intention. Hundreds of fun photographs, screenshots, travel notes, and professional updates. I love photography, so that archive of photos was top of mind. 

If you are thinking about archiving your Tweet history, this tool is one way to do that. Assuming you want to work with Python, are OK without a front-end, and want to learn the Bluesky API. (If you are not interested in working with your own Python code, other migration tools run as Chrome extensions, like Porto.)

So, if you are a Python developer, and want to manage the process yourself, you are in the right place ;) 

The `leaving_x.py` script provides a tool for posting Twitter archive content to Bluesky. The sript relies on `tweet_archive_parser.py` code that provides a TwitterArchiveParser class. There is also a `bluesky_poster.py` file that manages Bluesky requests with a BlueskyPoster class.

The `leaving_x.py` script posts Twitter archive content to Bluesky, and `on_this_day.py` handles the daily "On this day" reposts. Both rely on `tweet_archive_parser.py` (the `TweetArchiveParser` class, which reads the archive) and `bluesky_poster.py` (the `BlueskyPoster` class, which manages Bluesky requests).

## What the posts look like

A Tweet's text is posted as-is, minus its `t.co` media links. Mentions of Twitter handles stay plain text, so they don't link to (or notify) anyone on Bluesky.

A reply with a photo:

```
Replying to @MDCinMT and 7 others on Twitter:

Yes, true. That's my board too. ...
```

The same Tweet when it comes back as an "On this day" post:

```
On this day in 2021:

Replying to @MDCinMT and 7 others on Twitter:

Yes, true. That's my board too. ...
```

Posts are trimmed (with "…") to fit Bluesky's 300-character limit.

## Setup

### 1. Prerequisites

* Python 3.9+
* A complete downloaded Twitter archive (including the `tweets.js` file and the `tweets_media` folder).

### 2. Installation

Clone the repository to your local machine:

```bash
git clone https://github.com/jimmoffitt/leaving-x.git
cd leaving-x
```

Install the required Python packages:

```bash
pip install -r deploy/requirements-pi.txt
```

(`deploy/requirements-pi.txt` lists just what the scripts import. `requirements.txt` is a full freeze of the original Python 3.9 development environment.)

### 3. Configuration

The scripts are configured using a `.env.local` file in the root of the project. Copy `example.env.local` and fill in your own values:

```env
# Your Bluesky account handle (e.g., your-name.bsky.social)
BLUESKY_HANDLE="your-handle.bsky.social"

# An app-specific password created in Bluesky settings
BLUESKY_PASSWORD="xxxx-xxxx-xxxx-xxxx"

# The PDS URL for Bluesky (usually does not need to be changed)
BLUESKY_PDS_URL="https://bsky.social"

# The name of your Twitter data folder
TWITTER_DATA_ROOT_FOLDER="twitter_data"

# The time to wait between posts, in seconds (e.g., 60 = one post a minute)
SLEEP_INTERVAL_SECONDS=60
```

### 4. Twitter Archive

Copy `tweets.js` and the `tweets_media` folder from your unzipped Twitter archive's `data` folder into a folder whose name matches `TWITTER_DATA_ROOT_FOLDER`:

```
leaving-x/
|-- twitter_data/
|   |-- tweets.js
|   +-- tweets_media/
|       +-- ... (your image and video files)
|-- leaving_x.py
|-- on_this_day.py
|-- tweet_archive_parser.py
|-- bluesky_poster.py
|-- bluesky_facets.py
|-- bluesky_video.py
|-- posted_records.py
|-- delete_posts.py
|-- deploy/
+-- .env.local
```

---

## Usage

### Posting the archive (`leaving_x.py`)

* **Post the whole archive, backdated** (what you probably want):
    ```bash
    python leaving_x.py --backdate --start-from "2000-01-01 00:00:00"
    ```
* **Perform a dry run to see what would be posted**:
    ```bash
    python leaving_x.py --backdate --dry-run
    ```
* **Resume from the last post** (the default, using `last_processed_timestamp.txt`):
    ```bash
    python leaving_x.py --backdate
    ```
* **Start posting from a specific UTC timestamp** (add `--timezone local` for local time):
    ```bash
    python leaving_x.py --backdate --start-from "2022-01-15 14:30:00"
    ```
* **Post specific Tweets** (handy for testing):
    ```bash
    python leaving_x.py --backdate --tweet-ids 471150776228671488,1377811051723382784
    ```
* **Post only replies that have photos or video**:
    ```bash
    python leaving_x.py --backdate --media-replies
    ```
* **Reprocess and post all video Tweets**:
    ```bash
    python leaving_x.py --reprocess-videos
    ```

Without `--backdate`, posts are stamped with the current time.

Tweets already in `posted_records.json` are skipped (except with `--tweet-ids` and `--reprocess-videos`), so stopping and restarting a run is safe. The `--tweet-ids`, `--media-replies` and `--reprocess-videos` modes don't update `last_processed_timestamp.txt`.

### "On this day" reposts (`on_this_day.py`)

Run it every few minutes (see the systemd timer below). Each run reposts any of today's Tweets whose original time of day has passed and that haven't been reposted this year. Times are in UTC, so a Tweet comes back at the same local clock time it was first posted (give or take an hour for daylight saving). Feb 29 Tweets come back on Feb 28 in non-leap years.

* **See what's due today, without posting**:
    ```bash
    python on_this_day.py --dry-run
    ```
* **See what would be posted on another day**:
    ```bash
    python on_this_day.py --dry-run --date 2026-12-25
    ```

### Deleting posts (`delete_posts.py`)

Deletes posts within a UTC time window, optionally only those containing some text. It asks for confirmation before deleting. Always use `--dry-run` first!

```bash
python delete_posts.py --start-time "2024-06-15 00:00:00" --end-time "2024-06-18 23:59:59" --dry-run
python delete_posts.py --start-time "2024-06-18 00:00:00" --end-time "2024-06-18 23:59:59" --match-string "Broncos"
```

Note that the time window applies to each post's `createdAt`, which for backdated posts is the original Tweet time.

---

## Running on a Raspberry Pi

The `deploy/` folder runs this on a Pi (or any Linux box with systemd):

* `leaving-x-on-this-day.timer` / `.service` run `on_this_day.py` every 5 minutes. Each run takes a few seconds and exits, so nothing stays resident.
* `leaving-x-backfill.service` is a one-off that posts the whole archive, backdated, at one post a minute (~2 days for ~2,700 Tweets). It restarts on failure and is not started at boot.
* `sync_to_pi.sh` deploys from your Mac:
    1. Backs up the Pi's `posted_records.json` into `backups/`. The Pi is the source of truth for what's been posted, so this file is never pushed to it.
    2. Pushes committed code to a git repo on the Pi over ssh (it refuses to run with uncommitted changes).
    3. Copies `.env.local` and the Twitter archive (only changed files after the first run).
    4. With `--install`, creates the venv, installs packages, and installs and enables the systemd units.

```bash
deploy/sync_to_pi.sh --dry-run --install   # see what it would do
deploy/sync_to_pi.sh --install             # first deploy
deploy/sync_to_pi.sh                       # later code updates
ssh pi sudo systemctl start leaving-x-backfill
```

It deploys to `pi:projects/leaving-x` by default (the `pi` ssh alias); set `DEPLOY_HOST` and `DEPLOY_DIR` to change that. The unit files assume user `jim` and `/home/jim/projects/leaving-x`.

Keeping an eye on things:

```bash
ssh pi journalctl -u leaving-x-backfill -f          # backfill progress
ssh pi journalctl -u leaving-x-on-this-day -n 50    # recent "On this day" runs
ssh pi systemctl list-timers leaving-x-on-this-day.timer
```

---

## Debugging in VS Code

This project is configured for easy debugging in Visual Studio Code.

1.  Open the project folder in VS Code.
2.  Navigate to the **Run and Debug** view (Ctrl+Shift+D).
3.  A dropdown menu at the top will contain pre-configured launch options for the poster and the deleter (e.g., "Run Poster: Dry Run from Last Post", "Run Deleter: Dry Run").
4.  Set breakpoints in the code by clicking in the gutter next to the line numbers.
5.  Select a configuration from the dropdown and press the green "Start Debugging" button (F5).
