import discord
import asyncio


class TempCache:
    """
    This is how we avoid events such as ban and unban
    from triggering twice in the mod-log.
    Kinda hacky but functioning
    """

    def __init__(self, bot):
        self.bot = bot
        self._cache = []

    def add(self, user, server, action, seconds=5):
        tmp = (user.id, server.id, action)
        self._cache.append(tmp)

        async def delete_value():
            await asyncio.sleep(seconds)
            self._cache.remove(tmp)

        self.bot.loop.create_task(delete_value())

    def check(self, user, server, action):
        return (user.id, server.id, action) in self._cache