from interactions import listen, Task, IntervalTrigger, Embed, Button, ButtonStyle, slash_command, SlashContext, Extension
from interactions.models.discord import Snowflake
from src.misc.tasks import ClipTasks, DEFAULT_TRENDING_INTERVAL
from datetime import datetime
from asyncio import gather
from src.misc.twitch import TwitchAPI, TwitchTools
from src.env import TwitchCreds, LOG_PATH
import logging


DEFAULT_WAIT = 60 * 5  # 5 minutes


class ClipAlerts(Extension):
    def __init__(self, bot, **kwargs):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger("clip alerts")

        self._bot = bot
        self._clip_alert_types = [0, 1]
        self._db = kwargs['db']
        self._twitchApi = TwitchAPI(key=TwitchCreds.id, secret=TwitchCreds.secret,
                                    logger=self.logger,
                                    log_path=LOG_PATH,
                                    log_name="twitch-api-clips-usage.log")
        self.twitch_tools = TwitchTools(self._twitchApi)
        self.discord_tools = kwargs['discordtools']
        self.discord_misc = ClipTasks(bot, self._db, self.logger, self.twitch_tools,
                                      log_path=LOG_PATH,
                                      log_name="twitch-api-clips-usage.log")

        try:
            self.catchup: bool = kwargs['catchup']
        except KeyError:
            self.catchup: bool = True
        try:
            self.wait: int = kwargs['wait']
        except KeyError:
            self.wait: int = DEFAULT_WAIT
        self.task = Task(self.my_task, IntervalTrigger(seconds=self.wait))

    @slash_command(name="alerts", description="View all CLYPPY Alerts in this server")
    async def alerts(self, ctx: SlashContext):
        added = await self._db.cnx.execute_query("select channel_name, alert_type, discord_channel, settings, trending_interval from guild_twitch_channel where guild_id = %s", [int(ctx.guild.id)])
        clip_embed = Embed(title="Twitch Clip Alerts")
        try:
            for twitch, alert, channel, sett, t_i in added:
                if sett == "0":  # this sql column is set to string
                    sett = False
                else:
                    sett = True
                if alert == 0:
                    alert = "new clips"
                elif alert == 1:
                    alert = "trending clips"
                field_name = f"{twitch}"
                field_value = f"- Alert Type: {alert}\n- Discord Channel: <#{channel}>"
                if alert == "trending clips":
                    if t_i is not None:
                        field_value += f"\n- Trending Interval: {t_i}"
                    else:
                        field_value += f"\n- Trending Interval: {DEFAULT_TRENDING_INTERVAL}"
                if alert == "new clips" or alert == "trending clips":
                    field_value += f"\n- Use Embeds: {sett}"
                clip_embed.add_field(name=field_name, value=field_value, inline=True)
        except TypeError:  # nothing added
            clip_embed.description = "None"

    async def my_task(self):
        tasks = []
        for guild in self._bot.guilds:
            twitch_channels = await self._db.fetch_twitch_channels(guild.id, include_has_left=True, include_settings=True)
            # alert type = 0 new clips, 1 = new trending clip
            if twitch_channels is None:
                #self.logger.info(f"no twitch channels for guild {guild.id} ({guild.name})")
                continue
            guild_has_left = twitch_channels[0][2]
            if guild_has_left:
                tasks.append(self._db.cnx.execute_query("update guild_twitch_channel set has_left = 0 where guild_id = %s", values=[guild.id]))
            for channel in twitch_channels:
                channel, alert_type, has_left, use_embed, trending_interval, is_game = channel[0], channel[1], channel[2], channel[3], channel[4], channel[5]
                # if has_left, it means the bot is in the guild but left it in the past
                # so it rejoined
                if alert_type not in self._clip_alert_types:
                    continue
                ch_id = await self._db.get_guild_clip_alert_chn(guild.id, channel, alert_type)
                if ch_id is None:
                    # alert channel ids are made to be able to be set per guild's twitch channel
                    # so if this channel's one isn't set we go to the next channel
                    continue
                try:
                    chn_ctx = await self._bot.fetch_channel(Snowflake(ch_id))
                except:
                    self.logger.info(f"could not message the provided channel {ch_id}, was it deleted?")
                    continue
                task = self.discord_misc.clip_alerts(guild, channel, alert_type, chn_ctx, use_embed, trending_interval, is_game, has_left)
                tasks.append(task)
        await gather(*tasks)

    @listen()
    async def on_startup(self):
        self.task.start()
        self.logger.info(f"clips cog logged in as {self._bot.user.username}")
        self.logger.info(f"my guilds: {len(self._bot.guilds)}")
        self.logger.info("--------------")
        if not self.catchup:
            self.logger.info("will not catchup for new clips")
            await self._db.cnx.execute_query("UPDATE guild_twitch_channel SET last_clip_sent = NULL where alert_type = 0")
