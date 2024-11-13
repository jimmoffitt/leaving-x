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

async def create_post(config, tweet, bluesky_poster): 
    try:
        # Directly await the asynchronous create_post method
        await bluesky_poster.create_post(config, tweet)
        
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
    SLEEP_INTERVAL_SECONDS = os.getenv("SLEEP_INTERVAL_SECONDS")

    try:
        # Attempt to convert it to a float
        SLEEP_INTERVAL_SECONDS = float(SLEEP_INTERVAL_SECONDS)
    except (TypeError, ValueError):
        # Handle the case where it's not a valid float (e.g., if it's None or an invalid string)
        print("Invalid or missing SLEEP_INTERVAL value; using default of 1.0 seconds.")
        SLEEP_INTERVAL_SECONDS = 60.0  # Default value, or you could raise an error if appropriate

    # A way to pass configuration details to other components. 
    config = {}

    config['handle'] = BLUESKY_HANDLE
    config['password'] = BLUESKY_PASSWORD
    config['pds_url'] = BLUESKY_PDS_URL
    config['images_folder'] = str(script_dir / TWITTER_DATA_ROOT_FOLDER / 'tweets_media')
    config['tweet_objects_file'] = str(script_dir / TWITTER_DATA_ROOT_FOLDER / 'tweets.js')
    
    # Create TweetParser instance. 
    tweet_parser = TweetArchiveParser(config['tweet_objects_file'])

    # Create BlueskyPoster instance. 
    bluesky_poster = BlueskyPoster(pds_url=BLUESKY_PDS_URL, handle=BLUESKY_HANDLE, password=BLUESKY_PASSWORD) 
    
    # Load a collection of Tweets loaded from a downloaded Twitter account archives. 
    tweets = []
    tweets = tweet_parser.load_twitter_archive(config['tweet_objects_file'])

    # Let's sort it!
    tweets.sort(key=lambda tweet: datetime.strptime(tweet["created_at"], "%a %b %d %H:%M:%S +0000 %Y")) 
    
    # Filter out Replies? 
    tweets = tweet_parser.filter_out_replies(tweets)

    # OK, filter the Tweet collection and extract the metdata needed for posting and wanted for statistics. 
    tweets = tweet_parser.extract_metadata(tweets)

    # Generate a set of statistics and time-series data from the Tweet collection. 
    print(f"{tweet_parser.get_stats(tweets)}")
      
    # Load last processed timestamp
    last_processed_timestamp = load_last_processed_timestamp()

    if last_processed_timestamp:
        tweets = [tweet for tweet in tweets if 
                  datetime.strptime(tweet['timestamp'], '%Y-%m-%d %H:%M:%S') > last_processed_timestamp]
       
    async with aiohttp.ClientSession() as session:
        tasks = []
        for tweet in tweets:
            task = asyncio.create_task(create_post(config, tweet, bluesky_poster))
            tasks.append(task)

            # Introduce a small delay to avoid hitting rate limits
            await asyncio.sleep(SLEEP_INTERVAL_SECONDS)  # 3.6 seconds = 1000 posts per hour
            
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())