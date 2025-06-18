from bluesky_facets import parse_facets
from bluesky_video import BlueskyVideo
from tweet_archive_parser import TweetArchiveParser
import os
import sys
import re
import json
from typing import Dict, List
from pathlib import Path
import mimetypes
import asyncio
import aiohttp
from datetime import datetime, timezone
from datetime import timedelta
from dotenv import load_dotenv

class BlueskyPoster:
    """
        A class to handle posting and managing sessions with a Bluesky server.
    
        This class provides methods to authenticate, upload images, manage message lengths, and create posts on a Bluesky server.
    
        Attributes:
            pds_url (str): The URL of the Bluesky server.
            handle (str): The user handle for authentication.
            password (str): The password for authentication.
            access_jwt (str): The access token for the session.
            did (str): The decentralized identifier for the session.
            session_lock (asyncio.Lock): A lock to manage session creation.
            session (dict): The current session information.
            session_expiry (datetime): The expiry time of the current session.
        """
    def __init__(self, pds_url, handle, password):
        """
        Initializes the instance with server URL, user handle, and password, and sets up session management attributes.
        """
        self.pds_url = pds_url
        self.handle = handle
        self.password = password
        self.access_jwt = None
        self.did = None
        self.session_lock = asyncio.Lock()
        self.session = None
        self.session_expiry = None

        # Initialize the new video uploader class
        self.video_uploader = BlueskyVideo(pds_url, handle, password)
    
    async def bsky_login_session(self, pds_url: str, handle: str, password: str) -> Dict:
        """
            Initiates an asynchronous login session with a Bluesky server.
        
            Args:
                pds_url: The URL of the Bluesky server.
                handle: The user handle for login.
                password: The password for login.
        
            Returns:
                A dictionary containing the session data if successful, or None if an error occurs.
            """  # Make bsky_login_session async

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

    async def get_or_create_session(self):
        """
        Manages the session lifecycle, creating a new session if none exists or if the current session has expired.
        """  # No config argument needed here
        async with self.session_lock:
            if self.session is None or (self.session_expiry and datetime.now(timezone.utc) > self.session_expiry):
                self.session = await self.bsky_login_session(self.pds_url, self.handle, self.password)  # Use instance attributes
                if self.session is None:
                    print("Authentication failed")
                    return None

                # Assuming the session response includes `accessJwt` and a token expiry time in seconds (if available)
                self.access_jwt = self.session.get("accessJwt")
                self.did = self.session.get("did")
                
                # Set session expiry if token has an expiration field (adjust based on actual API response)
                expiry_seconds = self.session.get("expires_in", 3600)  # Default to 1 hour if unspecified
                self.session_expiry = datetime.now(timezone.utc) + timedelta(seconds=expiry_seconds)


            return self.session

    async def upload_video(self, config, media_filename):
        """
        Delegates video upload and MANUALLY constructs a clean blob dictionary
        to ensure API compatibility.
        """
        media_path = f"{config['media_folder']}/{media_filename}"
        
        # This returns the atproto library's Pydantic model instance
        video_blob_model = await self.video_uploader.upload(media_path)

        if video_blob_model:
            # Manually build the dictionary to match the Bluesky API lexicon ---
            # Do NOT use model_dump(), as it includes extra internal fields.
            clean_blob_dict = {
                '$type': 'blob',
                'ref': {
                    '$link': str(video_blob_model.ref.link) # Use the CID string from the ref
                },
                'mimeType': video_blob_model.mime_type, # Use camelCase for JSON
                'size': video_blob_model.size
            }
            return clean_blob_dict
            
        return None

    async def upload_image(self, config, media_filename):
        """
        Uploads an image to a Bluesky server using com.atproto.repo.uploadBlob.
        
        Args:
        config: Configuration dictionary containing server details.
        media_path: Path to the image file to be uploaded.
        
        Returns:
        The blob identifier if the upload is successful, or None if an error occurs.
        """

        media_path = f"{config['media_folder']}/{media_filename}"

        if not os.path.exists(media_path):
            print(f"File does not exist: {media_path}")
            return None
        
        mime_type, _ = mimetypes.guess_type(media_path)
        if not mime_type or not mime_type.startswith('image/'):
            print(f"Could not determine image mime type for {media_filename}. Defaulting to image/jpeg.")
            mime_type = 'image/jpeg' # Fallback for safety

        try:
            with open(media_path, "rb") as media_file:
                media_bytes = media_file.read()

            if len(media_bytes) > 1000000:
                raise Exception(
                    f"Image file size too large. 1000000 bytes maximum, got: {len(media_bytes)}"
                )

            async with aiohttp.ClientSession() as session:
                resp = await session.post(
                    # TODO: what is the recipe for uploading videos to Bluesky?
                    config['pds_url'] + "/xrpc/com.atproto.repo.uploadBlob",
                    headers={
                        "Content-Type": mime_type,
                        "Authorization": "Bearer " + self.access_jwt
                    },
                    data=media_bytes,
                )
                resp.raise_for_status()
                blob = (await resp.json())["blob"] 

            return blob

        except aiohttp.ClientError as e:  # Catch aiohttp exceptions
            print(f"Error uploading image: {e}")
            return None

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
        """
        Creates a new post on the Bluesky platform using the provided tweet data and configuration.
        
            Args:
            config: Configuration dictionary containing necessary session and API details.
            tweet: A dictionary representing the tweet data to be posted.
        
            Returns:
            None
        """
        bsky_session = await self.get_or_create_session()
        if bsky_session is None:
            return

        #config['accessJwt'] = bsky_session["accessJwt"]
        #config['did'] = bsky_session["did"]

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
            "text": tweet['text'],
            "createdAt": now,
            "facets": facets,
        }

        # --- REVISED EMBED LOGIC ---
        embed = None # Initialize embed variable

        # Check for different embed types. Using if/elif is safer.
        if tweet.get('media_filenames') and tweet['media_type'] in ['video', 'gif']:
            print('Attempting to embed a video/gif.')
            blob = await self.upload_video(config, tweet['media_filenames'][0])
            if blob:
                embed = {
                    "$type": "app.bsky.embed.video",
                    "video": blob,
                }

        elif tweet.get('media_filenames') and tweet['media_type'] in ['photo']:
            image_embed = {
                "$type": "app.bsky.embed.images",
                "images": []
            }
            for media_filename in tweet['media_filenames']:
                blob = await self.upload_image(config, media_filename)
                if blob:
                    image_setting = {"alt": '', "image": blob}
                    image_embed["images"].append(image_setting)
            
            if image_embed["images"]:
                embed = image_embed

        # TODO: test
        # --- NEWLY ADDED QUOTE TWEET LOGIC ---
        elif tweet.get('quoted_post_uri') and tweet.get('quoted_post_cid'):
            print("Embedding a quote tweet.")
            embed = {
                "$type": "app.bsky.embed.record",
                "record": {
                    "cid": tweet['quoted_post_cid'],
                    "uri": tweet['quoted_post_uri']
                }
            }

        # If any embed was created, add it to the post
        if embed:
            post["embed"] = embed

        print("Final post object being sent:")
        print(json.dumps(post, indent=2), file=sys.stderr)

        try:
            async with aiohttp.ClientSession() as session:
                resp = await session.post(
                    config['pds_url'] + "/xrpc/com.atproto.repo.createRecord",
                    headers={"Authorization": "Bearer " + self.access_jwt},
                    json={
                        "repo": self.did,
                        "collection": "app.bsky.feed.post",
                        "record": post,
                    },
                )
                print("createRecord response:", file=sys.stderr)
                resp.raise_for_status() # Check for HTTP errors
                
                response_json = await resp.json()
                print(json.dumps(response_json, indent=2))
                
                # --- CRITICAL CHANGE: RETURN THE RESPONSE ---
                return response_json
        except aiohttp.ClientError as e:
            print(f"Error creating record: {e}")
            return None

        

async def main():
    """
    Asynchronously loads environment variables, initializes configurations, and posts a tweet using BlueskyPoster.
    """

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
    config['media_folder'] = str(script_dir / TWITTER_DATA_ROOT_FOLDER / 'tweets_media')
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
    # tweet_id = '928009601601167366'
    tweet_id = '985872580350390279' #Video post
    # tweet_id = '981638312241725440' #quotes post 981630390937960448
    # tweet_id = '902302003812065281' #self-quotes post 902301386880286721

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