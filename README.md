# leaving-x
Python code for publishing Twitter archives to Bluesky.


## Introduction

As a developer, I am no longer interested in working with the Twitter/X API. That's saying a lot from someone who was on the Twitter developer relations team for 8 years (and built with Twitter data for 10). 

There are plenty of reason to move from X, including the paying for verification, the removal of the trust-and-safety team, and the recent change in Block behavior. For developers, the $100/month for hobbyist levels of data access can be hard to justify. 

So, this project started as an exercise to start learning the Bluesky API and the underlying AT Protocol. From the start, I loved the underlying concepts and design for a distributed network. A place where you and your data can be hosted where you want. Overall, the protocol reads like rebuilding the concepts that Twitter evolved to and re-designing them from the ground up. 

For me, the last step for deleting my account was somehow saving the decade of content that I had sometimes curated with intention. Hundreds of fun photographs, screenshots, travel notes, and professional updates. I love photography, so that archive of photos was top of mind. 

If you are thinking about archiving your Tweet history, this tool is one way to do that. Assuming you want to work with Python, are OK without a front-end, and want to learn the Bluesky API. (If you are not interested in working with your own Python code, other migration tools run as Chrome extensions, like Porto.)

So, if you are a Python developer, and want to manage the process yourself, you are in the right place ;) 

The `leaving_x.py` script provides a tool for posting Twitter archive content to Bluesky. The sript relies on `tweet_archive_parser.py` code that provides a TwitterArchiveParser class. There is also a `bluesky_poster.py` file that manages Bluesky requests with a BlueskyPoster class.  

### So, tell me more about this tool 
* Configuration is managed with a `.env.local` file that sets *environment variables*. These include Bluesky authentication details and script options (archive data path and posting interval)
* This tool knows how to navigate the Twitter archive file structure and parse Tweet JSON objects. These objects have evolved since 2006, and unexpected results are likely due to the code not parsing correctly (or incompletely). 
* The main mission of this tool is to manage the posting to Bluesky. Currently, it posts on a specified interval (which defaults to every 10 minutes).  Automated Posting: Read and post from a Twitter archive.
* This tool is designed to manage the posting images. Much of the code here is focused on mapping image file names to Tweet metadata, uploading images to Bluesky, and attaching the images to the Bluesky `createRecord` request. 

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [License](#license)

## Overview

The `leaving_x.py` script reads from a downloaded Twitter archive, and then posts the content to Bluesky using its API. The script manages authentication, posts on a configured interval, and handles various media types.

The `leaving_x.py` depends on two classes:
* TweetArchiveParser: Parses Twitter archive data.
* BlueskyPoster: Posts content to Bluesky.

**Script details**:
* Authentication details, and script options are stored in a `.env.local` file. Scipt option include archive data path and posting interval.
* If the Tweet image is available, the script will upload the file to Bluesky and attach image metadata to the request. 
* Currently, the script runs on a set schedule (defaults to posting every 10 minutes). 

## Installation

1. **Clone the repository**

   Clone the repository to your local environment:

   ```bash
   git clone https://github.com/jimmoffitt/leaving-x.git
   cd leaving-x

2. **Install requirements

Ensure you have Python 3.7+ installed. Then, install the required libraries:

    ```bash
    pip install -r requirements.txt

3. Set up Environment Variables

Create a .env.local file in the root directory based on .env.local.example (see the Configuration section for details).


## Configuration

Before running the script, you’ll need to create a `.env.local` file in the root directory of your project. This file contains environment variables necessary for Bluesky API authentication and Twitter archive configuration settings. Follow these steps:

1. Copy the example file to create a new .env.local file
```bash
cp .env.local.example .env.local
```

2. Update the `.env.local` file with your specific settings:

```bash
# Bluesky API authentication details
BLUESKY_PDS_URL = 'https://bsky.social'
BLUESKY_HANDLE = '{your_handle}.bsky.social'  # Replace `{your_handle}` with your actual Bluesky handle
BLUESKY_PASSWORD = 'your_password'            # Replace `your_password` with your Bluesky password

# Directory for Twitter data (ensure `tweets.js` and `tweets_media` folder are here)
TWITTER_DATA_ROOT_FOLDER = './twitter_data'

# Script configuration
SLEEP_INTERVAL_SECONDS = 60  # Adjust interval between posts (in seconds)
```

After setting up your `.env.local` file with these values, the script will be able to read the environment variables needed for authentication and data handling.

## Usage



## More details 

### External Libraries
* tweet_archive_parser: Parses Twitter archive data.
* bluesky_poster: Posts content to Bluesky.
* asyncio: Asynchronous programming.
* aiohttp: Asynchronous HTTP requests.
* datetime: Date and time manipulation.
* pathlib: File path manipulation.
* os: Operating system interactions.
* dotenv: Environment variable loading.

### Files Used
* tweets.js: A file containing tweet data from the Twitter archive.
* tweets_media/: Folder with media files (images) associated with the * tweets.
* last_processed_timestamp.txt: Stores the timestamp of the last successfully posted tweet to continue from that point on the next run.

[] TODO
### Main Functions
* `leaving_x.py` **main**: The main function that orchestrates the script's logic. Loads the Tweet archive into a list/array. 
* `bluesky_poster.py` **create_post**: Creates a post on Bluesky.
* `leaving_x.py` **load_last_processed_timestamp**: Loads the last processed timestamp from a file.
* `leaving_x.py` **save_last_processed_timestamp**: Saves the last processed timestamp to a file.

# Notes and todos

The script will:

* Load the last processed tweet's timestamp from last_processed_timestamp.txt.
* Parse the Twitter archive to load tweets created after the last processed timestamp.
* Filter out replies and extract metadata for posting.
* Post each tweet to Bluesky, introducing a delay to avoid rate limits.
* Update last_processed_timestamp.txt to track progress.


## Error Handling
Errors during the posting process are caught and printed. If an error occurs with a specific tweet, it is skipped, and the script continues to the next one.

License
This project is licensed under the Apache 2.0 License.
