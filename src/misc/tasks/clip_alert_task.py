from interactions.models.discord import Guild, TYPE_MESSAGEABLE_CHANNEL, Permissions
from datetime import datetime, timezone, timedelta
import traceback

from src.misc.database import Database
from src.misc.discord import DiscordTools
from src.misc.twitch import UserInfo, Game
from src.misc.cache import ClipCache, TrendingClipCache
from src.misc.errors import TwitchObjNotExists, BotRejoinedGuild


DEFAULT_TRENDING_INTERVAL = 28  # in days


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
                    type_clip = "Trending clip"
                    views_refreshing = True
                elif alert_type == 0:
                    msg_to_be_sent = f"A new clip has been created from {usr}"
                    type_clip = "New clip"
                else:
                    return  # if it's set to stream alerts, don't check for new clips
                newclips = False
                clips_in_msg, clip_embeds, compnts = 0, [], []

                #print("last", last_clip_sent)
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
                        #print(f"(SHARD {self.bot.get_shard_id(guild.id)})", guild.name, alert_type, "added new for", clip.broadcaster_name)
                        all_sent_clips.append(clip)
                        if clips_in_msg == 10:  # discord doesn't allow more than 10 embeds per msg
                            # any clips that would have been added to this message will be added in the next task
                            break
                if newclips:
                    await self.cache.set_last_clip_timestamp(guild, channel, alert_type, theclipiwillsendandstopat)
                    if Permissions.SEND_MESSAGES in chn_ctx.permissions_for(guild.me) and Permissions.EMBED_LINKS in chn_ctx.permissions_for(guild.me) and Permissions.MENTION_EVERYONE in chn_ctx.permissions_for(guild.me):
                        discord_msg = await chn_ctx.send(msgcontent, embeds=clip_embeds, components=compnts)
                        now = datetime.utcnow().replace(tzinfo=timezone.utc)
                        for s in range(len(all_sent_clips)): # insert the sent clips into the db
                            this = all_sent_clips[s]
                            if alert_type == 0:
                                await self.DB.cnx.execute_query("INSERT INTO sent_clips (guild_id, channel_id, alert_type, clip_id, clip_title, discord_msg_id, sent_when, msg_clip_index) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                                                                values=[guild.id, channel, alert_type, this.id, this.title, discord_msg.id, now, s])
                        # revert the "invalid channel permissions" warning for this alert in the db
                        await self.DB.cnx.execute_query("update guild_twitch_channel set permissions_valid = %s where guild_id = %s and channel_id = %s and alert_type = %s",
                                                        values=[True, guild.id, channel, alert_type])
                    else:
                        await post_to_hook(ERR_WEBHOOK, f"Invalid channel permissions detected, will not send new clips for {channel_user.display_name} in #{chn_ctx.name}", guild)
                        await self.DB.cnx.execute_query("update guild_twitch_channel set permissions_valid = %s where guild_id = %s and channel_id = %s and alert_type = %s",
                                                        values=[False, guild.id, channel, alert_type])
                        print(f"{guild.name} - Invalid channel permissions detected, will not send new clips for {channel_user.display_name}")
            self.trending_cache.trim_len()
        except:
            print(traceback.format_exc())
