# run this ONCE after creating your mysql database. It will create all the necessary tables & columns
from src.misc.database import Database
from src.env import DbCredentials
import asyncio
import mysql.connector
import logging


DB_PASS = "12345678"  # replace with the password of the root user
DB_HOST = "127.0.0.1"  # replace with your computer's IP
DB_NAME = "clyppydb"  # name the database anything you want (if you change it make sure to also update it in env.py


logger = logging.getLogger("dbsetup")


async def create_database_if_not_exists():
    cnx = mysql.connector.connect(user="root", password=DB_PASS, host=DB_HOST)
    cursor = cnx.cursor()
    logger.info(f"Creating database {DB_NAME}")
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    cursor.execute(f"USE {DB_NAME}")
    cursor.execute("CREATE TABLE IF NOT EXISTS guild_twitch_channel ("
                   "guild_id BIGINT,"
                   "channel_id BIGINT,"
                   "channel_name VARCHAR(255),"
                   "discord_channel BIGINT,"
                   "alert_type INT,"
                   "has_left BOOLEAN,"
                   "settings VARCHAR(255),"
                   "trending_interval INT,"
                   "is_game BOOLEAN,"
                   "last_clip_sent TIMESTAMP,"
                   "PRIMARY KEY (guild_id, channel_id, alert_type))")
    cursor.execute("CREATE TABLE IF NOT EXISTS guilds ("
                   "guild_id BIGINT,"
                   "guild_name TEXT,"
                   "PRIMARY KEY (guild_id))")
    cursor.close()
    cnx.close()


async def main():
    await create_database_if_not_exists()
    creds = DbCredentials()
    creds.username = "root"
    creds.passw = DB_PASS
    creds.port = 3306
    creds.host = DB_HOST
    creds.dbname = DB_NAME
    d = Database(creds, maxsize=50, pool_name="CLYPPY_POOL")
    await d.connect(asyncio.get_running_loop())


asyncio.run(main())
