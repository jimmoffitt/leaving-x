import asyncio
from datetime import datetime, timezone
import os
import argparse
from dotenv import load_dotenv
from atproto import AsyncClient

async def main():
    """
    Main function to connect to Bluesky, find posts within a specified
    timeframe (and optionally matching text), and delete them after confirmation.
    """
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(
        description="Delete Bluesky posts within a given UTC timeframe and optional text filter.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('--start-time', required=True, type=str,
                        help='The start of the deletion window (UTC).\nFormat: "YYYY-MM-DD HH:MM:SS"')
    parser.add_argument('--end-time', required=True, type=str,
                        help='The end of the deletion window (UTC).\nFormat: "YYYY-MM-DD HH:MM:SS"')
    parser.add_argument('--match-string', type=str,
                        help='(Optional) Only delete posts that also contain this text.')
    parser.add_argument('--dry-run', action='store_true',
                        help='List the posts that would be deleted without actually deleting them.')
    args = parser.parse_args()

    # --- Load Configuration from .env file ---
    script_dir = os.path.dirname(__file__)
    env_path = os.path.join(script_dir, '.env.local')
    load_dotenv(dotenv_path=env_path)

    config = {
        'handle': os.getenv("BLUESKY_HANDLE"),
        'password': os.getenv("BLUESKY_PASSWORD"),
        'pds_url': os.getenv("BLUESKY_PDS_URL", "https://bsky.social"),
    }

    if not all(config[k] for k in ['handle', 'password']):
        print("Error: BLUESKY_HANDLE and BLUESKY_PASSWORD must be set in your .env.local file.")
        return

    # --- Timezone-aware Datetime Parsing ---
    try:
        start_time_utc = datetime.strptime(args.start_time, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        end_time_utc = datetime.strptime(args.end_time, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
    except ValueError:
        print("Error: Invalid timestamp format. Please use 'YYYY-MM-DD HH:MM:SS'.")
        return

    if start_time_utc >= end_time_utc:
        print("Error: --start-time must be earlier than --end-time.")
        return

    print(f"Connecting to Bluesky as {config['handle']}...")
    client = AsyncClient(base_url=config['pds_url'])
    try:
        profile = await client.login(config['handle'], config['password'])
        print(f"Successfully logged in as {profile.handle} ({profile.did})")
    except Exception as e:
        print(f"Error: Login failed. {e}")
        return

    # --- Fetch and Filter Posts ---
    print(f"\nFetching posts between {start_time_utc.isoformat()} and {end_time_utc.isoformat()}...")
    
    posts_to_delete = []
    cursor = None
    post_count = 0
    
    while True:
        try:
            response = await client.com.atproto.repo.list_records({
                'repo': profile.did,
                'collection': 'app.bsky.feed.post',
                'limit': 100,
                'cursor': cursor
            })

            if not response.records:
                break 

            post_count += len(response.records)
            print(f"  Scanned {post_count} posts...", end='\r')

            for record in response.records:
                post_text = record.value.text
                post_time_str = record.value.created_at
                if not post_time_str:
                    continue
                
                post_time = datetime.fromisoformat(post_time_str.replace('Z', '+00:00'))

                print(f"  > Scanning post from: {post_time.isoformat()}")

                # Primary filter: time window
                if start_time_utc <= post_time <= end_time_utc:
                    post_text = record.value.text or ""
                    
                    # Secondary (optional) filter: text content
                    if args.match_string:
                        if args.match_string in post_text:
                            # Both filters match, add to list
                            posts_to_delete.append({
                                'uri': record.uri,
                                'rkey': record.uri.split('/')[-1],
                                'text': post_text[:75]
                            })
                    else:
                        # Only time filter was needed, add to list
                        posts_to_delete.append({
                            'uri': record.uri,
                            'rkey': record.uri.split('/')[-1],
                            'text': post_text[:75]
                        })

            cursor = response.cursor
            if not cursor:
                break 

        except Exception as e:
            print(f"\nAn error occurred while fetching posts: {e}")
            break


    # --- Confirmation and Deletion ---
    if not posts_to_delete:
        print("\nNo posts found in the specified timeframe.")
        return

    print(f"\n\nFound {len(posts_to_delete)} posts to delete:")
    for post in posts_to_delete:
        print(f"  - URI: {post['uri']}\n    Text: \"{post['text']}...\"")

    if args.dry_run:
        print("\n--- DRY RUN MODE ---")
        print("No posts were deleted.")
        return

    try:
        confirm = input("\nAre you sure you want to permanently delete these posts? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Deletion cancelled.")
            return
    except (EOFError, KeyboardInterrupt):
        print("\nDeletion cancelled.")
        return

    print("\nDeleting posts...")
    for post in posts_to_delete:
        try:
            await client.com.atproto.repo.delete_record({
                'repo': profile.did,
                'collection': 'app.bsky.feed.post',
                'rkey': post['rkey']
            })
            print(f"  ✅ DELETED: {post['uri']}")
        except Exception as e:
            print(f"  ❌ FAILED to delete {post['uri']}: {e}")

    print("\nDeletion process complete.")


if __name__ == "__main__":
    asyncio.run(main())
