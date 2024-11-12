from tweet_archive_parser import TweetArchiveParser
from bluesky_poster import BlueskyPoster
import asyncio
import aiohttp
from datetime import datetime, timedelta
from pathlib import Path
import os
from dotenv import load_dotenv

LAST_PROCESSED_TIMESTAMP_FILE = "last_processed_timestamp.txt"

def load_last_processed_timestamp():
    """Loads the last processed timestamp from file, or returns None if not found."""
    try:
        with open(LAST_PROCESSED_TIMESTAMP_FILE, "r") as f:
            timestamp_str = f.read().strip()
            return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
    except FileNotFoundError:
        return None

def save_last_processed_timestamp(timestamp):
    """Saves the last processed timestamp to file."""
    with open(LAST_PROCESSED_TIMESTAMP_FILE, "w") as f:
        f.write(timestamp.strftime('%Y-%m-%d %H:%M:%S'))

async def create_post_async(config, tweet, bluesky_poster): 
    # Run the synchronous create_post method in a separate thread
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(
            None,  # Use the default executor
            bluesky_poster.create_post,  # The function to execute
            config, 
            tweet
        )
      # Save the timestamp only after successful post
        save_last_processed_timestamp(datetime.strptime(tweet['timestamp'], '%Y-%m-%d %H:%M:%S')) 
    except Exception as e:
        print(f"Error posting tweet: {e}")  

async def main():
    # Get the directory of the current script
    script_dir = Path(__file__).parent 
    # Construct the path to .env.local within the script's directory
    env_path = script_dir / '.env.local'
    load_dotenv(dotenv_path=env_path)

    # Load from .env file.
    BLUESKY_HANDLE = os.getenv("BLUESKY_HANDLE")
    BLUESKY_PASSWORD = os.getenv("BLUESKY_PASSWORD")
    BLUESKY_PDS_URL = os.getenv("BLUESKY_PDS_URL")
    TWITTER_DATA_ROOT_FOLDER = os.getenv("TWITTER_DATA_ROOT_FOLDER")

    # A way to pass configuration details to other components. 
    config = {}

    config['handle'] = BLUESKY_HANDLE
    config['password'] = BLUESKY_PASSWORD
    config['pds_url'] = BLUESKY_PDS_URL
    config['images_folder'] = str(script_dir / TWITTER_DATA_ROOT_FOLDER / 'tweets_media')
    config['tweet_objects_file'] = str(script_dir / TWITTER_DATA_ROOT_FOLDER / 'tweets.js')
    
    # Create TweetParser instance. 
    twitter_parser = TweetArchiveParser(config['tweet_objects_file'])

    # Create BlueskyPoster instance. 
    bluesky_poster = BlueskyPoster(pds_url=BLUESKY_PDS_URL, handle=BLUESKY_HANDLE, password=BLUESKY_PASSWORD) 
    
    # Load a collection of Tweets loaded from a downloaded Twitter account archives. 
    tweets_raw = []
    tweets_raw = twitter_parser.load_twitter_archive()

    tweets = []

    # OK, filter the Tweet collection and extract the metdata needed for posting and wanted for statistics. 
    tweets = twitter_parser.extract_metadata(tweets_raw)

    # Generate a set of statistics and time-series data from the Tweet collection. 
    print(f"{twitter_parser.get_stats2(tweets)}")
      
    # Load last processed timestamp
    last_processed_timestamp = load_last_processed_timestamp()

    if last_processed_timestamp:
        tweets = [tweet for tweet in tweets if 
                  datetime.strptime(tweet['timestamp'], '%Y-%m-%d %H:%M:%S') > last_processed_timestamp]
       
    async with aiohttp.ClientSession() as session:
        tasks = []
        for tweet in tweets:
            task = asyncio.create_task(create_post_async(config, tweet, bluesky_poster))
            tasks.append(task)

            # Introduce a small delay to avoid hitting rate limits
            await asyncio.sleep(3.6)  # 3.6 seconds = 1000 posts per hour

        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())