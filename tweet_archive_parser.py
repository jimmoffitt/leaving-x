import json
from datetime import datetime, timedelta
from dateutil import parser
from pathlib import Path
import os
from dotenv import load_dotenv

class TweetArchiveParser:
    def __init__(self, archive_path):
        self.archive_path = archive_path
        #self.tweets = []
     
    def load_twitter_archive(self, tweet_objects_path = None):
        
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
        parsed_tweets = []

        
        # Already sorted.     
        #tweets.sort(key=lambda tweet: datetime.strptime(tweet["created_at"], "%a %b %d %H:%M:%S +0000 %Y")) 
        
        for tweet in tweets:
            timestamp = self.reformat_timestamp(tweet.get('created_at'))
            tweet_id = tweet.get('id', None)

            # Establishing `message` as the Tweet text contents. 
            message = tweet.get('full_text', '')
            truncated = tweet.get('truncated', False)
            
            hashtags = tweet.get('entities', {}).get('hashtags', [])
            mentions = tweet.get('entities', {}).get('user_mentions', [])
            urls = tweet.get('entities', {}).get('urls', [])

            image_paths = []

            # Assemble file names for any images. 
            # TODO: IIRC, this means more than one image. 
            # Note: there is always an `extended_entities` object if there is at least one image. 
            if 'extended_entities' in tweet:
                # This tweet has images or other media attached.
                media_obj = tweet.get('extended_entities', {}).get('media', [])
                for item in media_obj:
                    image_paths.append(f"{tweet_id}-{item['media_url'].split('/')[-1]}")
            else:
                # This tweet has no media attached.
                pass  # No need for extra logic here
        
            parsed_tweets.append({
                #"timestamp": self.reformat_timestamp(tweet.get('created_at')),
                "timestamp": timestamp,
                "tweet_id": tweet_id,
                #TODO: document the text/message boundaries.
                "text": message,
                "truncated": truncated,
                "image_paths": image_paths,
                "hashtags": [h.get('text') for h in hashtags],
                "mentions": [m.get('screen_name') for m in mentions],
                "urls": [u.get('expanded_url') for u in urls],
            })

        return parsed_tweets

    def get_stats(self, tweets):

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

    # TODO: Create instance of TweetParser and load the archive....

    # Get the directory of the current script
    script_dir = Path(__file__).parent 
    # Construct the path to .env.local within the script's directory
    env_path = script_dir / '.env.local'
    load_dotenv(dotenv_path=env_path)

    IMAGES_FOLDER = os.getenv("IMAGES_FOLDER")
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