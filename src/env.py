# edit your system environment variables to include the following, or hardcode them here
import os


token = os.getenv("CLYPPY_TOKEN")  # discord bot token


class TwitchCreds:
    secret = os.getenv("CLYPPY_TWITCH_SECRET")  # twitch api project secret + id
    id = os.getenv("CLYPPY_TWITCH_ID")


class DbCredentials:
    username = os.getenv("CLYPPY_DB_USER")
    passw = os.getenv("CLYPPY_DB_PASS")
    host = os.getenv("CLYPPY_DB_HOST")
    dbname = os.getenv("CLYPPY_DB_NAME")
    port = os.getenv("CLYPPY_DB_PORT")
