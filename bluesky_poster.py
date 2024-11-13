from bluesky_facets import parse_facets
from tweet_archive_parser import TweetArchiveParser
import requests
import os
import sys
import re
import json
from typing import Dict, List
from pathlib import Path
import asyncio
import aiohttp
from datetime import datetime, timezone
from dotenv import load_dotenv

class BlueskyPoster:
    def __init__(self, pds_url, handle, password):
        self.pds_url = pds_url
        self.handle = handle
        self.password = password
        self.access_jwt = None
        self.did = None
        self.session_lock = asyncio.Lock()
        self.session = None
        self.session_expiry = None
    
    async def bsky_login_session(self, pds_url: str, handle: str, password: str) -> Dict:  # Make bsky_login_session async

        headers = {'Content-Type': 'application/json'}

        try:
            async with aiohttp.ClientSession() as session:  # Use aiohttp for async requests
                resp = await session.post(  # Use await for the async post request
                    pds_url + "/xrpc/com.atproto.server.createSession",
                    json={"identifier": handle, "password": password},
                    headers=headers
                )
                resp.raise_for_status()  # This will raise an exception for 4xx and 5xx status codes
                return await resp.json()  # Use await for async json response
        except aiohttp.ClientError as e:  # Catch aiohttp exceptions
            print(f"An error occurred during the request: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None

    async def get_or_create_session(self):  # No config argument needed here
        async with self.session_lock:
            if self.session is None or (self.session_expiry and datetime.now(timezone.utc) > self.session_expiry):
                self.session = await self.bsky_login_session(self.pds_url, self.handle, self.password)  # Use instance attributes
                if self.session is None:
                    print("Authentication failed")
                    return None

                # ... (get session_expiry from session response)

            return self.session

    async def upload_image(self, config, image_path):
        """
        Uploads an image to a Bluesky server using com.atproto.repo.uploadBlob.
        """

        image_path = f"{config['images_folder']}/{image_path}"

        if not os.path.exists(image_path):
            print(f"File does not exist: {image_path}")
            return None

        try:
            with open(image_path, "rb") as image_file:
                img_bytes = image_file.read()

            if len(img_bytes) > 1000000:
                raise Exception(
                    f"image file size too large. 1000000 bytes maximum, got: {len(img_bytes)}"
                )

            async with aiohttp.ClientSession() as session:
                resp = await session.post(
                    config['pds_url'] + "/xrpc/com.atproto.repo.uploadBlob",
                    headers={
                        "Content-Type": "image/png",
                        "Authorization": "Bearer " + config['accessJwt']
                    },
                    data=img_bytes,
                )
                resp.raise_for_status()
                blob = (await resp.json())["blob"] 

            return blob

        except aiohttp.ClientError as e:  # Catch aiohttp exceptions
            print(f"Error uploading image: {e}")
            return None

    async def upload_file(self, pds_url: str, access_token: str, filename: str, file_data: bytes) -> Dict:
        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"{pds_url}/xrpc/com.atproto.repo.uploadBlob"
        
        async with aiohttp.ClientSession() as session:
            async with aiohttp.MultipartWriter('form-data') as mpwriter:
                part = mpwriter.append(file_data, {'Content-Type': 'image/jpeg'})
                part.set_content_disposition('form-data', name='file', filename=filename)

            resp = await session.post(url, headers=headers, data=mpwriter)
            resp.raise_for_status()
            return await resp.json()
  
    def manage_bluesky_message_length(self, tweet):
        """
        Manages the length of a Bluesky message to keep it under 300 characters.

        Args:
            tweet: A dictionary representing a tweet, containing a 'text' key.

        Returns:
            A string with the processed tweet and addendum, ready for Bluesky.
        """

        # Remove the URL from the tweet
        tweet['text'] = re.sub(r"https://t\.co/\S+", "", tweet['text']).strip()

        # Create the long and short versions of the addendum
        long_addendum = f"\n\nTweeted at {tweet['timestamp']} UTC"
        short_addendum = f"\nTweeted {tweet['timestamp'].split()[0]}"

        # Check if the long addendum fits within the character limit
        if len(tweet['text'] + long_addendum) <= 300:
            return tweet['text'] + long_addendum
        else:
            return tweet['text'] + short_addendum
    
    async def create_post(self, config, tweet):
        bsky_session = await self.get_or_create_session()
        if bsky_session is None:
            return

        config['accessJwt'] = bsky_session["accessJwt"]
        config['did'] = bsky_session["did"]

        tweet['text' ]= self.manage_bluesky_message_length(tweet)

        # trailing "Z" is preferred over "+00:00"
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # Use the parse_facets function to generate facets
        #facets = parse_facets(tweet['text'] + addendum, self.pds_url)
        facets = parse_facets(tweet['text'], self.pds_url)

        # these are the required fields which every post must include
        post = {
            # TODO: make general with pds_url
            "$type": "app.bsky.feed.post",
            #"text": tweet['text'] + addendum,
            "text": tweet['text'],
            "createdAt": now,
            "facets": facets,
        }

        if tweet['image_paths']:
            image_embed = {  # Initialize the embed dictionary outside the loop
                # TODO: make general with pds_url
                "$type": "app.bsky.embed.images",
                "images": []
            }
            for image_path in tweet['image_paths']:
                blob = self.upload_image(config, image_path)
                if blob:
                    image_setting = {
                        "alt": '',
                        "image": blob
                    }
                    image_embed["images"].append(image_setting)  # Append each image to the "images" list

            post["embed"] = image_embed  # Assign the embed after processing all images

        async with aiohttp.ClientSession() as session:  # Create aiohttp ClientSession here
            resp = await session.post(  # Use await for async post
                config['pds_url'] + "/xrpc/com.atproto.repo.createRecord",
                headers={"Authorization": "Bearer " + bsky_session["accessJwt"]},
                json={
                    "repo":bsky_session["did"],
                    "collection": "app.bsky.feed.post",
                    "record": post,
                },
            )
            print("createRecord response:", file=sys.stderr)
            print(json.dumps(await resp.json(), indent=2))  # Use await for async json response
            resp.raise_for_status()
        
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

    config = {}
    #TODO: figure out .env and overrides.
    config['handle'] = BLUESKY_HANDLE
    config['password'] = BLUESKY_PASSWORD
    config['pds_url'] = BLUESKY_PDS_URL
    config['images_folder'] = str(script_dir / TWITTER_DATA_ROOT_FOLDER / 'tweets_media')
    config['tweet_objects_file'] = str(script_dir / TWITTER_DATA_ROOT_FOLDER / 'tweets.js')
        
    if not (config['handle'] and config['password']):
        print("both handle and password are required", file=sys.stderr)
        sys.exit(-1)
    """ if args.image and len(args.image) > 4:
        print("at most 4 images per post", file=sys.stderr)
        sys.exit(-1) """
        
    # Create an instance of BlueskyPoster
    bluesky_poster = BlueskyPoster(config['pds_url'], config['handle'], config['password'])  # Assuming the constructor takes these arguments
        
    # Create TweetParser instance. 
    twitter_parser = TweetArchiveParser(config['tweet_objects_file'])
    
    tweets_raw = []
    tweets_raw = twitter_parser.load_twitter_archive()

    tweets = []
    tweets = twitter_parser.extract_metadata(tweets_raw)

    # TODO: need a Tweet to post. Pick one to test with. 
    #tweet = tweets[188]
    # tweet_id = '1662845607046795264' OK
    # tweet_id = '1217911688827211777' OK
    tweet_id = '928009601601167366'

    async with aiohttp.ClientSession() as session:
        tasks = []
        for item in tweets:
            # ... (prepare config and tweet_data)
            if item['tweet_id'] == tweet_id:
                tweet = item
                break

        task = asyncio.create_task(
            #poster.create_post_async(config, tweet, httpsession)  # Pass the session
            bluesky_poster.create_post(config, tweet)  # Pass the session
        )
        tasks.append(task)
        await asyncio.sleep(3.6)  # Adjust delay as needed

        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())