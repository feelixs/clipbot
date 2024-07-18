from interactions.models.discord import Guild, TYPE_MESSAGEABLE_CHANNEL, Permissions
from datetime import datetime, timezone, timedelta
import traceback

from src.misc.database import Database
from src.misc.discord import DiscordTools
from src.misc.twitch import UserInfo, Game
from src.misc.cache import ClipCache, TrendingClipCache
from src.misc.errors import TwitchObjNotExists, BotRejoinedGuild
from src.env import DEFAULT_TRENDING_INTERVAL


class ClipTasks(DiscordTools):
    """All processes needed for clip fetching & posting"""
    def __init__(self, client, db: Database, logger, twitch_tools, log_path=None, log_name=None):
        super().__init__(client, db, logger, twitch_tools, log_path, log_name)
        self.DB = db
        self.cache = ClipCache(db)
        self.trending_cache = TrendingClipCache()
        self.i = 0

    async def clip_alerts(self, guild: Guild, channel: int, alert_type: int, chn_ctx: TYPE_MESSAGEABLE_CHANNEL, use_embeds, trending_interval, is_game=False, has_left=False):
        """Main clip task, posts embeds with new/trending clips"""
        try:
            try:
                if has_left:
                    raise BotRejoinedGuild  # reset last_timestamp on rejoins
                last_clip_sent = await self.cache.pull_last_clip_timestamp(guild, channel, alert_type)
            except (BotRejoinedGuild, ValueError):
                last_clip_sent = datetime.utcnow()
                await self.cache.set_last_clip_timestamp(guild, channel, alert_type, last_clip_sent)
            last_clip_sent = last_clip_sent.replace(tzinfo=timezone.utc)
            if is_game == 1:
                is_game = True
            else:
                is_game = False
            if not is_game:
                # twitch users
                try:
                    channel_user = await self.DB.cnx.execute_query("SELECT * from twitch_channels where channel_id = %s", [channel])
                    channel_user = UserInfo(name=channel_user[0][1], id=channel_user[0][0], api=self.TWITCH_API)
                except:
                    try:
                        channel_user = await self.TWITCH_TOOLS.find_user(query=None, id=channel)
                    except TwitchObjNotExists:
                        return
            else:
                # twitch game
                try:
                    channel_user = await self.DB.cnx.execute_query("SELECT * from game_info where game_id = %s", [channel])
                    channel_user = Game(name=channel_user[0][1], id=channel_user[0][0], api=self.TWITCH_API)
                except:
                    try:
                        channel_user = await Game(id=channel, api=self.TWITCH_API).fetch()
                    except TwitchObjNotExists:
                        return
            if trending_interval is None:
                trending_interval = DEFAULT_TRENDING_INTERVAL
            if use_embeds is None:
                # default value = use embeds
                use_embeds = True
            elif use_embeds == "0":
                use_embeds = False
            elif use_embeds == "1":
                use_embeds = True
            if alert_type == 0:
                latest_clips = await channel_user.get_broadcaster_clips(limit=100, started_at=last_clip_sent)
            else:  # alert_type == 1:
                latest_clips = await channel_user.get_broadcaster_clips(limit=100, started_at=datetime.utcnow() - timedelta(days=int(trending_interval)))
            if not latest_clips:
                # if it's empty (no clips)
                return
            else:
                views_refreshing = False
                usr = channel_user.username
                if not use_embeds:
                    usr = f"`{usr}`"
                if alert_type == 1:
                    msg_to_be_sent = f"A clip from {usr} is now trending"
                    views_refreshing = True
                elif alert_type == 0:
                    msg_to_be_sent = f"A new clip has been created from {usr}"
                else:
                    return
                newclips = False
                clips_in_msg, clip_embeds, compnts = 0, [], []
                theclipiwillsendandstopat = last_clip_sent
                msgcontent = ""
                all_sent_clips = []
                for clip in latest_clips:
                    if last_clip_sent < clip.created_at:
                        if alert_type == 1 and self.trending_cache.exists(guild, channel, alert_type, clip):
                            continue
                        newclips = True
                        if alert_type == 1:
                            self.trending_cache.add(guild, channel, alert_type, clip)
                        if use_embeds:
                            this_embed = await self.create_clip_embed(clip, msg_to_be_sent, refresh_views=views_refreshing)
                            clip_embeds.append(this_embed)
                        else:
                            msgcontent += self.create_clip_msg(clip, msg_to_be_sent)
                        clips_in_msg += 1
                        theclipiwillsendandstopat = clip.created_at
                        all_sent_clips.append(clip)
                        if clips_in_msg == 10:  # discord doesn't allow more than 10 embeds per msg
                            # any clips that would have been added to this message will be added in the next task
                            break
                if newclips:
                    await self.cache.set_last_clip_timestamp(guild, channel, alert_type, theclipiwillsendandstopat)
                    if Permissions.SEND_MESSAGES in chn_ctx.permissions_for(guild.me) and Permissions.EMBED_LINKS in chn_ctx.permissions_for(guild.me) and Permissions.MENTION_EVERYONE in chn_ctx.permissions_for(guild.me):
                        await chn_ctx.send(msgcontent, embeds=clip_embeds, components=compnts)
                    else:
                        self.logger.info(f"{guild.name} - Invalid channel permissions detected, will not send new clips for {channel_user.display_name}")
            self.trending_cache.trim_len()
        except:
            self.logger.error(traceback.format_exc())
