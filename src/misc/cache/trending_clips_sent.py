from interactions.models.discord import Guild
from src.misc.twitch import Clip
from typing import Union
from time import time, sleep


class TrendingClipCache:
    def __init__(self, max_len: int = 100):
        self._sent_clips = {}  # {'...': [('clip_id', timestamp_added_to_cache), ...]}
        self._MAX_LEN = max_len

    def add(self, guild: Union[Guild, int], channel: int, alert_type: int, clip: Union[Clip, str]):
        if isinstance(guild, Guild):
            guild = guild.id
        if isinstance(clip, Clip):
            clip = clip.id
        if f'{guild}-{channel}-{alert_type}' not in self._sent_clips:
            self._sent_clips[f'{guild}-{channel}-{alert_type}'] = []
        self._sent_clips[f'{guild}-{channel}-{alert_type}'].append((clip, time()))

    def _getvals(self, guild: Union[Guild, int], channel: int, alert_type: int) -> [(str, float), ...]:
        # raises KeyError it doesn't exist
        # returns all clips and timestamps for the guild-channel-type pair
        if isinstance(guild, Guild):
            guild = guild.id
        return self._sent_clips[f'{guild}-{channel}-{alert_type}']

    def _gettime(self, guild: Union[Guild, int], channel: int, alert_type: int, clip: Union[Clip, str]) -> float:
        # raises KeyError it doesn't exist
        # returns the timestamp of when the clip added to cache for the guild-channel-type pair
        if isinstance(guild, Guild):
            guild = guild.id
        if isinstance(clip, Clip):
            clip = clip.id
        try:
            at = self._sent_clips[f'{guild}-{channel}-{alert_type}']
            allclips, alltimes = [], []
            [(allclips.append(v[0]), alltimes.append(v[1])) for v in at]
            if clip in allclips:
                return alltimes[allclips.index(clip)]
            else:
                raise KeyError  # the clip doesn't exist for this guild-channel-type pair
        except KeyError:
            raise  # just for readability

    def _del(self, guild: Union[Guild, int], channel: int, alert_type: int, clip: Union[Clip, str]) -> bool:
        # returns if the clip existed
        if isinstance(guild, Guild):
            guild = guild.id
        if isinstance(clip, Clip):
            clip = clip.id
        try:
            list_without_removed = self._sent_clips[f'{guild}-{channel}-{alert_type}']
        except KeyError:
            return False
        temp = []
        e = False
        for c in list_without_removed:
            if c[0] != clip:
                temp.append(c)
            else:
                e = True
        self._sent_clips[f'{guild}-{channel}-{alert_type}'] = temp
        return e

    def _del_bytimestamp(self, what: str, ts: float):
        """:param what the key at which to check for & delete by the timestamp
        :param ts the timestamp to look for"""
        at: [(str, float), ...] = self._sent_clips[what]
        temp = []
        for val in at:
            if val[1] != ts:
                temp.append(val)
        self._sent_clips[what] = temp

    def exists(self, guild: Union[Guild, int], channel: int, alert_type: int, clip: Union[Clip, str]):
        """does the specified clip exist for the guild-channel-type pair?"""
        # returns if the clip exists
        try:
            if isinstance(guild, Guild):
                guild = guild.id
            if isinstance(clip, Clip):
                clip = clip.id
            for c in self._sent_clips[f'{guild}-{channel}-{alert_type}']:
                if c[0] == clip:
                    return True
        except KeyError:
            return False
        return False

    def trim_len(self, max_len: int = None):
        # remove excess values
        if max_len is None:
            max_len = self._MAX_LEN
        for pair in self._sent_clips:
            while len(self._sent_clips[pair]) > max_len:
                timestamps = [v[1] for v in self._sent_clips[pair]]
                m = min(timestamps)
                self._del_bytimestamp(pair, m)


if __name__ == "__main__":
    p = TrendingClipCache(1)
    p.add(0, 0, 0, "123")
    sleep(1)
    p.add(0, 0, 0, "456")
    sleep(1)
    p.add(1, 1, 1, "222")
    print(p.__dict__)
    a =p._gettime(0, 0, 0, "123")
    print(a)
    print(p._gettime(0, 0, 0, "456"))
    print(p.exists(0, 0, 0, "123"))
    p.trim_len()
    print(p.__dict__)
