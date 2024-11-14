# leaving-x
A script to publish a Twitter archive to Bluesky.


## Introduction

As a developer, I am no longer interested in working with the Twitter/X API. That's saying a lot from someone who was on the Twitter developer relations team for 8 years (and built with Twitter data for 10). 

There are plenty of reason to move from X, including the pay-to-verify joke, the removal of the trust-and-safety team, and the recent change in Block behavior. As a developer, the $100/month for hobbyist levels of data access is laughable. 

So, this project started as an exercise to start learning the Bluesky API and the underlying AT Protocol. From the start, I loved the underlying concepts and design for a distributed network. A place where the entire ecosystem can not be bought by someone who wants to take it in a direction you do not support. 

For me, the last step for deleting my account was somehow saving the decade of content that I had sometimes curated with intention. Hundreds of fun photographs, screenshots, travel notes, and professional updates. 

So if you want to port your Twitter archive to somewhere else, I highly encourage that. This is not a novel idea, and there are great tools out there to help you do that. Including some that provides this service as a Chrome extension. 

If you are a Python developer, and want to manage the process yourself, you are in the right place ;) 



The `BlueskyPoster` class provides a tool for posting Twitter archive content to Bluesky, enabling seamless transition of posts from Twitter (X) to Bluesky’s platform. The tool allows for uploading images, scheduling posts, and managing authentication with Bluesky's API.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [License](#license)

## Overview

This script reads from a downloaded Twitter archive, then posts the content to Bluesky using its API. You can manage authentication, configure posting intervals, and handle various media types, making it an efficient way to migrate posts to Bluesky.

## Features

- **Automated Posting**: Read and post from a Twitter archive.
- **Media Support**: Upload and post images associated with your Twitter archive.
- **Scheduling**: Set intervals between posts for a timed rollout.
- **Environment Configuration**: Easily configure API credentials and archive locations.


## Installation

1. **Clone the repository**

   Clone the repository to your local environment:

   ```bash
   git clone https://github.com/jimmoffitt/leaving-x.git
   cd leaving-x

2. **Install requirements

Ensure you have Python 3.7+ installed. Then, install required libraries:

    ```bash
    pip install -r requirements.txt

3. Set up Environement Variables

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



# Notes and todos

The script will:

* Load the last processed tweet's timestamp from last_processed_timestamp.txt.
* Parse the Twitter archive to load tweets created after the last processed timestamp.
* Filter out replies and extract metadata for posting.
* Post each tweet to Bluesky, introducing a delay to avoid rate limits.
* Update last_processed_timestamp.txt to track progress.

## Details
Files Used
* tweets.js: A file containing tweet data from the Twitter archive.
* tweets_media/: Folder with media files (images) associated with the * tweets.
* last_processed_timestamp.txt: Stores the timestamp of the last successfully posted tweet to continue from that point on the next run.

## Main Functions
* load_last_processed_timestamp(): Loads the last posted tweet's timestamp.
* save_last_processed_timestamp(timestamp): Saves the timestamp of the most recent post to file.
* create_post(config, tweet, bluesky_poster): Posts a tweet to Bluesky, handling any errors and updating the timestamp upon success.
main(): Loads environment variables, configures components, loads tweets, filters, posts, and saves progress.

[] TODO
## Error Handling
Errors during the posting process are caught and printed. If an error occurs with a specific tweet, it is skipped, and the script continues to the next one.

License
This project is licensed under the MIT License.