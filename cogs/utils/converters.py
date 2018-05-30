from discord.ext.commands.converter import IDConverter
from discord.ext.commands.errors import BadArgument
import re



# Cela aurait pu être importé mais comme c'est interne c'est plus sûr
# de l'obtenir ici
def _get_from_servers(bot, getter, argument):
    result = None
    for server in bot.servers:
        result = getattr(server, getter)(argument)
        if result:
            return result
    return result


class GlobalUser(IDConverter):
    """
    Ceci est une copie (presque) directe du convertisseur Member de discord.py
    La principale différence est que si la commande est émise dans un serveur,
    il tentera d'abord d'obtenir l'utilisateur de ce serveur et en cas d'échec, il 
    tentera de le pêcher à partir du pool global
    """
    def convert(self):
        message = self.ctx.message
        bot = self.ctx.bot
        match = self._get_id_match() or re.match(r'<@!?([0-9]+)>$', self.argument)
        server = message.server
        result = None
        if match is None:
            # pas une mention...
            if server:
                result = server.get_member_named(self.argument)
            if result is None:
                result = _get_from_servers(bot, 'get_member_named', self.argument)
        else:
            user_id = match.group(1)
            if server:
                result = server.get_member(user_id)
            if result is None:
                result = _get_from_servers(bot, 'get_member', user_id)

        if result is None:
            raise BadArgument('Utilisateur "{}" non trouvé'.format(self.argument))

        return result
