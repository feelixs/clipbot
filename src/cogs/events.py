from interactions import slash_command, listen, SlashContext, Guild, Extension, OptionType, SlashCommandOption
from interactions.api.events.discord import GuildJoin, GuildLeft
from datetime import datetime
from typing import Union, Optional
import logging


class Events(Extension):
    def __init__(self, bot, **kwargs):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger("events")

        self.last_posted_stats_at: Optional[datetime] = None
        self.task_num = 0
        self.CHANGE_PRESENCE_EVERY = 10
        self.ready, self.my_guilds = False, []
        self._bot = bot
        self.SHARD_ID = kwargs['shardid']
        self.TOTAL_SHARDS = kwargs['totalshards']
        self.discord_tools = kwargs['discordtools']
        self._db = kwargs['db']

        try:
            self.catchup_leaves = kwargs['catchup_leaves']
        except KeyError:
            self.catchup_leaves = True
        try:
            self.wait: int = kwargs['wait']
        except KeyError:
            self.wait: int = 60

    async def _leave(self, guild: Union[Guild, int]):
        if isinstance(guild, Guild):
            name, gid = guild.name, guild.id
        else:
            name, gid = guild, guild
        await self._db.cnx.execute_query(
            "UPDATE guild_twitch_channel SET last_clip_sent = NULL, has_left = 1 WHERE guild_id = %s;",
            values=[gid])
        self.logger.info(f'Left guild: {name}')

    @listen()
    async def on_guild_left(self, event: GuildLeft):
        if self.ready:
            await self._leave(event.guild)

    @listen()
    async def on_guild_join(self, event: GuildJoin):
        if self.ready:
            g = await self._db.add_guild(event.guild)
            self.logger.info(g)
            self.logger.info(f'Joined new guild: {event.guild.name}')

    @slash_command(name="log", description="Display the chatlogs for a Twitch user",
                   options=[SlashCommandOption(name="user",
                                               description="the Twitch user to check logs for",
                                               required=True,
                                               type=OptionType.STRING),
                            SlashCommandOption(name="channel",
                                               description="the Twitch channel (username) where they sent chat messages",
                                               required=True,
                                               type=OptionType.STRING),
                            SlashCommandOption(name="year",
                                               description="the year to retrieve logs from",
                                               required=False,
                                               type=OptionType.INTEGER),
                            SlashCommandOption(name="month",
                                               description="the month to retrieve logs from",
                                               required=False,
                                               type=OptionType.INTEGER)
                            ])
    async def log(self, ctx: SlashContext, user: str, channel: str, year: int = None, month: int = None):
        message = await self.discord_tools.generate_twitch_log(ctx, user, channel, year, month)

    @listen()
    async def on_ready(self):
        if not self.ready:
            self.ready = True
            self.logger.info(f"events cog logged in as {self._bot.user.username}")
            self.logger.info(f"running as shard: {self.SHARD_ID}")
            self.logger.info(f"total shards: {self.TOTAL_SHARDS}")
            self.logger.info(f"my guilds: {len(self._bot.guilds)}")
            self.logger.info("--------------")
            my_guilds = [guild.id for guild in self._bot.guilds]
            if self.catchup_leaves:
                stored_guilds = await self._db.cnx.execute_query("select guild_id, has_left from guild_twitch_channel")
                for guild in stored_guilds:
                    guild, hasleft = guild[0], guild[1]
                    if guild not in my_guilds and hasleft != 1:
                        await self._leave(guild)
                        # calling leave on a guild updates all alerts for it
                        continue
