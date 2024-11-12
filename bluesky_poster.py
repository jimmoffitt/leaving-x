from bluesky_facets import parse_facets
from tweet_archive_parser import TweetArchiveParser
import requests
import os
import sys
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

    def bsky_login_sessionX(self, pds_url: str, handle: str, password: str) -> Dict:

        headers = {'Content-Type': 'application/json'}

        try:
            resp = requests.post(
                pds_url + "/xrpc/com.atproto.server.createSession",
                json={"identifier": handle, "password": password},
                headers = headers
            )
            print(resp.json())  
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error occurred: {e}")
            if resp.status_code == 401:
                print("Authentication failed. Please check your handle and password.")
            return None
        except requests.exceptions.RequestException as e:
            print(f"An error occurred during the request: {e}")
            return None 
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None

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

    def upload_image(self, config, image_path):
        """
        Uploads an image to a Bluesky server using com.atproto.repo.uploadBlob.

        Args:
            args: An object containing the following attributes:
                image: The path to the image file.
                pds_url: The base URL of the server.
                accessJwt: The access token for authentication.

        Returns:
            A dictionary containing the 'cid' and 'mimeType' of the uploaded image 
            if successful, or None if there is an error.
        """

        # Build image_path
        image_path = f"{config['images_folder']}/{image_path}"


        if not os.path.exists(image_path):
            print(f"File does not exist: {image_path}")
            return None

        try:
            with open(image_path, "rb") as image_file:
                img_bytes = image_file.read()

            # this size limit is specified in the app.bsky.embed.images lexicon
            if len(img_bytes) > 1000000:
                raise Exception(
                    f"image file size too large. 1000000 bytes maximum, got: {len(img_bytes)}"
                )
            
            #TODO: strip EXIF metadata here, if needed

            resp = requests.post(
                config['pds_url'] + "/xrpc/com.atproto.repo.uploadBlob",
                headers={
                    "Content-Type": "image/png",
                    "Authorization": "Bearer " + config['accessJwt']
                },
                data=img_bytes,
            )

            resp.raise_for_status()
            blob = resp.json()["blob"]

            return blob

        except requests.exceptions.RequestException as e:
            print(f"Error uploading image: {e}")
            return None

    def upload_file(self, pds_url: str, access_token: str, filename: str, file_data: bytes) -> Dict:
        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"{pds_url}/xrpc/com.atproto.repo.uploadBlob"
        files = {"file": (filename, file_data, "image/jpeg")}
        
        response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()
        return response.json()

    async def create_post(self, config, tweet):
        bsky_session = await self.get_or_create_session()
        if bsky_session is None:
            return

        config['accessJwt'] = bsky_session["accessJwt"]
        config['did'] = bsky_session["did"]

        # trailing "Z" is preferred over "+00:00"
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        addendum = f"\n\nOriginally Tweeted at {tweet['timestamp']} UTC"

        # Use the parse_facets function to generate facets
        facets = parse_facets(tweet['text'] + addendum, self.pds_url)

        # these are the required fields which every post must include
        post = {
            # TODO: make general with pds_url
            "$type": "app.bsky.feed.post",
            "text": tweet['text'] + addendum,
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

    async def create_postX(self, config, tweet):
        session = await self.get_or_create_session()
        if session is None:
            return

        config['accessJwt'] = session["accessJwt"]
        config['did'] = session["did"]

        # trailing "Z" is preferred over "+00:00"
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        addendum = f"\n\nOriginally Tweeted at {tweet['timestamp']} UTC"

        # Use the parse_facets function to generate facets
        facets = parse_facets(tweet['text'] + addendum, self.pds_url)

        # these are the required fields which every post must include
        post = {
            # TODO: make general with pds_url
            "$type": "app.bsky.feed.post",
            "text": tweet['text'] + addendum,
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


        resp = requests.post(
            config['pds_url'] + "/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization": "Bearer " + session["accessJwt"]},
            json={
                "repo": session["did"],
                "collection": "app.bsky.feed.post",
                "record": post,
            },
        )
        print("createRecord response:", file=sys.stderr)
        print(json.dumps(resp.json(), indent=2))
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

    # TODO: need a Tweet to post. 
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