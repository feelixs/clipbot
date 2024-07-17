from interactions import listen, Task, IntervalTrigger, Embed, Button, ButtonStyle, slash_command, SlashContext, Extension
from interactions.models.discord import Snowflake
from src.misc.tasks import ClipTasks, DEFAULT_TRENDING_INTERVAL
from datetime import datetime
from asyncio import gather
import aiohttp
from src.misc.twitch import TwitchAPI, TwitchTools
from time import time
from src.env import TwitchCreds
import logging
import os


DEFAULT_WAIT = 60 * 5  # 5 minutes


class ClipAlerts(Extension):
    def __init__(self, bot, **kwargs):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger("clip alerts")

        self._bot = bot
        self._clip_alert_types = [0, 1]
        self.SHARD_ID = kwargs['shardid']
        self._db = kwargs['db']
        self._twitchApi = TwitchAPI(key=TwitchCreds.id, secret=TwitchCreds.secret,
                                    logger=self.logger,
                                    log_path=os.getenv('TWITCH_API_REMAINING_LOG'),
                                    log_name="twitch-api-clips-usage-shard" + str(self.SHARD_ID) + ".log")
        self.twitch_tools = TwitchTools(self._twitchApi)
        self.discord_tools = kwargs['discordtools']
        self.discord_misc = ClipTasks(bot, self._db, self.logger, self.twitch_tools,
                                      log_path=os.getenv('TWITCH_API_REMAINING_LOG'),
                                      log_name="twitch-api-clips-usage-shard-" + str(self.SHARD_ID) + ".log")

        try:
            self.catchup: bool = kwargs['catchup']
        except KeyError:
            self.catchup: bool = True
        try:
            self.wait: int = kwargs['wait']
        except KeyError:
            self.wait: int = DEFAULT_WAIT
        try:
            self._clyppy_api_key = kwargs['clyppy_key']
        except KeyError:
            self._clyppy_api_key = os.getenv('MY_API_SECRET')
        self.task = Task(self.my_task, IntervalTrigger(seconds=self.wait))

    async def set_my_ping(self):
        header = {'Authorization': f"SecretID {self._clyppy_api_key}"}
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.clyppy.com/ping-set/", headers=header,
                                    data={'proc': 'clips', 'utc': datetime.utcnow().timestamp()}) as resp:
                try:
                    data = await resp.json()
                except Exception as e:
                    self.logger.error(f"could not set ping: {await resp.text()}")
                    raise
                return data

    @slash_command(name="alerts", description="View all CLYPPY Alerts in this server")
    async def alerts(self, ctx: SlashContext):
        anyadded = False
        added = await self._db.cnx.execute_query("select channel_name, alert_type, clip_alert_channel, mention_role, settings, include_chat, trending_interval from guild_twitch_channel where guild_id = %s", [int(ctx.guild.id)])
        clip_embed = Embed(title="Twitch Clip Alerts")
        onlive_embed = Embed(title="Twitch Stream Alerts")
        youtube_embed = Embed(title="YouTube Alerts")
        try:
            for twitch, alert, channel, role, sett, chat, t_i in added:
                if sett == "0":  # this sql column is set to string
                    sett = False
                else:
                    sett = True
                if alert == 0:
                    alert = "new clips"
                elif alert == 1:
                    alert = "trending clips"
                elif alert == int(os.getenv("ONLIVE_ALERT_NUM")):
                    alert = "stream notifications"
                elif alert == 6:
                    alert = "Upload Hot Clips"
                    if chat == 0:
                        chat = False
                    else:
                        chat = True
                elif alert == 5:
                    alert = "Upload New Clips"
                if role is not None:
                    if role == 0:
                        role = "None"
                    elif role == 1:
                        role = "@everyone"
                    elif role == 2:
                        role = "@here"
                    else:
                        role = f"<@&{role}>"
                field_name = f"{twitch}"
                field_value = f"- Alert Type: {alert}\n- Discord Channel: <#{channel}>"
                if alert == "stream notifications":
                    field_value += f"\n- Mentions: {role}"
                if alert == "trending clips":
                    if t_i is not None:
                        field_value += f"\n- Trending Interval: {t_i}"
                    else:
                        field_value += f"\n- Trending Interval: {DEFAULT_TRENDING_INTERVAL}"
                if alert == "new clips" or alert == "trending clips":
                    field_value += f"\n- Use Embeds: {sett}"
                if alert == "Upload Hot Clips":
                    field_value += f"\n- Include Chat: {chat}"

                if alert == "stream notifications":
                    onlive_embed.add_field(name=field_name, value=field_value, inline=True)
                else:
                    clip_embed.add_field(name=field_name, value=field_value, inline=True)
            anyadded = True
        except TypeError:  # nothing added
            clip_embed.description = "None"

        yt_added = await self._db.cnx.execute_query("select channel_name, alert_type, alert_channel_id, mention_role, show_desc from guild_yt_channel where guild_id = %s", [int(ctx.guild.id)])
        try:
            for handle, alert_type, discord_channel_id, role, desc in yt_added:
                if desc == 0 or desc is None:
                    desc = False
                else:
                    desc = True
                if alert_type == 8:
                    alert_type = "youtube uploads"
                if role is not None:
                    if role == 0:
                        role = "None"
                    elif role == 1:
                        role = "@everyone"
                    elif role == 2:
                        role = "@here"
                    else:
                        role = f"<@&{role}>"
                field_value = f"- Alert Type: {alert_type}\n- Discord Channel: <#{discord_channel_id}>\n- Mentions: {role}\n-Include Description: {desc}"
                youtube_embed.add_field(name=handle, value=field_value, inline=True)
                anyadded = True
        except TypeError:
            youtube_embed.description = "None"
        if onlive_embed.description is None:
            onlive_embed.description = "None"
        else:
            anyadded = True
        if anyadded:
            await ctx.send(embeds=[clip_embed, onlive_embed, youtube_embed, Embed(title="More Help", description="**[Help with Alerts](https://help.clyppy.com/dashboard/alerts/)**" + create_nexus_str())], delete_after=600)
        else:
            btn = [Button(label="Visit Dashboard", url="https://my.clyppy.com", style=ButtonStyle.LINK)]
            await ctx.send(f"**[Help with Alerts](https://help.clyppy.com/dashboard/alerts/)**\n\nYou don't have any alerts. Visit your Dashboard to add one!" + create_nexus_str(), components=btn, delete_after=600)

    async def my_task(self):
        start = time()
        await self.set_my_ping()
        # only run for the guilds this shard is in
        tasks = []
        for guild in self._bot.guilds:
            if self._bot.get_shard_id(int(guild.id)) != self.SHARD_ID:
                self.logger.info(f"skipping guild {guild.id} ({guild.name}) because it's not in this shard")
                continue
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
        # if time.time() - start > args.wait:
        self.logger.info(f"(SHARD {self.SHARD_ID}) took {time() - start} secs")  # after it takes more than --wait we should add more shards

    @listen()
    async def on_startup(self):
        self.task.start()
        self.logger.info(f"clips cog logged in as {self._bot.user.username}")
        self.logger.info(f"total shards: {self._bot.total_shards}")
        self.logger.info(f"shard id: {self.SHARD_ID}")
        self.logger.info(f"my guilds: {len(self._bot.guilds)}")
        self.logger.info("--------------")
        if not self.catchup:
            self.logger.info("will not catchup for new clips")
            await self._db.cnx.execute_query("UPDATE guild_twitch_channel SET last_clip_sent = NULL where alert_type = 0")
        await self._db.cnx.execute_query("UPDATE procstats set started_at = %s where process_name = 'clips'", values=[datetime.utcnow()])
