from interactions import Client, Intents
from src.misc.twitch import TwitchAPI, TwitchTools
from src.misc.discord import DiscordTools
from src.misc.database import Database
from env import token, TwitchCreds, LOG_PATH
import logging
import asyncio

SHARD_ID = 0

intent = Intents.DEFAULT
Bot = Client(intents=intent)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("main.py")
DB = Database(maxsize=50, pool_name="ClipBotPool")

TWITCH_API = TwitchAPI(key=TwitchCreds.id, secret=TwitchCreds.secret, logger=logger, log_path=LOG_PATH, log_name="twitch-api-all-usage-shard"+str(SHARD_ID)+".log")
TWITCH_TOOLS = TwitchTools(TWITCH_API)
DISCORD_TOOLS = DiscordTools(Bot, DB, logger, twitchtools=TWITCH_TOOLS)


async def main():
    Bot.load_extension('cogs.clip_alerts', db=DB, twitchtools=TWITCH_TOOLS, discordtools=DISCORD_TOOLS)
    Bot.load_extension('cogs.events', db=DB, twitchtools=TWITCH_TOOLS, discordtools=DISCORD_TOOLS)
    await DB.connect(asyncio.get_running_loop())
    await Bot.astart(token=token)

if __name__ == "__main__":
    asyncio.run(main())
