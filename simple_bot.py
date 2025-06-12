
import tweepy
import time
import os
import requests
from datetime import datetime
import logging

# Simple version of the bot for testing with limited API calls
class SimplifiedRUGGUARDBot:
    def __init__(self):
        self.setup_api()
        self.trusted_accounts = self.load_default_trusted_accounts()

    def setup_api(self):
        consumer_key = os.getenv('TWITTER_CONSUMER_KEY')
        consumer_secret = os.getenv('TWITTER_CONSUMER_SECRET')
        access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')

        auth = tweepy.OAuth1UserHandler(
            consumer_key, consumer_secret,
            access_token, access_token_secret
        )
        self.api = tweepy.API(auth, wait_on_rate_limit=True)

    def load_default_trusted_accounts(self):
        return [
            "solana", "anatoly_yakovenko", "trent_vanepps", "aeyakovenko",
            "0xMert_", "rajgokal", "steppenwolf_dev", "StephenArnold17",
            "projectruggaurd", "devsyrem"
        ]

    def check_mentions_once(self):
        """Check mentions once (for testing)"""
        try:
            bot_username = self.api.verify_credentials().screen_name
            print(f"Bot username: @{bot_username}")

            # Get recent mentions
            mentions = self.api.mentions_timeline(count=5, tweet_mode="extended")

            for mention in mentions:
                if "riddle me this" in mention.full_text.lower():
                    print(f"Found trigger phrase in tweet from @{mention.user.screen_name}")

                    if mention.in_reply_to_status_id:
                        original_tweet = self.api.get_status(mention.in_reply_to_status_id)
                        user_to_analyze = original_tweet.user

                        print(f"Analyzing: @{user_to_analyze.screen_name}")
                        print(f"Account age: {(datetime.now() - user_to_analyze.created_at).days} days")
                        print(f"Followers: {user_to_analyze.followers_count}")
                        print(f"Following: {user_to_analyze.friends_count}")

                        # Simple trust check
                        if user_to_analyze.screen_name.lower() in [acc.lower() for acc in self.trusted_accounts]:
                            trust_level = "VERIFIED TRUSTED ✅"
                        elif user_to_analyze.verified:
                            trust_level = "VERIFIED ACCOUNT ✅"
                        elif user_to_analyze.followers_count > 1000:
                            trust_level = "ESTABLISHED ACCOUNT ⚠️"
                        else:
                            trust_level = "UNVERIFIED ACCOUNT ❌"

                        report = f"📊 @{user_to_analyze.screen_name} Analysis\n{trust_level}\nFollowers: {user_to_analyze.followers_count:,}\nAge: {(datetime.now() - user_to_analyze.created_at).days}d\n#RUGGUARD"

                        # Post reply (commented out for testing)
                        # self.api.update_status(status=report, in_reply_to_status_id=mention.id)
                        print(f"Would post: {report}")

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    bot = SimplifiedRUGGUARDBot()
    bot.check_mentions_once()
