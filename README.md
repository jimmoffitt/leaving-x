# leaving-x
A script to publish a Twitter archive to Bluesky.


## Introduction

As a developer, I am no longer interested in working with the Twitter/X API. That's saying a lot from someone who was on the Twitter developer relations team for 8 years (and built with Twitter data for 10). 

There are plenty of reason to move from X, including the pay-to-verify joke, the removal of the trust-and-safety team, and the recent change in Block behavior. As a developer, the $100/month for hobbyist levels of data access is laughable. 

So, this project started as an exercise to start learning the Bluesky API and the underlying AT Protocol. From the start, I loved the underlying concepts and design for a distributing network. A place where the entire ecosystem can not be bought by someone who wants to take it in a direction you do not support. 

For me, the last step for deleting my account was somehow saving the decade of content that I had sometimes curated with intention. Hundreds of fun photographs, screenshots, travel notes, and professional updates. 

So if you want to port your Twitter archive to somewhere else, I highly encourage that. This is not a novel idea, and there are great tools out there to help you do that. Including some that provides this service as a Chrome extension. 

If you are a Python developer, and want to manage the process yourself, you are in the right place ;) 



## Setting up the `.env.local` file

Before running the script, you’ll need to create a `.env.local` file in the root directory of your project. This file contains environment variables necessary for Bluesky API authentication and Twitter archive configuration settings. Follow these steps:

### Copy the example file to create a new .env.local file
```bash
cp .env.local.example .env.local
```

Update the `.env.local` file with your specific settings:


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



Table of Contents
Requirements
Setup
Configuration
Usage
Details
Files Used
Main Functions
Error Handling
License
Requirements
Python 3.8+
Libraries: tweet_archive_parser, bluesky_poster, aiohttp, asyncio, python-dotenv
A valid .env.local file with credentials for both Twitter and Bluesky
Setup
Clone this repository.
Install required dependencies: pip install -r requirements.txt
Prepare the .env.local file in the same directory as the script with the following environment variables:
makefile
Copy code
BLUESKY_HANDLE=<your_bluesky_handle>
BLUESKY_PASSWORD=<your_bluesky_password>
BLUESKY_PDS_URL=<your_bluesky_pds_url>
TWITTER_DATA_ROOT_FOLDER=<path_to_your_twitter_data_folder>
SLEEP_INTERVAL_SECONDS=<desired_delay_in_seconds_between_posts>
Configuration
Make sure the TWITTER_DATA_ROOT_FOLDER points to the root folder of your downloaded Twitter archive, which should include:

tweets.js: Contains the tweet data.
tweets_media: Directory with images associated with the tweets.
Usage
To run the script: python script_name.py

The script will:

Load the last processed tweet's timestamp from last_processed_timestamp.txt.
Parse the Twitter archive to load tweets created after the last processed timestamp.
Filter out replies and extract metadata for posting.
Post each tweet to Bluesky, introducing a delay to avoid rate limits.
Update last_processed_timestamp.txt to track progress.
Details
Files Used
tweets.js: A file containing tweet data from the Twitter archive.
tweets_media/: Folder with media files (images) associated with the tweets.
last_processed_timestamp.txt: Stores the timestamp of the last successfully posted tweet to continue from that point on the next run.
Main Functions
load_last_processed_timestamp(): Loads the last posted tweet's timestamp.
save_last_processed_timestamp(timestamp): Saves the timestamp of the most recent post to file.
create_post(config, tweet, bluesky_poster): Posts a tweet to Bluesky, handling any errors and updating the timestamp upon success.
main(): Loads environment variables, configures components, loads tweets, filters, posts, and saves progress.
Error Handling
Errors during the posting process are caught and printed. If an error occurs with a specific tweet, it is skipped, and the script continues to the next one.

License
This project is licensed under the MIT License.