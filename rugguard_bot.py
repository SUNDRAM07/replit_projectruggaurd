
import tweepy
import time
import os
import re
import json
import requests
from datetime import datetime, timedelta
import threading
import schedule
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RUGGUARDBot:
    def __init__(self):
        self.setup_twitter_api()
        self.trusted_accounts = self.load_trusted_accounts()
        self.processed_tweets = set()  # To avoid processing the same tweet twice
        self.last_check_time = datetime.now() - timedelta(hours=1)

    def setup_twitter_api(self):
        """Setup Twitter API authentication"""
        try:
            # Get credentials from environment variables
            consumer_key = os.getenv('TWITTER_CONSUMER_KEY')
            consumer_secret = os.getenv('TWITTER_CONSUMER_SECRET')
            access_token = os.getenv('TWITTER_ACCESS_TOKEN')
            access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')

            if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
                raise ValueError("Missing Twitter API credentials in environment variables")

            # Setup OAuth authentication
            auth = tweepy.OAuth1UserHandler(
                consumer_key, consumer_secret,
                access_token, access_token_secret
            )

            # Create API object
            self.api = tweepy.API(auth, wait_on_rate_limit=True)

            # Verify credentials
            self.api.verify_credentials()
            logger.info("Twitter API authentication successful")

        except Exception as e:
            logger.error(f"Failed to setup Twitter API: {e}")
            raise

    def load_trusted_accounts(self):
        """Load trusted accounts list from GitHub or local file"""
        try:
            # Try to fetch from GitHub first
            url = "https://raw.githubusercontent.com/devsyrem/turst-list/main/list"
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                trusted_list = response.text.strip().split('\n')
                trusted_list = [account.strip() for account in trusted_list if account.strip()]
                logger.info(f"Loaded {len(trusted_list)} trusted accounts from GitHub")
                return trusted_list
            else:
                logger.warning("Could not fetch trusted accounts from GitHub, using default list")

        except Exception as e:
            logger.warning(f"Error fetching trusted accounts: {e}")

        # Fallback to default trusted accounts
        default_trusted = [
            "JupiterExchange",    "RaydiumProtocol",     "orca_so",    "KaminoFinance",    "MeteoraAG",    "saros_xyz",    "DriftProtocol",    "solendprotocol",     "MarinadeFinance",
            "jito_labs",    "MadLads",    "MagicEden",    "Lifinity_io",    "SolanaMBS",    "DegenApeAcademy",    "okaybears",    "famousfoxfed",    "CetsOnCreck",    "xNFT_Backpack",
            "tensor_hq",    "wormholecrypto",    "helium",    "PythNetwork",    "solana",    "solanalabs",    "phantom",    "solflare_wallet",    "solanaexplorer",    "solanabeach_io",
            "solanafm",     "solanium_io",    "staratlas",    "grapeprotocol",    "mangomarkets",    "bonfida",    "medianetwork_",    "Saber_HQ",    "StepFinance_",    "tulipprotocol",
            "SunnyAggregator","aeyakovenko",  "rajgokal",  "VinnyLingham", "TonyGuoga", "Austin_Federa",     "Wordcel_xyz",    "TrutsXYZ",    "StellarSoulNFT",    "superteam_xyz","Bunkr_io",
            "candypay_xyz",    "solanabridge",    "solana_tourism",    "MemeDaoSOL",    "superteamIND",    "superteamVN",     "superteamDE",    "superteamUK",      "superteamUAE","superteamNG",      
            "superteamBalkan",      "superteamMY",    "superteamFR",    "superteamJP",    "superteamSG",    "superteamCA",    "superteamTR",    "superteamTH",    "superteamPH",    "superteamMX", "superteamBR",      
        ]
        logger.info(f"Using default trusted accounts list with {len(default_trusted)} accounts")
        return default_trusted

    def check_mentions(self):
        """Check for new mentions containing the trigger phrase"""
        try:
            logger.info("Checking for new mentions...")

            # Search for mentions of the bot account
            bot_username = self.api.verify_credentials().screen_name
            search_query = f"@{bot_username} riddle me this"

            # Get recent tweets mentioning the bot with the trigger phrase
            tweets = tweepy.Cursor(
                self.api.search_tweets,
                q=search_query,
                result_type="recent",
                tweet_mode="extended"
            ).items(10)  # Limit to 10 recent tweets

            mentions_found = 0
            for tweet in tweets:
                try:
                    # Skip if already processed
                    if tweet.id in self.processed_tweets:
                        continue

                    # Skip if tweet is too old (older than 1 hour)
                    if tweet.created_at < self.last_check_time:
                        continue

                    logger.info(f"Processing mention from @{tweet.user.screen_name}")

                    # Check if this is a reply to another tweet
                    if tweet.in_reply_to_status_id:
                        # Get the original tweet being replied to
                        try:
                            original_tweet = self.api.get_status(
                                tweet.in_reply_to_status_id,
                                tweet_mode="extended"
                            )

                            # Analyze the original tweet's author
                            analysis = self.analyze_account(original_tweet.user)

                            # Generate and post report
                            self.post_trustworthiness_report(tweet, original_tweet.user, analysis)

                            mentions_found += 1

                        except tweepy.TweepyException as e:
                            logger.error(f"Could not fetch original tweet: {e}")
                            continue
                    else:
                        logger.info("Mention is not a reply to another tweet, skipping")

                    # Mark as processed
                    self.processed_tweets.add(tweet.id)

                except Exception as e:
                    logger.error(f"Error processing tweet {tweet.id}: {e}")
                    continue

            logger.info(f"Processed {mentions_found} new mentions")
            self.last_check_time = datetime.now()

        except Exception as e:
            logger.error(f"Error checking mentions: {e}")

    def analyze_account(self, user):
        """Analyze a Twitter account's trustworthiness"""
        logger.info(f"Analyzing account: @{user.screen_name}")

        analysis = {
            'username': user.screen_name,
            'display_name': user.name,
            'account_age_days': (datetime.now() - user.created_at).days,
            'followers_count': user.followers_count,
            'following_count': user.friends_count,
            'tweet_count': user.statuses_count,
            'verified': user.verified,
            'has_profile_image': not user.default_profile_image,
            'has_bio': bool(user.description),
            'bio_length': len(user.description) if user.description else 0,
            'trusted_network_score': 0,
            'risk_level': 'UNKNOWN',
            'trust_score': 0
        }

        # Calculate follower/following ratio
        if analysis['following_count'] > 0:
            analysis['follower_ratio'] = analysis['followers_count'] / analysis['following_count']
        else:
            analysis['follower_ratio'] = analysis['followers_count']  # Following 0 accounts

        # Check trusted network connections
        analysis['trusted_network_score'] = self.check_trusted_network(user)

        # Calculate overall trust score
        analysis['trust_score'] = self.calculate_trust_score(analysis)

        # Determine risk level
        analysis['risk_level'] = self.determine_risk_level(analysis)

        return analysis

    def check_trusted_network(self, user):
        """Check how many trusted accounts follow this user"""
        trusted_followers = 0

        try:
            # Get followers of the user (limited by API rate limits)
            follower_ids = []
            for page in tweepy.Cursor(self.api.get_follower_ids, user_id=user.id).pages(1):
                follower_ids.extend(page)
                break  # Only get first page due to rate limits

            # Check if any trusted accounts are in the followers list
            for trusted_account in self.trusted_accounts:
                try:
                    trusted_user = self.api.get_user(screen_name=trusted_account)
                    if trusted_user.id in follower_ids:
                        trusted_followers += 1
                        logger.info(f"Trusted account @{trusted_account} follows @{user.screen_name}")
                except:
                    continue  # Skip if trusted account doesn't exist or is private

        except Exception as e:
            logger.warning(f"Could not check trusted network for @{user.screen_name}: {e}")

        return trusted_followers

    def calculate_trust_score(self, analysis):
        """Calculate overall trust score (0-100)"""
        score = 0

        # Account age bonus (max 20 points)
        if analysis['account_age_days'] > 365:
            score += 20
        elif analysis['account_age_days'] > 180:
            score += 15
        elif analysis['account_age_days'] > 90:
            score += 10
        elif analysis['account_age_days'] > 30:
            score += 5

        # Follower ratio bonus (max 20 points)
        if 0.1 <= analysis['follower_ratio'] <= 10:
            score += 20  # Healthy ratio
        elif 0.01 <= analysis['follower_ratio'] <= 100:
            score += 10  # Acceptable ratio

        # Profile completeness (max 15 points)
        if analysis['has_profile_image']:
            score += 5
        if analysis['has_bio'] and analysis['bio_length'] > 20:
            score += 10

        # Verification bonus (max 15 points)
        if analysis['verified']:
            score += 15

        # Trusted network bonus (max 30 points)
        if analysis['trusted_network_score'] >= 3:
            score += 30  # Strong trusted network
        elif analysis['trusted_network_score'] >= 2:
            score += 20  # Good trusted network
        elif analysis['trusted_network_score'] >= 1:
            score += 10  # Some trusted connections

        return min(score, 100)  # Cap at 100

    def determine_risk_level(self, analysis):
        """Determine risk level based on trust score"""
        if analysis['trust_score'] >= 70:
            return "LOW RISK ✅"
        elif analysis['trust_score'] >= 40:
            return "MEDIUM RISK ⚠️"
        else:
            return "HIGH RISK ❌"

    def post_trustworthiness_report(self, trigger_tweet, analyzed_user, analysis):
        """Post trustworthiness report as a reply"""
        try:
            # Generate report text
            report = self.generate_report_text(analysis)

            # Post reply
            reply = self.api.update_status(
                status=report,
                in_reply_to_status_id=trigger_tweet.id,
                auto_populate_reply_metadata=True
            )

            logger.info(f"Posted trustworthiness report for @{analyzed_user.screen_name}")
            return reply

        except Exception as e:
            logger.error(f"Failed to post report: {e}")
            return None

    def generate_report_text(self, analysis):
        """Generate the trustworthiness report text"""

        # Special case for accounts in trusted list
        if analysis['username'].lower() in [acc.lower() for acc in self.trusted_accounts]:
            return f"🔒 VERIFIED TRUSTED ACCOUNT\n\n@{analysis['username']} is on our trusted accounts list.\n\nRisk Level: VERIFIED ✅\nTrust Score: 100/100\n\n#RUGGUARD #TrustScore"

        report_lines = [
            f"📊 TRUSTWORTHINESS REPORT",
            f"Account: @{analysis['username']}",
            f"",
            f"🎯 Risk Level: {analysis['risk_level']}",
            f"📈 Trust Score: {analysis['trust_score']}/100",
            f"",
            f"📋 Account Metrics:",
            f"• Age: {analysis['account_age_days']} days",
            f"• Followers: {analysis['followers_count']:,}",
            f"• Following: {analysis['following_count']:,}",
            f"• Ratio: {analysis['follower_ratio']:.2f}",
            f"• Verified: {'Yes' if analysis['verified'] else 'No'}",
            f"",
            f"🤝 Trusted Network: {analysis['trusted_network_score']} connections",
            f"",
            f"#RUGGUARD #TrustScore"
        ]

        # Join and ensure it fits in tweet length
        report = "\n".join(report_lines)

        # Truncate if too long (Twitter's limit is 280 characters)
        if len(report) > 275:
            report = report[:272] + "..."

        return report

    def run_bot(self):
        """Main bot loop"""
        logger.info("Starting RUGGUARD bot...")

        # Schedule periodic checks every 5 minutes
        schedule.every(5).minutes.do(self.check_mentions)

        # Run initial check
        self.check_mentions()

        # Keep the bot running
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute for scheduled tasks
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error in bot loop: {e}")
                time.sleep(300)  # Wait 5 minutes before retrying

def main():
    """Main function to start the bot"""
    try:
        bot = RUGGUARDBot()
        bot.run_bot()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        return 1
    return 0

if __name__ == "__main__":
    exit(main())
