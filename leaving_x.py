from tweet_archive_parser import TweetArchiveParser
from bluesky_poster import BlueskyPoster
import asyncio
import aiohttp
from datetime import datetime, timezone #, timedelta?
from pathlib import Path
import os
from dotenv import load_dotenv
import argparse # Added for command-line arguments

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

async def create_post(config, tweet, bluesky_poster, save_timestamp_on_success=True):
    """
    Asynchronously creates a post, handling quote tweets first.
    This function's single responsibility is to perform a REAL post.
    """
    try:
        # If this is a quote tweet, we must create the post being quoted FIRST.
        if 'quoted_status' in tweet and tweet.get('quoted_status'):
            print(f"-> This is a quote tweet. Processing the quoted post first...")
            
            # Call the poster to create the post that is being quoted
            quoted_post_record = await bluesky_poster.create_post(config, tweet['quoted_status'])
            
            # If successful, attach its URI and CID to the main tweet object
            if quoted_post_record and 'uri' in quoted_post_record:
                print(f"-> Quoted post created successfully. Embedding it now.")
                tweet['quoted_post_uri'] = quoted_post_record.get('uri')
                tweet['quoted_post_cid'] = quoted_post_record.get('cid')
            else:
                print("Warning: Failed to create the quoted post. Posting without the quote embed.")
                if 'quoted_status' in tweet:
                    del tweet['quoted_status']

        # 1. Capture the return value from the main post creation call
        final_post_record = await bluesky_poster.create_post(config, tweet)
        
        # 2. Check if the post was successful and build the new detailed message
        if final_post_record:
            post_url = f"https://bsky.app/profile/{config['handle']}/post/{final_post_record.get('uri', '').split('/')[-1]}"
            text_snippet = tweet.get('text', '').split('\n')[0][:75]
            
            message = f"✅ SUCCESS: Posted \"{text_snippet}...\""
            
            # Describe the attachment based on the original tweet object
            if tweet.get('media_type') in ['video', 'gif']:
                message += f" with {len(tweet.get('media_filenames',[]))} {tweet['media_type']}(s)"
            elif tweet.get('media_type') == 'photo':
                message += f" with {len(tweet.get('media_filenames',[]))} photo(s)"
            elif 'quoted_post_uri' in tweet:
                message += " with a quote tweet"

            message += f". URL: {post_url}"
            print(message)
        else:
            print(f"❌ FAILED: Post creation failed for Tweet from {tweet['timestamp']}.")

        # 3. The decision to save the timestamp now also depends on a successful post
        if save_timestamp_on_success and final_post_record:
            ts_to_save = datetime.strptime(tweet['timestamp'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
            save_last_processed_timestamp(ts_to_save)




    except aiohttp.ClientError as e:
        print(f"Network error posting tweet from {tweet.get('timestamp')}: {e}")
    except Exception as e:
        print(f"Unexpected error posting tweet from {tweet.get('timestamp')}: {e}")

async def main():
    """
    Loads environment variables, processes Twitter archive, and posts tweets to Bluesky
    based on command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Post Twitter archive tweets to Bluesky.", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--start-from', type=str,
                       help='Start processing from a specific timestamp (format: "YYYY-MM-DD HH:MM:SS").')
    parser.add_argument('--timezone', type=str, default='utc', choices=['utc', 'local'],
                       help="Specify the timezone for the --start-from timestamp. Defaults to 'utc'.")
    parser.add_argument('--reprocess-videos', action='store_true',
                       help='Reprocess all video tweets from the beginning.')
    parser.add_argument('--dry-run', action='store_true',
                       help='Simulate the posting process without creating actual posts.\nSets interval to 1 second and does not save last processed time.')
    args = parser.parse_args()

    # --- Argument Validation ---
    if args.reprocess_videos and args.start_from:
        parser.error("--reprocess-videos and --start-from cannot be used together.")

    # --- Configuration Loading ---
    script_dir = Path(__file__).parent
    env_path = script_dir / '.env.local'
    load_dotenv(dotenv_path=env_path)

    config = {
        'handle': os.getenv("BLUESKY_HANDLE"),
        'password': os.getenv("BLUESKY_PASSWORD"),
        'pds_url': os.getenv("BLUESKY_PDS_URL"),
        'media_folder': str(script_dir / os.getenv("TWITTER_DATA_ROOT_FOLDER") / 'tweets_media'),
        'tweet_objects_file': str(script_dir / os.getenv("TWITTER_DATA_ROOT_FOLDER") / 'tweets.js'),
        'sleep_interval_seconds': float(os.getenv("SLEEP_INTERVAL_SECONDS", 600.0)) # Default to 10 minutes
    }

    if args.dry_run:
        print("="*50)
        print("===      DRY RUN MODE ACTIVATED      ===")
        print("=== No posts will be made or saved. Setting interval to 1 second. ===")
        print("="*50)
        config['sleep_interval_seconds'] = 1.0

    # if not config['handle'] or not config['password'] or not config['pds_url']:
    if not all(config[k] for k in ['handle', 'password', 'pds_url']):
        raise ValueError("Missing required environment variables for Bluesky configuration.")

    # -------------------------------------------  
    # --- Instance Initialization ---------------
    tweet_parser = TweetArchiveParser(config['tweet_objects_file'])
    bluesky_poster = BlueskyPoster(pds_url=config['pds_url'], handle=config['handle'], password=config['password'])

    # -------------------------------------------  
    # --- Tweet Loading and Preparation ---------
    
    # Load a collection of Tweets loaded from a downloaded Twitter account archives, populate tweets[].
    print("Loading and parsing Twitter archive...")
    tweets_raw = tweet_parser.load_twitter_archive()
    # Previously:
    # tweets = tweet_parser.load_twitter_archive(config['tweet_objects_file'])

    # Let's sort it!
    tweets_sorted = sorted(tweets_raw, key=lambda tweet: datetime.strptime(tweet["created_at"], "%a %b %d %H:%M:%S +0000 %Y"))
    # Previously:
    # tweets.sort(key=lambda tweet: datetime.strptime(tweet["created_at"], "%a %b %d %H:%M:%S +0000 %Y")) 
    
    tweets_filtered = tweet_parser.filter_out_replies(tweets_sorted)
    tweets = tweet_parser.extract_metadata(tweets_filtered)

    # Generate a set of statistics and time-series data from the Tweet collection. 
    print(f"Loaded {len(tweets)} tweets to potentially process.")
    print(f"{tweet_parser.get_stats(tweets)}")

    # -------------------------------------------  
    # --- Mode Selection and Filtering ----------

    last_processed_timestamp = None
    save_on_post = True

    if args.reprocess_videos:
        print("--- Mode: Reprocessing all videos ---")
        tweets = [t for t in tweets if t.get('media_type') in ['video', 'gif']]
        save_on_post = False  # Do not update the timestamp file in this mode
        print(f"Found {len(tweets)} video tweets to process.")
    elif args.start_from:
        try:
            start_dt_naive = datetime.strptime(args.start_from, '%Y-%m-%d %H:%M:%S')
            if args.timezone == 'local':
                # Interpret the naive datetime in the system's local timezone and make it aware
                last_processed_timestamp = start_dt_naive.astimezone()
                print(f"--- Mode: Starting from local time {last_processed_timestamp.strftime('%Y-%m-%d %H:%M:%S %Z')} ---")
                print(f"--- Converted to UTC for comparison: {last_processed_timestamp.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')} ---")
            else: # Default is 'utc'
                # Make the naive datetime aware by setting its timezone to UTC
                last_processed_timestamp = start_dt_naive.replace(tzinfo=timezone.utc)
                print(f"--- Mode: Starting from UTC time {args.start_from} ---")
        except ValueError:
            print("Error: Invalid timestamp format for --start-from. Please use 'YYYY-MM-DD HH:M:%S'.")
            return
    else:
        print("--- Mode: Resuming from last saved post ---")
        last_processed_timestamp = load_last_processed_timestamp()

    if last_processed_timestamp:
        print(f"Filtering tweets after: {last_processed_timestamp}")
        tweets = [t for t in tweets if datetime.strptime(t['timestamp'], '%Y-%m-%d %H:%M:%S') > last_processed_timestamp]
        print(f"Found {len(tweets)} new tweets to process.")
    else:
        # This branch will now also be hit if --start-from isn't used and no save file exists
        print("No saved or specified start time. Processing from the beginning of the archive.")

    # --- Main Processing Loop ---
    if not tweets:
        print("No new tweets to post.")
        return
        
    # --- Main Processing Loop (Restored to staggered parallel execution) ---
    print(f"\nStarting post sequence. Staggering post starts by {config['sleep_interval_seconds']} seconds.")
    
    tasks = []
    for tweet in tweets:
        tweet_url = f"https://twitter.com/i/status/{tweet['tweet_id']}"
        print(f"Processing Tweet ID: {tweet['tweet_id']} from {tweet['timestamp']} UTC (Original: {tweet_url})")
        
        
        if args.dry_run:
            # In dry-run mode, we print the simulation and do nothing else.
            print(f"-> DRY RUN: Would post Tweet with text: \"{tweet['text'][:75]}...\"")
            if tweet.get('media_type'):
                print(f"-> DRY RUN: with {tweet['media_type']}: {tweet['media_filenames']}")
        else:
            # In a real run, we create the background task for posting.
            task = asyncio.create_task(
                create_post(config, tweet, bluesky_poster, save_timestamp_on_success=save_on_post)
            )
            tasks.append(task)
        
        # Wait for the specified interval before starting the next post task
        # This creates the stagger effect.
        await asyncio.sleep(config['sleep_interval_seconds'])

    # After starting all tasks with delays, wait here until they are all completed.
    print("\nAll posts have been queued. Waiting for any remaining uploads to complete...")
    await asyncio.gather(*tasks)

    print("\nScript finished.")


if __name__ == "__main__":
    asyncio.run(main())