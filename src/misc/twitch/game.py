from src.misc.twitch.api import TwitchAPI
from src.misc.twitch.clip import Clip
from datetime import datetime
from src.misc.twitch import UserInfo
from src.misc.errors import TwitchObjNotExists


class Game(UserInfo):
    def __init__(self, id: int, api: TwitchAPI, name=None):
        """If data = int, pull game data from api
            if data is dict, then it's assumed to be the game's api data"""
        self.api = api
        self.id = id
        if name is None:
            super().__init__(None, id, api)
            self.data, self.name, self.thumbnail_url, self.igdb_id = None, None, None, None
        else:
            super().__init__(name, id, api)
            self.name = name
            self.data, self.thumbnail_url, self.igdb_id = None, None, None

    async def fetch(self):
        """ call this after each instantiation
        If we already have the game name and id, we don't need to fetch anything from twitch API"""
        if self.name is None:
            return await self._from_id()
        return self

    async def _from_id(self):
        try:
            j = await self.api.get(url='https://api.twitch.tv/helix/games?id=' + str(self.id))
            self.data = j['data'][0]
        except:
            raise TwitchObjNotExists
        return await self._from_data()

    async def _from_data(self):
        d = self.data
        self.id, self.name, self.thumbnail_url, self.igdb_id = d['id'], d['name'], d['box_art_url'], d['igdb_id']
        self.username = self.name
        return self

    async def get_broadcaster_clips(self, limit: int = 100, started_at: datetime = None, sort=True) -> [Clip]:
        """Given a game id, will return a json of clips based on limit and started_at
        :param limit max amount of clips to return
        :param started_at  only return clips created after this datetime
        :param sort sorts them by date if true"""
        if started_at is None:
            start = ""
        else:
            start = "&started_at=" + started_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        data = await self.api.get(url='https://api.twitch.tv/helix/clips?game_id=' + str(self.id) + '&first=' + str(limit) + start)
        data = data['data']
        clips = []
        [clips.append(Clip(c, self.api)) for c in data]
        if sort:
            clips.sort(key=lambda c: c.created_at)
        return clips
