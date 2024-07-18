# run this ONCE after creating your mysql database. It will create all the necessary tables & columns
from src.misc.database import Database
from src.env import DbCredentials
import asyncio
import mysql.connector

creds = DbCredentials()
d = Database(creds, maxsize=50, pool_name="CLYPPY_POOL")


async def create_database_if_not_exists():
    cnx = mysql.connector.connect(user="root", password=creds.passw, host="localhost")
    cursor = cnx.cursor()
    d.logger.info(f"Creating database {creds.dbname}")
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {creds.dbname}")
    cursor.execute(f"USE {creds.dbname}")
    d.logger.info(f"Creating table 'guild_twitch_channel'")
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
    d.logger.info(f"Creating table 'guilds'")
    cursor.execute("CREATE TABLE IF NOT EXISTS guilds ("
                   "guild_id BIGINT,"
                   "guild_name TEXT,"
                   "PRIMARY KEY (guild_id))")
    d.logger.info(f"Creating table 'twitch_channels'")
    cursor.execute("CREATE TABLE IF NOT EXISTS twitch_channels ("
                   "channel_id BIGINT,"
                   "user_name VARCHAR(100),"
                   "PRIMARY KEY (channel_id))")
    cursor.close()
    cnx.close()


async def main():
    await create_database_if_not_exists()
    await d.connect(asyncio.get_running_loop())
    d.logger.info("Database setup was successful!")
    await d.close()

if __name__ == "__main__":
    asyncio.run(main())
