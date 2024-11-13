# leaving-x
A script to publish a Twitter archive to Bluesky


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