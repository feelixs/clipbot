class TooManyTriesError(Exception):
    """Exception raised when the maximum number of retries is exceeded."""
    pass


class ClipNotExists(Exception):
    pass


class BotRejoinedGuild(Exception):
    pass


class TwitchObjNotExists(Exception):
    pass


class RateLimitExceededError(Exception):
    def __init__(self, resets_when, *args):
        super().__init__(*args)
        self.resets_when = resets_when
