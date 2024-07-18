from src.misc.database.connection import PooledConnection
from interactions.models.discord.guild import Guild
from src.misc.twitch import UserInfo
from src.env import DbCredentials
from datetime import datetime, timezone
from typing import Union, Tuple
import logging


class Database:
    def __init__(self, cred: DbCredentials = None, maxsize=None, pool_name=None):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger("Database")
        if cred is None:
            self.cnx = PooledConnection(DbCredentials(), self.logger, maxsize=maxsize, pool_name=pool_name)
        else:
            self.cnx = PooledConnection(cred, self.logger, maxsize=maxsize, pool_name=pool_name)

    async def connect(self, loop):
        self.logger.info('connecting to database...')
        await self.cnx.connect(loop)

    async def store_guild_twitch_pair(self, guild: Union[Guild, int], user: UserInfo, discord_chn: int, alert_type: int):
        if isinstance(guild, Guild):
            guild = int(guild.id)
        q = "INSERT INTO guild_twitch_channel (guild_id, channel_id, channel_name, discord_channel, alert_type) " \
            "values (%s, %s, %s, %s, %s)"
        param = [guild, user.id, user.username, discord_chn, alert_type]
        await self.cnx.execute_query(q, values=param)

    async def add_guild(self, guild: Union[Guild, Tuple[int, str]]):
        if isinstance(guild, Guild):
            name = guild.name
            gid = int(guild.id)
        else:
            name = guild[1]
            gid = guild[0]
        stored = await self.select_where_eq("guilds", "guild_id", "guild_id", gid)
        if stored is None:  # doesn't exist in the db
            formatted_name = name.replace("'", "")
            await self.insert_into("guilds", int(guild.id), formatted_name)

    async def insert_into(self, table, row, what):
        """Can only run on the 'key' value of a table"""
        add_query = f"INSERT INTO {table} (guild_id, guild_name) VALUES (%s, %s)"
        await self.cnx.execute_query(add_query, values=[row, what])

    async def select_where_eq(self, table, what, where, where_is):
        select_query = f"SELECT {what} FROM {table} where {where} = %s"
        return await self.cnx.execute_query(select_query, values=[where_is], scaler=True)

    async def get_last_clip_sent(self, guild: Guild, channel_id: int, alert_type: int, utc=False) -> datetime:
        """:param guild the corresponding guild
            :param channel_id which twitch channel's clips """
        q = "select last_clip_sent from guild_twitch_channel where guild_id = %s and channel_id = %s and alert_type = %s"
        time = await self.cnx.execute_query(q, values=[guild.id, channel_id, alert_type], scaler=True)
        if time is None:
            raise ValueError("last_clip_sent was not found for values " + str([guild.id, channel_id, alert_type]))
        if utc:
            return time.replace(tzinfo=timezone.utc)
        return time

    async def set_last_clip_sent(self, guild: Union[Guild, int], channel_id: int, alert_type: int, timestamp: datetime):
        if isinstance(guild, Guild):
            guild = int(guild.id)
        formatted_timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")  # MySQL TIMESTAMP format
        query = "UPDATE guild_twitch_channel SET last_clip_sent = %s WHERE guild_id = %s AND channel_id = %s AND alert_type = %s"
        await self.cnx.execute_query(query, values=[formatted_timestamp, guild, channel_id, alert_type])

    async def fetch_twitch_channels(self, guild_id, include_has_left=False, include_settings=False) -> [int]:
        """Fetch all twitch channel ids that the guild is watching for clips"""
        if include_settings:
            if include_has_left:
                query = "select channel_id, alert_type, has_left, settings, trending_interval, is_game from guild_twitch_channel where guild_id = %s"
            else:
                query = "select channel_id, alert_type, settings, trending_interval from guild_twitch_channel where guild_id = %s"
        else:
            if include_has_left:
                query = "select channel_id, alert_type, has_left from guild_twitch_channel where guild_id = %s"
            else:
                query = "select channel_id, alert_type from guild_twitch_channel where guild_id = %s"
        h = await self.cnx.execute_query(query, values=guild_id)
        return h

    async def delete_from(self, table, column, which):
        # delete from guilds where guild_id = 759798762171662399
        update_guilds_query = f"delete from {table} where {column} = %s"
        await self.cnx.execute_query(update_guilds_query, values=[which])

    async def get_guild_clip_alert_chn(self, guild_id: int, channel_id: int, alert_type: int):
        q = "select discord_channel from guild_twitch_channel where "\
                                            f"guild_id = %s and channel_id = %s and alert_type = %s"
        return await self.cnx.execute_query(q, values=[guild_id, channel_id, alert_type], scaler=True)
