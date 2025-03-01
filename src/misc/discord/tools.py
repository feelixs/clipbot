from interactions import SlashContext, TYPE_MESSAGEABLE_CHANNEL, Embed, Button, ButtonStyle, Guild
from interactions.models.discord import Message
from src.misc.twitch import TwitchAPI, TwitchTools, UserInfo, User, Clip
from src.env import TwitchCreds
from src.misc.errors import TwitchObjNotExists
from src.misc.database import Database
import aiohttp


class DiscordTools:
    def __init__(self, client, db: Database, logger, twitchtools=None, log_path=None, log_name=None):
        self.bot = client
        self.logger = logger
        self.DB = db
        if twitchtools is None:
            self.TWITCH_API = TwitchAPI(key=TwitchCreds.id, secret=TwitchCreds.secret, logger=logger, log_path=log_path, log_name=log_name)
            self.TWITCH_TOOLS = TwitchTools(self.TWITCH_API)
        else:
            self.TWITCH_TOOLS = twitchtools
            self.TWITCH_API = twitchtools.api

    async def get_twitch_game_name(self, id:  int) -> str:
        try:
            name = await self.TWITCH_TOOLS.get_game_name(id)
            stored_game = UserInfo(name['name'], id, self.TWITCH_API)
        except TwitchObjNotExists:
            return "Not found"
        return stored_game.username  # this is actually the game's name in this case

    @staticmethod
    def get_role(role_num: int):
        everyone = (role_num == 1)
        here = (role_num == 2)
        if role_num is not None and role_num != 0:
            if everyone:
                return "@everyone"
            elif here:
                return "@here"
            else:
                return f"<@&{role_num}>"
        else:
            return ""

    @staticmethod
    def get_last_lines(string):
        if len(string) > 2000:
            string = string[-1980:]  # the last 1980 characters
        string = string.split("\n")
        fuldate = ""
        for c in string[1]:  # this line guaranteed to not be messed up from the trim (the line[0] will be messed up)
            fuldate += c
            if c == "]":
                break
        string[0] = fuldate
        string = "\n".join(string)
        return string

    @staticmethod
    def format_log(string):
        """
        [2023-04-13 00:43:30]  hesmen: BatChest "BATCHEST" BatChest "BATCHEST" BatChest "BATCHEST" BatChest "BATCHEST" BatChest "BATCHEST" BatChest "BATCHEST"
        [2023-04-13 00:43:30]  hesmen has been timed out for 30 seconds
        [2023-04-13 00:49:33]  hesmen: BatChest "BATCHEST" BatChest "BATCHEST" BatChest "BATCHEST" BatChest "BATCHEST"
        [2023-04-13 00:49:33]  hesmen has been timed out for 30 seconds
        [2023-04-14 00:50:18]  hesmen: h
        [2023-04-14 00:50:32]  hesmen: BBoomer RAVE Fire

        becomes

        [2023-04-13 ]
        00:43:30 hesmen: BatChest "BATCHEST" BatChest "BATCHEST" BatChest "BATCHEST" BatChest "BATCHEST" BatChest "BATCHEST" BatChest "BATCHEST"
        00:43:30  hesmen has been timed out for 30 seconds
        00:49:33  hesmen: BatChest "BATCHEST" BatChest "BATCHEST" BatChest "BATCHEST" BatChest "BATCHEST"
        00:49:33 hesmen has been timed out for 30 seconds

        [2023-04-13]
        00:50:18 hesmen: h
        00:50:32 hesmen: BBoomer RAVE Fire
        """
        formatted_logs = ""
        eachdate = ""
        for ind, line in enumerate(string.split("\n")):
            if ind == 0:
                continue
            if line.strip():
                tmst, txt = line.split(" ", 1)

                if eachdate != tmst.split(" ")[0]:
                    eachdate = tmst.split(" ")[0]
                    formatted_logs += f"\n{eachdate}]\n"
                actime, txt = txt.split(']', 1)
                for c in range(len(txt)):
                    if txt[c] == "#":
                        while txt[c] != " ":
                            c += 1
                        txt = txt[:c] + "`" + txt[c:]
                        break
                formatted_logs += f"`{actime} {txt}\n"
        return formatted_logs

    async def generate_twitch_log(self, ctx: SlashContext, user: str, twitch_channel: str, year: int, month: int) -> Message:
        try:
            async with aiohttp.ClientSession() as session:
                if year is not None and month is not None:
                    async with session.get(f"https://logs.ivr.fi/channel/{twitch_channel}/user/{user}/{year}/{month}") as resp:
                        logs_output = await resp.text()
                elif year is None and month is None:
                    async with session.get(f"https://logs.ivr.fi/channel/{twitch_channel}/user/{user}") as resp:
                        logs_output = await resp.text()
                else:
                    return await ctx.send("An error occurred: year & month must be either both filled out, or none filled out", ephemeral=True)
                if logs_output.count("\n") == 0:
                    if "[" in logs_output:
                        return await ctx.send(logs_output)
                    else:
                        return await ctx.send(f'for user `{user}` on Twitch channel `{twitch_channel}`:\n`' + logs_output + '`')
                else:
                    logs_output = self.get_last_lines(logs_output)
                    logs_output = self.format_log(logs_output)
                    if logs_output == "":
                        return await ctx.send(f"No logs available for `{user}` in Twitch channel `{twitch_channel}`")
                    else:
                        return await ctx.send(logs_output)
        except:
            return await ctx.send("An error occurred retrieving Twitch logs, please contact out support team if the issue persists", ephemeral=True)

    async def create_clip_embed(self, clip: Clip, description: str, add_img: bool = True, refresh_views=False):
        this_embed = Embed(title=f"**\u200b{clip.title}**", description=description)
        this_embed.add_field(name="Created", value=f"<t:{int(clip.created_at.timestamp())}>", inline=True)
        this_embed.add_field(name="Creator", value=f"[\u200b{clip.creator_name}](https://twitch.tv/{clip.creator_name})", inline=True)
        this_embed.add_field(name="Duration", value=f"{clip.duration}s", inline=True)
        gname = await self.get_twitch_game_name(clip.game_id)
        this_embed.add_field(name="Playing", value=gname, inline=True)
        if refresh_views:
            v = await clip.get_views()
        else:
            v = clip.views
        this_embed.add_field(name="Views", value=v, inline=True)
        if add_img:
            this_embed.set_image(clip.thumbnail_url)
        return this_embed

    @staticmethod
    def create_clip_msg(clip: Clip, description: str):
        return description + f" created by `{clip.creator_name}`: {clip.url}\n"
