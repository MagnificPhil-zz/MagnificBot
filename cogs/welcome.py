import discord
from discord.ext import commands
from .utils.dataIO import dataIO, fileIO
from .utils import checks
from __main__ import settings
from collections import defaultdict
import os
import asyncio



default_greeting = "Bienvenue {0.mention} à {1.name}!"
default_settings = {"GREETING": default_greeting, "ON": False, "CHANNEL": None, "WHISPER" : False}
settings_path = "data/red/ownersettings.json"
class Welcome:
    """Accueil les nouveaux membres du serveur"""

    def __init__(self, bot):
        self.bot = bot
        settings = dataIO.load_json(settings_path)
        self.settings = defaultdict(lambda: default_settings.copy(), settings)
        #self.settings = fileIO("data/welcome/settings.json", "load")


    @commands.group(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def welcomeset(self, ctx):
        """Définit les paramètres de l'accueil"""
        server = ctx.message.server
        channels = server.channels
        if server.id not in self.settings:
            self.settings[server.id] = default_settings
            self.settings[server.id]["CHANNEL"] = server.default_channel.id
            self.settings[server.id]["CHANNEL_NAME"] = server.default_channel.name
        else:
            for channel in channels:
                if channel.id == self.settings[server.id]["CHANNEL"]:
                    self.settings[server.id]["CHANNEL_NAME"] = channel.name
        fileIO("data/welcome/settings.json","save",self.settings)
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            msg = "```"
            msg += "GREETING: {}\n".format(self.settings[server.id]["GREETING"])
            msg += "CHANNEL: #{}\n".format(self.get_welcome_channel(server)) 
            msg += "ON: {}\n".format(self.settings[server.id]["ON"]) 
            msg += "WHISPER: {}\n".format(self.settings[server.id]["WHISPER"])
            msg += "```"
            await self.bot.say(msg)


    @welcomeset.command(pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def greeting(self, ctx, *, format_msg):
        """Définit le format du message d'accueil.

        {0} représente la personne
        {1} représente le serveur

        Par défaut le message est définit sur : 
            Bienvenue {0.mention} à {1.name}!

        Explications:
            {0.mention} mentione la personne : "@machin"
            {0.name} remprésente son nom :"machin"
            {0.discriminator} représente le numéro associé : "#1234"
            {0.id} représente l'identifiant discord
            
            pour le serveur : {1} vous ne pouvez utiliser que :
            {1.name} et {.id}
        """
        server = ctx.message.server
        self.settings[server.id]["GREETING"] = format_msg
        fileIO("data/welcome/settings.json","save",self.settings)
        await self.bot.say("Welcome message set for the server.")
        await self.send_testing_msg(ctx)

    @welcomeset.command(pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def toggle(self, ctx):
        """Turns on/off welcoming new users to the server"""
        server = ctx.message.server
        self.settings[server.id]["ON"] = not self.settings[server.id]["ON"]
        if self.settings[server.id]["ON"]:
            await self.bot.say("I will now welcome new users to the server.")
            await self.send_testing_msg(ctx)
        else:
            await self.bot.say("I will no longer welcome new users.")
        fileIO("data/welcome/settings.json", "save", self.settings)

    @welcomeset.command(pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def channel(self, ctx, channel : discord.Channel=None): 
        """Définit le channel pour les messages d'accueil

        Si le channel n'est pas spécifié,
        le channel par défaut du serveur sera utilisé."""
        server = ctx.message.server
        if channel == None:
            channel = ctx.message.server.default_channel
        if not server.get_member(self.bot.user.id).permissions_in(channel).send_messages:
            await self.bot.say("Je n'ai pas les permissions d'envoyer un message à {0.mention}".format(channel))
            return
        self.settings[server.id]["CHANNEL"] = channel.id
        self.settings[server.id]["CHANNEL_NAME"] = channel.name
        fileIO("data/welcome/settings.json", "save", self.settings)
        channel = self.get_welcome_channel(server)
        await self.bot.send_message(channel,"Je vais maintenant envoyer les messages à {0.mention}".format(channel))
        await self.send_testing_msg(ctx)

    @welcomeset.command(pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def whisper(self, ctx, choice : str=None): 
        """Définit si oui ou non le message est envoyé en MP
        
        Options:
            off - Désactive les MP à l'utilisateur
            only - MP uniquement l'utilisateur, rien dans le channel d'accueil
            both - message d'accueil en MP et dans le channel d'accueil

        Si l'option n'est pas spécifiée, passe de 'off' à 'only'"""
        options = {"off": False, "only": True, "both": "BOTH"}
        server = ctx.message.server
        if choice == None:
            self.settings[server.id]["WHISPER"] = not self.settings[server.id]["WHISPER"]
        elif choice.lower() not in options:
            await send_cmd_help(ctx)
            return
        else:
            self.settings[server.id]["WHISPER"] = options[choice.lower()]
        fileIO("data/welcome/settings.json", "save", self.settings)
        channel = self.get_welcome_channel(server)
        if not self.settings[server.id]["WHISPER"]:
            await self.bot.say("I will no longer send DMs to new users")
        elif self.settings[server.id]["WHISPER"] == "BOTH":
            await self.bot.send_message(channel,"I will now send welcome messages to {0.mention} as well as to the new user in a DM".format(channel))
        else:
            await self.bot.send_message(channel,"I will now only send welcome messages to the new user as a DM".format(channel))
        await self.send_testing_msg(ctx)


    async def member_join(self, member):
        server = member.server
        if server.id not in self.settings:
            self.settings[server.id] = default_settings
            self.settings[server.id]["CHANNEL"] = server.default_channel.id
            fileIO("data/welcome/settings.json","save",self.settings)
        if not self.settings[server.id]["ON"]:
            return
        if server == None:
            print("Le serveur n'est pas définit.\n"
            "Message privé ou une nouvelle fonctionnalité de Discord ?..\n"
            "Quoi qu'il en soit il y a eu une ERREUR\n"
            "L'utilisateur concerné est {}#{}".format(member.name, member.discriminator))
            return
        channel = self.get_welcome_channel(server)
        if channel is None:
            print("welcome.py : \n"
                "Channel non trouvé : \n"
                "Il a sûrement été supprimé.\n "
                "Utilisateur qui a rejoint : {}#{}".format(member.name, member.discriminator))
            return
        if self.settings[server.id]["WHISPER"]:
            await self.bot.send_message(member, self.settings[server.id]["GREETING"].format(member, server))
        if self.settings[server.id]["WHISPER"] != True and self.speak_permissions(server):
            await self.bot.send_message(channel, self.settings[server.id]["GREETING"].format(member, server))
        else:
            print("Erreur de permissions. Utilisateur qui a rejoint: {0.name}".format(member))
            print("Le bot n'a pas les permissions pour envoyer un message sur {0.name} à #{1.name} channel".format(server,channel))


    def get_welcome_channel(self, server):
        try:
            return server.get_channel(self.settings[server.id]["CHANNEL"])
        except:
            return None

    def speak_permissions(self, server):
        channel = self.get_welcome_channel(server)
        if channel is None:
            return False
        return server.get_member(self.bot.user.id).permissions_in(channel).send_messages

    async def send_testing_msg(self, ctx):
        server = ctx.message.server
        channel = self.get_welcome_channel(server)
        if channel is None:
            await self.bot.send_message(ctx.message.channel, "Je ne trouve pas le channel spécifié.\n Il a dû être supprimé.")
            return
        await self.bot.send_message(ctx.message.channel, "`J'envoie un message de test à `{0.mention}".format(channel))
        if self.speak_permissions(server):
            if self.settings[server.id]["WHISPER"]:
                await self.bot.send_message(ctx.message.author, self.settings[server.id]["GREETING"].format(ctx.message.author,server))
            if self.settings[server.id]["WHISPER"] != True:
                await self.bot.send_message(channel, self.settings[server.id]["GREETING"].format(ctx.message.author,server))
        else: 
            await self.bot.send_message(ctx.message.channel,"Je n'ai pas les permissions pour envoyer un message à {0.mention}".format(channel))
        
    # def send_caselog(self, ctx, user, server):
        # bank = self.bot.get_cog('Economy').bank
        # if server is None:


def check_folders():
    if not os.path.exists("data/welcome"):
        print("Creating data/welcome folder...")
        os.makedirs("data/welcome")

def check_files():
    f = "data/welcome/settings.json"
    if not fileIO(f, "check"):
        print("Creating welcome settings.json...")
        fileIO(f, "save", {})
    else: #consistency check
        current = fileIO(f, "load")
        for k,v in current.items():
            if v.keys() != default_settings.keys():
                for key in default_settings.keys():
                    if key not in v.keys():
                        current[k][key] = default_settings[key]
                        print("Adding " + str(key) + " field to welcome settings.json")
        fileIO(f, "save", current)

def setup(bot):
    check_folders()
    check_files()
    n = Welcome(bot)
    bot.add_listener(n.member_join,"on_member_join")
    bot.add_cog(n)
