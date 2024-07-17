from interactions import Client, Intents
from src.misc.twitch import TwitchAPI, TwitchTools
from src.misc.discord import DiscordTools
from src.misc.database import Database
from env import token, TwitchCreds
import logging
import asyncio
import os

SHARD_ID = 0

intent = Intents.DEFAULT
Bot = Client(intents=intent)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("main.py")
DB = Database(maxsize=50, pool_name="CLYPPY_POOL")

TWITCH_API = TwitchAPI(key=TwitchCreds.id, secret=TwitchCreds.secret, logger=logger, log_path=os.path.dirname(os.path.abspath(__file__)), log_name="twitch-api-all-usage-shard"+str(SHARD_ID)+".log")
TWITCH_TOOLS = TwitchTools(TWITCH_API)
DISCORD_TOOLS = DiscordTools(Bot, DB, logger, twitchtools=TWITCH_TOOLS)


async def main():
    Bot.load_extension('cogs.clip_alerts', shardid=SHARD_ID, db=DB, twitchtools=TWITCH_TOOLS,
                       discordtools=DISCORD_TOOLS)
    await Bot.astart(token=token)


asyncio.run(main())
