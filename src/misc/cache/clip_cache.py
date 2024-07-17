from src.misc.database import Database
from interactions.models.discord import Guild
from datetime import datetime
from src.misc.twitch import Clip
from typing import Union
import time


class ClipCache:
    def __init__(self, DB: Database, refresh_every: int = 60):
        self._timestamps, self._pending_clips, self._clip_ids = {}, {}, {}
        self._include_chat, self._preserve = {}, {}
        self._last_refreshed = time.time()
        self._refresh_delta = refresh_every
        # we need to refresh the settings from db periodically in case an alert's settings is edited (rmd & added again)
        self._DB = DB

    async def _refresh(self):
        self._last_refreshed = time.time()
        data = await self._DB.cnx.execute_query("select guild_id, channel_id, alert_type, include_chat, preserve_quality from guild_twitch_channel")
        self._include_chat = {}
        for g in data:
            guild, channel, alert_type, chat, preserve = g[0], g[1], g[2], g[3], g[4]
            self._include_chat[f"{guild}-{channel}-{alert_type}"] = chat
            self._preserve[f"{guild}-{channel}-{alert_type}"] = preserve

    def _check_clip_queue(self, guild):
        try:
            if not isinstance(self._pending_clips[guild], list):
                self._pending_clips[guild] = []
        except KeyError:
            self._pending_clips[guild] = []

    def add_queued_clip(self, guild: Union[Guild, int], add: Clip):
        if isinstance(guild, Guild):
            guild = guild.id
        self._check_clip_queue(guild)
        self._pending_clips[guild].append(add)

    def rm_queued_clip(self, guild: Union[Guild, int], add: Clip):
        if isinstance(guild, Guild):
            guild = guild.id
        self._check_clip_queue(guild)
        if add in self._pending_clips[guild]:
            self._pending_clips[guild].remove(add)
            return True
        return False

    def get_queued_clips(self, guild: Union[Guild, int]) -> list:
        if isinstance(guild, Guild):
            guild = guild.id
        self._check_clip_queue(guild)
        return self._pending_clips[guild] if self._pending_clips[guild] else [Clip(None, api=None)]

    def is_queued(self, guild, clip):
        return clip.id in [c.id for c in self.get_queued_clips(guild)]

    async def get_include_chat_enabled(self, guild: Union[Guild, int], channel: int, alert_type: int, auto_update_cache=True):
        if time.time() - self._last_refreshed > self._refresh_delta:
            await self._refresh()
        if isinstance(guild, Guild):
            guild = guild.id
        try:
            return self._include_chat[f'{guild}-{channel}-{alert_type}']
        except KeyError:
            res = await self._DB.cnx.execute_query("select include_chat from guild_twitch_channel where guild_id = %s and channel_id = %s and alert_type = %s",
                                                    values=[guild, channel, alert_type], scaler=True)
            if auto_update_cache:
                # if this isn't enabled, you'll need to call set_include_chat_enabled(commit=False) after fetching from DB
                self._include_chat[f'{guild}-{channel}-{alert_type}'] = res
            return res

    async def get_preserve_quality(self, guild: Union[Guild, int], channel: int, alert_type: int, auto_update_cache=True):
        if time.time() - self._last_refreshed > self._refresh_delta:
            await self._refresh()
        if isinstance(guild, Guild):
            guild = guild.id
        try:
            return self._preserve[f'{guild}-{channel}-{alert_type}']
        except KeyError:
            res = await self._DB.cnx.execute_query("select preserve_quality from guild_twitch_channel where guild_id = %s and channel_id = %s and alert_type = %s",
                                                    values=[guild, channel, alert_type], scaler=True)
            if auto_update_cache:
                # if this isn't enabled, you'll need to call set_include_chat_enabled(commit=False) after fetching from DB
                self._preserve[f'{guild}-{channel}-{alert_type}'] = res
            return res

    async def set_include_chat_enabled(self, guild: Guild, channel: int, alert_type: int, to: bool, commit=True):
        self._include_chat[f'{guild.id}-{channel}-{alert_type}'] = to
        if commit:
            await self._DB.cnx.execute_query("update guild_twitch_channel set include_chat = %s where guild_id = %s and channel_id = %s and alert_type = %s",
                                                    values=[to, int(guild.id), channel, alert_type])

    async def set_preserve_quality(self, guild: Guild, channel: int, alert_type: int, to: bool, commit=True):
        self._preserve[f'{guild.id}-{channel}-{alert_type}'] = to
        if commit:
            await self._DB.cnx.execute_query("update guild_twitch_channel set preserve_quality = %s where guild_id = %s and channel_id = %s and alert_type = %s",
                                                    values=[to, int(guild.id), channel, alert_type])

    async def set_last_clip_timestamp(self, guild: Guild, channel: int, alert_type: int, to: datetime):
        self._timestamps[f'{guild.id}-{channel}-{alert_type}'] = to
        await self._DB.set_last_clip_sent(guild, channel, alert_type, to)

    async def pull_last_clip_timestamp(self, guild: Guild, channel: int, alert_type: int):
        return await self._DB.get_last_clip_sent(guild, channel, alert_type, utc=True)

    async def get_last_clip_timestamp(self, guild: Guild, channel: int, alert_type: int):
        try:
            return self._timestamps[f'{guild.id}-{channel}-{alert_type}']
        except KeyError:
            return await self._DB.get_last_clip_sent(guild, channel, alert_type, utc=True)
