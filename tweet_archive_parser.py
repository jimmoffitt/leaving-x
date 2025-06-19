import json
from datetime import datetime, timedelta
from dateutil import parser
from pathlib import Path
import os
from dotenv import load_dotenv

class TweetArchiveParser:
    """
    A class to parse and analyze a Twitter archive.
    
    Attributes:
    archive_path (str): The path to the Twitter archive file.
    """
    def __init__(self, archive_path):
        """
        Initializes the instance with the specified archive path.
        """
        self.archive_path = archive_path
        #self.tweets = []
     
    def load_twitter_archive(self, tweet_objects_path = None):
        """
        Loads and parses a Twitter archive from a specified file path, extracting tweet data.
        """
        
        tweets_raw = []
        tweets = []
        
        try:

            if tweet_objects_path == None:
                tweet_objects_path = self.archive_path

            # Convert Path object to string if necessary
            if isinstance(tweet_objects_path, Path):
                tweet_objects_path = str(tweet_objects_path) 

            with open(tweet_objects_path, 'r') as file:
                # Read the entire file content
                file_content = file.read()  
                
                # Find the start of the JSON array
                start_index = file_content.find('[')  
                
                # Extract the JSON array string
                json_string = file_content[start_index:]  
                
                # Parse the JSON string
                tweets_raw = json.loads(json_string)

            #Strip out top `tweet` attributes.
            for item in tweets_raw:
                tweets.append(item['tweet'])
                
            return tweets
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error decoding JSON from {tweet_objects_path}: {e}")
            return []  # Or handle the error as needed

    def reformat_timestamp(self, timestamp_str):
        """
        Reformats a timestamp string from the format 'Wed Oct 16 22:18:35 +0000 2024'
        to 'YYYY-MM-DD HH:mm:ss' in UTC.

        Args:
            timestamp_str: The timestamp string to reformat.

        Returns:
            The reformatted timestamp string.
        """
        dt_object = datetime.strptime(timestamp_str, '%a %b %d %H:%M:%S %z %Y')
        return dt_object.strftime('%Y-%m-%d %H:%M:%S')

    def filter_out_quotes(self, tweets):

        not_quote_tweets = []

        for tweet in tweets:
            pass
            # Check if tweet is a quote (signature?)
            is_quote = any(key.startswith("????") for key in tweet)
        
            if not is_quote:
                not_quote_tweets.append(tweet)
                print(f"Adding Tweet: {tweet['full_text']} ") 
            else:
                print(f"Tweet skipped as Quote: {tweet['full_text']} ")    

        return not_quote_tweets

    def filter_out_replies(self, tweets):
        """
        Filters out reply tweets from a list of tweet objects.

        Args:
        tweets: A list of tweet objects.

        Returns:
        A new list containing only the tweets that are not replies.
        """
        not_reply_tweets = []

        for tweet in tweets:

            # Check if tweet is a reply (has 'in_reply_to_' fields) or starts with '@'
            is_reply = any(key.startswith("in_reply_to_") for key in tweet)

            if tweet.get('full_text', '').startswith('@'):
                pass

            starts_with_at = tweet.get('full_text', '').startswith("@")
        
            if not is_reply and not starts_with_at:
                if '@' in tweet["full_text"][0:10]:
                    pass
                not_reply_tweets.append(tweet)
                print(f"Adding Tweet: {tweet['full_text']} ") 
            else:
                print(f"Tweet skipped as Reply: {tweet['full_text']} ")    
                
        return not_reply_tweets
    
    def extract_metadata(self, tweets):
        """
        Extracts and formats metadata from a list of tweets, including timestamps, IDs, text, and media information.

        Args:
            tweets: A list of tweet objects.

        For media, there can be up to four images or one video.     

        """
        parsed_tweets = []
                
        # Already sorted.     
        #tweets.sort(key=lambda tweet: datetime.strptime(tweet["created_at"], "%a %b %d %H:%M:%S +0000 %Y")) 
        
        for tweet in tweets:
            timestamp = self.reformat_timestamp(tweet.get('created_at'))
            tweet_id = tweet.get('id', None)
            media_type = ''

            # Establishing `message` as the Tweet text contents. 
            message = tweet.get('full_text', '')
            truncated = tweet.get('truncated', False)
            
            hashtags = tweet.get('entities', {}).get('hashtags', [])
            mentions = tweet.get('entities', {}).get('user_mentions', [])
            urls = tweet.get('entities', {}).get('urls', [])

            # Handle media details.
            media_filenames = [] # There may be multiple images (but never more than one video). 

            # Assemble file names for images and videos. 
            # Note: there is always an `extended_entities` object if there is at least one media object. 
            if 'extended_entities' in tweet:
                # This tweet has images or a video attached.

                # Grab the `media` object,
                media_obj = tweet.get('extended_entities', {}).get('media', [])

                # If there is a `tyoe` attribute, grab its value.
                for item in media_obj:
                    if 'type' in item:
                        media_type = item['type']

                if media_type == 'photo':
                    print('Got at least one photo, assembling their paths' )
                    media_filenames.append(f"{tweet_id}-{item['media_url'].split('/')[-1]}")

                # Handle both videos and animated GIFs, as Twitter processes them similarly.
                if media_type == 'video' or media_type == 'animated_gif':
                    print(f'Got a {media_type} for tweet {tweet_id}, finding the best quality variant')
                    
                    best_variant = None
                    highest_bitrate = -1

                    # Check for the existence of 'video_info' and 'variants'
                    if 'video_info' in item and 'variants' in item['video_info']:
                        for variant in item['video_info']['variants']:
                            # We only want mp4 files that have a bitrate specified.
                            # Other variants can be streaming manifests (m3u8).
                            if variant.get('content_type') == 'video/mp4' and 'bitrate' in variant:
                                current_bitrate = int(variant['bitrate'])
                                if current_bitrate > highest_bitrate:
                                    highest_bitrate = current_bitrate
                                    best_variant = variant
                    
                    if best_variant:
                        media_url = best_variant['url']
                        # Clean the URL to get a clean filename
                        media_tag = media_url.split('/')[-1].split('?')[0]
                        media_filenames.append(f"{tweet_id}-{media_tag}")
                    else:
                        # This message will appear if a video/gif has no valid mp4 variants
                        print(f"Warning: Could not find a suitable MP4 variant for tweet {tweet_id}")
        
            # Pack up anything that will be needed later, such as when posting to Bluesky    
            parsed_tweets.append({
                #"timestamp": self.reformat_timestamp(tweet.get('created_at')),
                "timestamp": timestamp,
                "tweet_id": tweet_id,
                #TODO: document the text/message boundaries.
                "text": message,
                "truncated": truncated,
                "media_type": media_type,
                "media_filenames": media_filenames,
                "hashtags": [h.get('text') for h in hashtags],
                "mentions": [m.get('screen_name') for m in mentions],
                "urls": [u.get('expanded_url') for u in urls],
            })

        return parsed_tweets

    def get_stats(self, tweets):
        """
        Analyzes a list of tweets to generate statistical data, including tweet counts, average tweet length, and usage of replies, hashtags, and mentions.
        
        Args:
            tweets: A list of tweet objects to analyze.
        
        Returns:
            A dictionary containing various statistics about the tweets.
        """

        # TODO: expand
        """ 
        Can be thought of as a one time generation.
        Tweet types? 
        Number of images? 
        We have time series data, let's work with it.
        Tweets per hour, day, and week. It is seasonal? 
        This works with the 'create Tweet' events, so ongoing, subsequent engagements are not known. 
        """

        #Already sorted.
        #sorted_array = sorted(tweets, key=lambda item: item["timestamp"])

        stats = {}
        
        # We have a set of global numbers, and a set of time-series data.

        stats['num_tweets'] = len(tweets)
        print(f"{stats['num_tweets']} Tweets in the archive.")

        # Assuming tweets are already sorted by "created_at"
        stats['earliest_timestamp'] = tweets[0]["timestamp"]
        stats['latest_timestamp'] = tweets[-1]["timestamp"]

        # Calculate average tweet length
        # TODO: still text?
        total_tweet_length = sum(len(tweet["text"]) for tweet in tweets)
        stats['avg_tweet_length'] = total_tweet_length / stats['num_tweets']

        reply_count = 0
        for item in tweets:
            is_reply = any(key.startswith("in_reply_to_") for key in item)
            if is_reply:
                reply_count += 1
        print(f"Number of Reply Tweets: {reply_count}")    

        hashtag_count = 0
        for item in tweets:
            if len(item['hashtags']) > 0:
                hashtag_count += len(item['hashtags'])
        print(f"Number of #Hashtags used: {hashtag_count}")    

         # Let's look at mentions:
        mention_count = 0
        for item in tweets:
            if len(item['mentions']) > 0:
                mention_count += len(item['mentions'])
        print(f"Number of @Mentions made: {mention_count}") 
        # TODO: OK, so we can count, now let's build a collection and surface top choices, etc. 
        # TODO: and it made be good to generate a time-series of entity counts. 

        # Calculate daily average tweets
        earliest_date = parser.parse(stats['earliest_timestamp']).date()
        latest_date = parser.parse(stats['latest_timestamp']).date()
        days_spanned = (latest_date - earliest_date).days + 1  # +1 to include both start and end days
        stats['daily_avg_tweets'] = stats['num_tweets'] / days_spanned
        stats['days_spanned'] = days_spanned
        print(f"Archive spans {days_spanned}({days_spanned/365} years) days. Average Tweets per day: {stats['daily_avg_tweets']}")

        return stats
    
def main():
    """
    Initializes environment, loads and processes Twitter archive, and outputs tweet metadata to a JSON file.
    """

    # TODO: Create instance of TweetParser and load the archive....

    # Get the directory of the current script
    script_dir = Path(__file__).parent 
    # Construct the path to .env.local within the script's directory
    env_path = script_dir / '.env.local'
    load_dotenv(dotenv_path=env_path)

    TWITTER_DATA_ROOT_FOLDER = os.getenv("TWITTER_DATA_ROOT_FOLDER")

    # TODO: migrate this script to leaving_twitter home. 
    tweet_objects_path = str(script_dir / TWITTER_DATA_ROOT_FOLDER / 'tweets.js')
    
    # Create TweetParser instance. 
    tweet_parser = TweetArchiveParser(tweet_objects_path)

    # Load archive file.
    tweets = tweet_parser.load_twitter_archive(tweet_objects_path)

    # Let's sort it!
    tweets.sort(key=lambda tweet: datetime.strptime(tweet["created_at"], "%a %b %d %H:%M:%S +0000 %Y")) 

    tweets = tweet_parser.filter_out_replies(tweets)
    
    # Load a Tweet
    #tweet = tweets_raw[888]['tweet']
    #tweet_id = '1217911688827211777'
    #tweet_id = '928009601601167366'
        
    # It should be generally useful to sort the Tweet array to be chronologically ordered.    
    # Sorting by `created_at` in ascending order. 
    # TODO: revisit
    #sorted_tweets = sorted(tweets, key=lambda item: item["created_at"])  # OR TIMESTAMP
    
    # Tour the Tweets and cherry-pick attributes need to post to target network. 
    # Also handle the weird parsing details. Truncated Tweets? Extended entities? 
    tweet_metadata = tweet_parser.extract_metadata(tweets)

    #Set up our final list
    tweets = []
    
    # Create a file name for the JSON output
    output_file = script_dir / TWITTER_DATA_ROOT_FOLDER / 'tweet_metadata.json'  

    # Write the tweet_metadata to a JSON file
    with open(output_file, 'w') as f:
        json.dump(tweet_metadata, f, indent=4)  # Use indent for pretty printing

    stats = tweet_parser.get_stats(tweets)
    print(f"Here is the stats object: \n {stats}")

    print('Finished')

if __name__ == '__main__':
    main()