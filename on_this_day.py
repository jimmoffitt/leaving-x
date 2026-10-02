from tweet_archive_parser import TweetArchiveParser
from bluesky_poster import BlueskyPoster
from posted_records import load_posted_records, save_posted_record
import asyncio
import argparse
import calendar
import contextlib
import io
import os
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

"""
Reposts "On this day" Tweets: Tweets from this month/day in earlier years are reposted at their
original time of day (UTC), with an "On this day in YYYY:" line. Once the new post is up, the
previous copy (the backdated archive post, or last year's "On this day" post) is deleted.

Designed to be run every few minutes (e.g. with launchd or cron). Each run posts whatever is due
and not yet posted this year, so it is safe to run repeatedly.
"""

def is_on_this_day(tweet_time, now):
    """True if the Tweet was posted on today's month/day in an earlier year. Feb 29 Tweets show up on Feb 28 in non-leap years."""
    if tweet_time.year >= now.year:
        return False
    if (tweet_time.month, tweet_time.day) == (now.month, now.day):
        return True
    return (tweet_time.month, tweet_time.day) == (2, 29) and (now.month, now.day) == (2, 28) and not calendar.isleap(now.year)

async def main():
    parser = argparse.ArgumentParser(description='Repost "On this day" Tweets to Bluesky.')
    parser.add_argument('--date', type=str,
                        help='Pretend today is this date (format: "YYYY-MM-DD"), with every Tweet from that day due. For testing with --dry-run.')
    parser.add_argument('--dry-run', action='store_true',
                        help='List what would be posted and deleted, without changing anything.')
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    load_dotenv(dotenv_path=script_dir / '.env.local')

    config = {
        'handle': os.getenv("BLUESKY_HANDLE"),
        'password': os.getenv("BLUESKY_PASSWORD"),
        'pds_url': os.getenv("BLUESKY_PDS_URL"),
        'media_folder': str(script_dir / os.getenv("TWITTER_DATA_ROOT_FOLDER") / 'tweets_media'),
        'tweet_objects_file': str(script_dir / os.getenv("TWITTER_DATA_ROOT_FOLDER") / 'tweets.js'),
        'backdate': False,  # "On this day" posts use the current time.
    }

    if not all(config[k] for k in ['handle', 'password', 'pds_url']):
        raise ValueError("Missing required environment variables for Bluesky configuration.")

    now = datetime.now(timezone.utc)
    if args.date:
        # End of the given day, so every Tweet from that day is due.
        now = datetime.strptime(args.date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)

    tweet_parser = TweetArchiveParser(config['tweet_objects_file'])
    with contextlib.redirect_stdout(io.StringIO()):  # The parser prints a line per Tweet; keep the logs readable.
        tweets = tweet_parser.extract_metadata(tweet_parser.filter_out_replies(tweet_parser.load_twitter_archive()))
    records = load_posted_records()

    due = []
    for tweet in tweets:
        tweet_time = datetime.strptime(tweet['timestamp'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        if not is_on_this_day(tweet_time, now):
            continue
        # Post at (or after) the original time of day.
        if tweet_time.time() > now.time():
            continue
        record = records.get(tweet['tweet_id'], {})
        if record.get('kind') == 'on_this_day' and record.get('year') == now.year:
            continue
        due.append(tweet)

    due.sort(key=lambda t: t['timestamp'][11:])
    print(f"{now.strftime('%Y-%m-%d %H:%M')} UTC: {len(due)} 'On this day' Tweets due.")

    bluesky_poster = BlueskyPoster(pds_url=config['pds_url'], handle=config['handle'], password=config['password'])

    # Retry deleting any old copies that failed to delete on an earlier run.
    for tweet_id, record in records.items():
        for stale_uri in record.get('stale_uris', []):
            if args.dry_run:
                print(f"-> DRY RUN: Would retry deleting {stale_uri}")
            elif await bluesky_poster.delete_post(stale_uri):
                record['stale_uris'].remove(stale_uri)
                save_posted_record(tweet_id, record)

    for tweet in due:
        old_record = records.get(tweet['tweet_id'], {})
        year = tweet['timestamp'][:4]
        tweet['post_prefix'] = f"On this day in {year}:\n\n"

        if args.dry_run:
            print(f"-> DRY RUN: Would post Tweet {tweet['tweet_id']} from {tweet['timestamp']}: \"{tweet['text'][:60]}...\"")
            if old_record.get('uri'):
                print(f"   and then delete the {old_record.get('kind')} copy {old_record['uri']}")
            continue

        new_post = await bluesky_poster.create_post(config, tweet)
        if not new_post:
            print(f"❌ FAILED: 'On this day' post for Tweet {tweet['tweet_id']}. Will retry on the next run.")
            continue
        print(f"✅ Posted 'On this day' Tweet {tweet['tweet_id']}: {new_post.get('uri')}")

        # Only delete the old copy once the new one is up.
        stale_uris = old_record.get('stale_uris', [])
        if old_record.get('uri') and not await bluesky_poster.delete_post(old_record['uri']):
            stale_uris.append(old_record['uri'])

        save_posted_record(tweet['tweet_id'], {
            "uri": new_post.get('uri'),
            "cid": new_post.get('cid'),
            "kind": "on_this_day",
            "year": now.year,
            "stale_uris": stale_uris,
        })

if __name__ == "__main__":
    asyncio.run(main())
