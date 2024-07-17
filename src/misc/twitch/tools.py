from src.misc.twitch.api import TwitchAPI
from src.misc.twitch import User, Clip
from typing import Union, Optional
from asyncio import gather
from src.misc.errors import TwitchObjNotExists


class TwitchTools:
    def __init__(self, api: TwitchAPI):
        self.api = api

    async def find_user(self, query: Optional[str], id: int = None) -> User:
        """Given a Twitch username query, return a User object if an exact match is found (non case-sensitive)"""
        if id is None:
            data = await self.api.get(url='https://api.twitch.tv/helix/search/channels?query=' + str(query))
        elif query is None:
            """Search by id, if given"""
            data = await self.api.get(url=f'https://api.twitch.tv/helix/users?id={id}')
        else:
            # both are None?
            raise TwitchObjNotExists
        for usr in data['data']:
            if query is not None:
                if str(usr['display_name']).replace(" ", "").lower() == str(query).lower():  # .replace() takes out spaces - some names in twitch api have a space afterwards which messes up the bot
                    return User(usr, api=self.api)
            else:
                if str(usr['id']) == str(id):
                    return User(usr, api=self.api, broadcaster=False)
        raise TwitchObjNotExists

    @staticmethod
    def parse_clip_url(url: str) -> str:
        if "m.twitch.tv" in url:
            # convert mobile link to pc link
            url = url.replace("https://m.", "https://clips.").replace("/clip/", "/").split("?")[0]
        slug = str(url).split('/')[-1]
        if "?" in slug:
            slug = slug.split('?')[0]
        return slug

    async def get_clip(self, url: str) -> Optional[Clip]:
        slug = self.parse_clip_url(url)
        info = await self.api.get("https://api.twitch.tv/helix/clips?id=" + slug)
        try:
            return Clip(info['data'][0], self.api)
        except IndexError:
            return None

    async def get_clip_by_id(self, id: str) -> Optional[Clip]:
        info = await self.api.get("https://api.twitch.tv/helix/clips?id=" + id)
        try:
            return Clip(info['data'][0], self.api)
        except IndexError:
            return None

    async def get_game_name(self, game_id: Union[int, str]) -> str:
        """Convert Twitch game id into the game's actual name"""
        try:
            j = await self.api.get(url='https://api.twitch.tv/helix/games?id=' + str(game_id))
            return j['data'][0]
        except:
            raise TwitchObjNotExists

    async def get_is_live(self, user: str) -> str:
        return await (await self.find_user(user)).is_live

    async def get_title(self, user: str) -> str:
        return await (await self.find_user(user)).title

    async def check_live(self, users: [str]) -> [str]:
        """Given a list of Twitch usernames, return a boolean list of live statuses"""
        live_statuses = await gather(*[self.get_is_live(user) for user in users])
        return live_statuses

    async def get_titles(self, users: [str]) -> [str]:
        """Given a list of Twitch usernames, return a list of their stream titles"""
        titles = await gather(*[self.get_title(user) for user in users])
        return titles

    async def get_most_recent_vid(self, user_query):
        """Given a Twitch username, return their most recent VOD"""
        user = await self.find_user(user_query)
        res = await self.api.get('https://api.twitch.tv/helix/videos?user_id=' + user.id + "&sort=time&first=1")
        return res['data'][-1]
