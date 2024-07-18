# edit your system environment variables to include the following, or hardcode them here
import os

LOG_PATH = os.path.dirname(os.path.abspath(__file__))

token = os.getenv("CLYPPY_TOKEN")  # discord bot token


class TwitchCreds:
    secret = os.getenv("CLYPPY_TWITCH_SECRET")  # twitch api project secret + id
    id = os.getenv("CLYPPY_TWITCH_ID")


class DbCredentials:
    # update the password to what you set when you installed mysql
    passw = '12345678'
    # you can probably leave the rest as is
    username = 'root'
    dbname = 'clyppydb'
    host = 'localhost'
    port = '3306'
