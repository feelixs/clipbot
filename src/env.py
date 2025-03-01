# edit your system environment variables to include the following, or hardcode them here
import os

LOG_PATH = os.path.dirname(os.path.abspath(__file__))

token = os.getenv("CLIP_BOT_TOKEN")  # discord bot token

# how many seconds to wait between clip refreshes
DEFAULT_WAIT = 60 * 2  # 2 minutes


# the number of days to sort all trending clips by when checking for new entries
DEFAULT_TRENDING_INTERVAL = 28  # in days


class TwitchCreds:
    secret = os.getenv("CLIP_BOT_TWITCH_SECRET")  # twitch api project secret + id
    id = os.getenv("CLIP_BOT_TWITCH_ID")


class DbCredentials:
    # update the password to what you set when you installed mysql
    passw = '12345678'
    # you can probably leave the rest as is
    username = 'root'
    dbname = 'clip_bot_db'
    host = 'localhost'
    port = '3306'
