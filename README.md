# leaving-x
This project provides a set of Python scripts to read a downloaded Twitter archive and publish its content—including text, photos, videos, and quote tweets—to the Bluesky social network. It also includes utility scripts for managing and cleaning up the posts on Bluesky.

The main script is designed to run periodically, posting old tweets chronologically and keeping track of its progress so it can resume where it left off.

## Features

* **Chronological Posting**: Posts tweets from your archive in the order they were originally created.
* **Media Support**: Automatically uploads and attaches photos, GIFs, and videos to your posts.
* **Quote Tweet Handling**: Re-creates quote tweets by first posting the quoted tweet, then embedding it in the main post.
* **Intelligent Resumption**: Remembers the last tweet successfully posted and resumes from that point on the next run.
* **Flexible Control**: Use command-line arguments to start from a specific time, reprocess all videos, or perform a dry run without posting.
* **Post Management Utilities**: Includes scripts to delete posts from your Bluesky feed based on a timeframe or by searching for specific text within the posts.

## Introduction

As a developer, I am no longer interested in working with the Twitter/X API. That's saying a lot from someone who was on the Twitter developer relations team for 8 years (and built with Twitter data for 10). 

There are plenty of reason to move from X, including the paying for verification, the removal of the trust-and-safety team, and the recent change in Block behavior. For developers, the $100/month for hobbyist levels of data access can be hard to justify. 

So, this project started as an exercise to start learning the Bluesky API and the underlying AT Protocol. From the start, I loved the underlying concepts and design for a distributed network. A place where you and your data can be hosted where you want. Overall, the protocol reads like rebuilding the concepts that Twitter evolved to and re-designing them from the ground up. 

For me, the last step for deleting my account was somehow saving the decade of content that I had sometimes curated with intention. Hundreds of fun photographs, screenshots, travel notes, and professional updates. I love photography, so that archive of photos was top of mind. 

If you are thinking about archiving your Tweet history, this tool is one way to do that. Assuming you want to work with Python, are OK without a front-end, and want to learn the Bluesky API. (If you are not interested in working with your own Python code, other migration tools run as Chrome extensions, like Porto.)

So, if you are a Python developer, and want to manage the process yourself, you are in the right place ;) 

The `leaving_x.py` script provides a tool for posting Twitter archive content to Bluesky. The sript relies on `tweet_archive_parser.py` code that provides a TwitterArchiveParser class. There is also a `bluesky_poster.py` file that manages Bluesky requests with a BlueskyPoster class.  

## Setup

### 1. Prerequisites

* Python 3.9+
* A complete downloaded Twitter archive (including the `tweets.js` file and `data/tweets_media` folder).

### 2. Installation

Clone the repository to your local machine:

```bash
git clone https://github.com/jimmoffitt/leaving-x.git
cd leaving-x
```

Install the required Python packages:

```bash
pip install -r requirements.txt
```

*(You will need to create a `requirements.txt` file in your project directory with the following content):*

```
aiohttp==3.11.10
atproto==0.0.56
debugpy==1.8.14
httpx==0.28.1
python-dotenv==1.0.1
PyYAML==6.0.2
requests==2.32.3
```

### 3. Configuration

The scripts are configured using a `.env.local` file.

1.  **Create the file**: In the root of the project, create a file named `.env.local`.
2.  **Add your credentials**: Copy the example below into the file and replace the placeholder values with your own information.

**.env.local Example:**

```env
# Your Bluesky account handle (e.g., your-name.bsky.social)
BLUESKY_HANDLE="your-handle.bsky.social"

# An app-specific password created in Bluesky settings
BLUESKY_PASSWORD="xxxx-xxxx-xxxx-xxxx"

# The PDS URL for Bluesky (usually does not need to be changed)
BLUESKY_PDS_URL="[https://bsky.social](https://bsky.social)"

# The name of your Twitter data folder
TWITTER_DATA_ROOT_FOLDER="twitter_data"

# The time to wait between posts, in seconds (e.g., 600 = 10 minutes)
SLEEP_INTERVAL_SECONDS=600
```

### 4. Twitter Archive

Place your unzipped Twitter archive folder into the project directory. The folder name should match the `TWITTER_DATA_ROOT_FOLDER` value in your `.env.local` file. The script expects the following structure:

```
leaving-x/
|-- twitter_data/
|   |-- tweets.js
|   +-- data/
|       +-- tweets_media/
|           +-- ... (your image and video files)
|-- leaving_x.py
|-- bluesky_facets.py
|-- bluesky_poster.py
|-- bluesky_video.py
|-- tweet_archive_parser.py
|-- delete_posts.py
+-- .env.local
```

---

## Usage

### Posting Tweets (`leaving_x.py`)

This is the main script for publishing your archive.

* **Run normally (resumes from last post)**:
    ```bash
    python leaving_x.py
    ```
* **Perform a dry run to see what would be posted**:
    ```bash
    python leaving_x.py --dry-run
    ```
* **Start posting from a specific UTC timestamp**:
    ```bash
    python leaving_x.py --start-from "2022-01-15 14:30:00"
    ```
* **Start posting from a specific local timestamp**:
    ```bash
    python leaving_x.py --start-from "2022-01-15 08:30:00" --timezone local
    ```
* **Reprocess and post all video tweets from the archive**:
    *(This mode does not update the last processed timestamp).*
    ```bash
    python leaving_x.py --reprocess-videos
    ```

### Deleting Posts

These scripts help clean up your Bluesky feed. Always use `--dry-run` first to confirm!

* **`delete_posts.py`**: Deletes posts within a specific UTC time window.
    ```bash
    python delete_posts.py --start-time "2024-06-15 00:00:00" --end-time "2024-06-18 23:59:59" --dry-run
    ```
    You can also add an optional `--match-string` to further filter the posts in that time window.
    ```bash
    python delete_posts.py --start-time "2024-06-18 00:00:00" --end-time "2024-06-18 23:59:59" --match-string "Broncos"
    ```
* **`delete_by_text.py`**: Deletes all posts containing a specific substring (e.g., the "Tweeted at" footer).
    ```bash
    python delete_by_text.py --filter-text "Tweeted at" --dry-run
    ```

---

## Debugging in VS Code

This project is configured for easy debugging in Visual Studio Code.

1.  Open the project folder in VS Code.
2.  Navigate to the **Run and Debug** view (Ctrl+Shift+D).
3.  A dropdown menu at the top will contain pre-configured launch options for all scripts (e.g., "Run Poster: Dry Run", "Run Deleter: Dry Run").
4.  Set breakpoints in the code by clicking in the gutter next to the line numbers.
5.  Select a configuration from the dropdown and press the green "Start Debugging" button (F5).
