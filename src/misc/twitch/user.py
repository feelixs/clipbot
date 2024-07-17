from src.misc.twitch.api import TwitchAPI
from src.misc.twitch.clip import Clip
from datetime import datetime


class UserInfo:
    def __init__(self, name, id, api):
        self.username, self.id, self.api = name, id, api
        self.display_name = self.username

    async def get_broadcaster_clips(self, limit: int = 100, started_at: datetime = None, sort=True) -> [Clip]:
        """Given a broadcaster id, will return a json of clips based on limit and started_at
        :param limit max amount of clips to return
        :param started_at  only return clips created after this datetime
        :param sort sorts them by date if true"""
        if started_at is None:
            start = ""
        else:
            start = "&started_at=" + started_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        data = await self.api.get(url='https://api.twitch.tv/helix/clips?broadcaster_id=' + str(self.id) + '&first=' + str(limit) + start)
        data = data['data']
        clips = []
        [clips.append(Clip(c, self.api)) for c in data]
        if sort:
            clips.sort(key=lambda c: c.created_at)
        return clips


class User(UserInfo):
    def __init__(self, data, api: TwitchAPI, broadcaster=True):
        """Converts a provided user's json data from Twitch api into a Python object
        :param broadcaster when returned by search twitch returns a 'broadcaster', but when getting a user by id it returns a 'user'"""
        self.api = api
        self.data = data
        if data is None:
            super().__init__(None, None, api)
            self.login_name = None
            self.broadcaster_language = None
            self.display_name = None
            self.game_id = None
            self.broadcaster_id = None
            self.is_live = None
            self.tag_ids = None
            self.thumbnail_url = None
            self.title = None
            self.started_at = None
        else:
            super().__init__(data['display_name'], data['id'], self.api)
            self.display_name = data['display_name']
            self.broadcaster_id = data['id']
            if broadcaster:
                self.login_name = data['broadcaster_login']
                self.broadcaster_language = data['broadcaster_language']
                self.is_live = data['is_live']
                self.tag_ids = data['tag_ids']
                self.game_id = data['game_id']
                self.started_at = data['started_at']
                self.title = data['title']
                self.thumbnail_url = data['thumbnail_url']
            else:
                self.login_name = data['login']
                self.broadcaster_language, self.is_live, self.tag_ids, \
                self.game_id, self.started_at, self.title, self.thumbnail_url = None, None, None, None, None, None, None
