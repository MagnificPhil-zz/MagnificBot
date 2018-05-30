import discord
import os
import re
import logging
import asyncio

from datetime import datetime
from collections import deque, defaultdict, OrderedDict
from random import choice

from discord.ext import commands
from __main__ import send_cmd_help, settings
from cogs.utils.dataIO import dataIO
from cogs.utils import checks
from cogs.utils import cases
from cogs.utils import tempcache
from cogs.utils.chat_formatting import escape_mass_mentions, box, pagify

sel_log_path = "data/mod/sel.log"

class Sel:
    """Recruiters tools."""
    _ignore_list_path = "data/mod/ignorelist.json"
    _filter_path = "data/mod/filter.json"
    _ownersettings_path = "data/red/ownersettings.json"
    _perms_cache_path = "data/mod/perms_cache.json"
    _past_names_path = "data/mod/past_names.json"
    _past_nicknames_path = "data/mod/past_nicknames.json"
    _reminders_path = "data/remindme/reminders.json"
    _sel_settings_path = "data/mod/sel_settings.json"


    def __init__(self, bot):
        self.bot = bot
        self.ignore_list = dataIO.load_json(self._ignore_list_path)
        self.filter = dataIO.load_json(self._filter_path)
        self.past_names = dataIO.load_json(self._past_names_path)
        self.past_nicknames = dataIO.load_json(self._past_nicknames_path)
        self.settings = dataIO.load_json(self._ownersettings_path)
        self.cases = cases.Cases(self.bot)
        self.cache = OrderedDict()
        self.temp_cache = tempcache.TempCache(self.bot)
        perms_cache = dataIO.load_json(self._perms_cache_path)
        self._perms_cache = defaultdict(dict, perms_cache)
        self.sel_settings = dataIO.load_json(self._sel_settings_path)

 ### GROUP INFO START
    @commands.group(name="infos", no_pm=True, pass_context=True)
    @checks.sel_or_permissions()
    async def infos(self, ctx):
        """Groupe: Donne des infos"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @infos.command(name="user", pass_context=True, no_pm=True)
    async def userinfo(self, ctx, *, user: discord.Member=None):
        """Montre les informations d'un utilisateur"""
        author = ctx.message.author
        server = ctx.message.server

        if not user:
            user = author

        roles = [x.name for x in user.roles if x.name != "@everyone"]

        since_created = (ctx.message.timestamp - user.created_at).days
        since_joined = (ctx.message.timestamp - user.joined_at).days
        user_joined = user.joined_at.strftime("%d %b %Y %H:%M")
        user_created = user.created_at.strftime("%d %b %Y %H:%M")
        member_number = sorted(server.members,
                               key=lambda m: m.joined_at).index(user) + 1

        created_on = "Le {}\n(Il y a {} jours)".format(user_created, since_created)
        joined_on = "Le {}\n(Il y a {} jours)".format(user_joined, since_joined)

        game = "Chill {}".format(user.status)

        if user.game is None:
            pass
        elif user.game.url is None:
            game = "Joue {}".format(user.game)
        else:
            game = "Stream: [{}]({})".format(user.game, user.game.url)

        if roles:
            roles = sorted(roles, key=[x.name for x in server.role_hierarchy
                                       if x.name != "@everyone"].index)
            roles = ", ".join(roles)
        else:
            roles = "None"

        data = discord.Embed(description=game, colour=user.colour)
        data.add_field(name="A rejoint Discord le", value=created_on)
        data.add_field(name="A rejoint ce serveur le", value=joined_on)
        data.add_field(name="Rôles", value=roles, inline=False)
        data.set_footer(text="Membre #{} | ID:{}"
                             "".format(member_number, user.id))

        name = str(user)
        name = " ~ ".join((name, user.nick)) if user.nick else name

        if user.avatar_url:
            data.set_author(name=name, url=user.avatar_url)
            data.set_thumbnail(url=user.avatar_url)
        else:
            data.set_author(name=name)

        try:
            log_msg = "{}({}) a demandé des infos sur {}({})".format(author.name, author.id, user.name,
                                                                     user.id, )
            # case_number = await self.cases.new_case(server,
            #                     action="KICK",
            #                     mod=author,
            #                     user=user,
            #                     reason=reason)
            # log_msg = "CASE : " + str(case_number) + " --> " + log_msg
            logger.info(log_msg)
            await self.bot.say(embed=data, delete_after=self.settings[server.id]["delete_delay"])
        except discord.HTTPException:
            await self.bot.say("J'ai besoin du droit `Intégrer des liens` "
                               "pour envoyer ça", delete_after=self.settings[server.id]["delete_delay"])

    @infos.command(name="srv", pass_context=True, no_pm=True)
    async def infosrv(self, ctx):
        """Montre les informations du serveur"""
        server = ctx.message.server
        author = ctx.message.author
        online = len([m.status for m in server.members
                      if m.status == discord.Status.online or
                      m.status == discord.Status.idle])
        total_users = len(server.members)
        text_channels = len([x for x in server.channels
                             if x.type == discord.ChannelType.text])
        voice_channels = len([x for x in server.channels
                              if x.type == discord.ChannelType.voice])
        passed = (ctx.message.timestamp - server.created_at).days
        created_at = ("Depuis {}. Cela fait {} jours!"
                      "".format(server.created_at.strftime("%d %b %Y %H:%M"),
                                passed))

        colour = ''.join([choice('0123456789ABCDEF') for x in range(6)])
        colour = int(colour, 16)

        data = discord.Embed(
            description=created_at,
            colour=discord.Colour(value=colour))
        data.add_field(name="Region", value=str(server.region))
        data.add_field(name="Users", value="{}/{}".format(online, total_users))
        data.add_field(name="Text Channels", value=text_channels)
        data.add_field(name="Voice Channels", value=voice_channels)
        data.add_field(name="Roles", value=len(server.roles))
        data.add_field(name="Owner", value=str(server.owner))
        data.set_footer(text="Server ID: " + server.id)

        if server.icon_url:
            data.set_author(name=server.name, url=server.icon_url)
            data.set_thumbnail(url=server.icon_url)
        else:
            data.set_author(name=server.name)

        try:
            log_msg = "{}({}) a demandé des infos sur {}({})".format(author.name, author.id, server.name,
                                                                     server.id, )
            await self.bot.say(embed=data, delete_after=self.settings[server.id]["delete_delay"])
            logger.info(log_msg)
        except discord.HTTPException:
            await self.bot.say("J'ai besoin de la permission `Embed links` "
                               "pour répondre", delete_after=self.settings[server.id]["delete_delay"])

    @infos.command(pass_context=True, no_pm=True)
    async def names(self, ctx, user : discord.Member):
        """Montre les anciens noms/surnoms d'un user"""
        server = user.server
        author = ctx.message.author
        names = self.past_names[user.id] if user.id in self.past_names else None
        try:
            nicks = self.past_nicknames[server.id][user.id]
            nicks = [escape_mass_mentions(nick) for nick in nicks]
        except:
            nicks = None
        msg = ""
        if names:
            names = [escape_mass_mentions(name) for name in names]
            msg += "**Les 20 derniers noms**:\n"
            msg += ", ".join(names)
        if nicks:
            if msg:
                msg += "\n\n"
            msg += "**Les 20 derniers surnoms**:\n"
            msg += ", ".join(nicks)
        log_msg = "{}({}) a demandé des infos sur les noms et surnoms de {}({})".format(author.name, author.id, user.name,
                                                                     user.id, )
        if msg:
            
            await self.bot.say(msg, delete_after=self.settings[server.id]["delete_delay"])
        else:
            await self.bot.say("Ce user n'a aucun nom passé enregistré ou "
                               "surnom changé.", delete_after=self.settings[server.id]["delete_delay"])
        logger.info(log_msg)
 ### GROUP INFO END

 ### GROUP RECRUTE START
    @commands.group(name="select", no_pm=True, pass_context=True)
    @checks.sel_or_permissions()
    async def _recrute(self, ctx):
        """Groupe: Gestion des candidatures (en cours)"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_recrute.command(pass_context=True, name='question')
    async def _question(self, ctx, question: str, *reponses):
        """Ajoute une question pour le recrutement.

        question: doit être entre-guillemets si il y a une espace.
        reponses: pas obligatoire. Pour fournir l'ensemble des reponses possibles 
                  il suffit de les séparer d'un espace"""
        server = ctx.message.server
        author = ctx.message.author
        if server.id not in self.sel_settings:
            self.sel_settings[server.id] = dict()
        if question is None:
            await send_cmd_help(ctx)
            return
        nb_quest = len(self.sel_settings[server.id]["questions"]) + 1
        question = {
            "created": datetime.utcnow().timestamp(),
            "message":  question,
            "reponses": reponses,
            "author": str(author) if author is not None else None,
            "author_id": author.id if author is not None else None,
            #"until": until.timestamp() if until else None,
        }
        #print(type(reponses), reponses)
        self.sel_settings[server.id]["questions"][str(nb_quest)] = question
        dataIO.save_json(self._sel_settings_path, self.sel_settings)
        await self.bot.say("La question a été enregistrée.", delete_after = self.settings[server.id]["delete_delay"])

    @_recrute.command(pass_context=True, name='liste')
    async def _list_question(self, ctx, question: str, *reponses):
        pass
        
    def register_meeting():
        pass

    def informations_candidat():
        pass

    def test_candidat():
        pass

    def sauvegarde_test_results():
        pass

    def sauvegarde_CR_examen():
        pass

    def donne_un_avis():
        pass

    def passe_a_moderation():
        pass

    def vote_moderation():
        pass

    def vote_admins():
        pass

    def tranche_choix():
        pass

    def retex_sel_mod_admin():
        pass

    def informe_adj_mod_sel():
        pass

    def Informe_candidat():
        pass

    def donne_role():
        pass

    def donne_regles():
        pass
 ### GROUP RECRUTE END

 ### GROUP WRITE START
    @commands.group(name="send", no_pm=True, pass_context=True)
    @checks.sel_or_permissions()
    async def _write(self, ctx):
        """Groupe: Envoyer des messages spéciaux"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_write.command(pass_context=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def to_owner(self, ctx, *, message: str):
        """Envoyer un message au proprietaire"""
        if self.bot.settings.owner is None:
            await self.bot.say("Il n'y a pas de proprietaire defini.")
            return
        server = ctx.message.server
        owner = discord.utils.get(self.bot.get_all_members(),
                                  id=self.bot.settings.owner)
        author = ctx.message.author
        footer = "User ID: " + author.id

        if ctx.message.server is None:
            source = "via MP"
        else:
            source = "de {}".format(server)
            footer += " | Serveur ID: " + server.id

        if isinstance(author, discord.Member):
            colour = author.colour
        else:
            colour = discord.Colour.red()

        description = "Envoyé par {} {}".format(author, source)

        e = discord.Embed(colour=colour, description=message)
        if author.avatar_url:
            e.set_author(name=description, icon_url=author.avatar_url)
        else:
            e.set_author(name=description)
        e.set_footer(text=footer)

        try:
            await self.bot.send_message(owner, embed=e)
        except discord.InvalidArgument:
            await self.bot.say("Je ne peux envoyer ce message, je ne trouve pas"
                               " mon propriétaire... *sigh*", delete_after=self.settings[server.id]["delete_delay"])
        except discord.HTTPException:
            await self.bot.say("ce message est trop long.", delete_after=self.settings[server.id]["delete_delay"])
        except:
            await self.bot.say("je ne peux pas livrer ce message. Désolé.", delete_after=self.settings[server.id]["delete_delay"])
        else:
            await self.bot.say("Le message a été envoyé.", delete_after=self.settings[server.id]["delete_delay"])

    @_write.command(pass_context=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def claim(self, ctx, *, message: str):
        """Faire une réclamation"""
        if message != None:
            await self.write_to_claim(ctx, 'Réclamation', message)
        else:
            await send_cmd_help(ctx)

    @_write.command(pass_context=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def suggest(self, ctx, *, message: str):
        """Suggérer une idée"""
        if message != None:
            await self.write_to_claim(ctx, 'Idée ou Suggestion', message)
        else:
            await send_cmd_help(ctx)
 ### GROUP WRITE END

    @commands.group(name="postuler",pass_context=True)
    async def _candidat(self, ctx):
        """Groupe: Faire une candidature (en cours)"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_candidat.command(pass_context=True, name='guilde')
    async def _guilde(self, ctx):
        """Faire une candidature pour entrer dans la guilde"""
        server = ctx.message.server
        author = ctx.message.author
        await self.bot.say("EN COURS !!!!", delete_after = self.settings[server.id]["delete_delay"])

    @_candidat.command(pass_context=True, name='esport')
    async def _sport(self, ctx):
        """Faire une candidature pour devenir compétiteur"""
        server = ctx.message.server
        author = ctx.message.author
        await self.bot.say("EN COURS !!!!", delete_after = self.settings[server.id]["delete_delay"])

    async def write_to_claim(self, ctx, titre: str, message: str):
        server = ctx.message.server
        author = ctx.message.author
        footer = "User ID: " + author.id

        if ctx.message.server is None:
            source = "via MP"
        else:
            source = "de {}".format(server)
            footer += " | Serveur ID: " + server.id

        if isinstance(author, discord.Member):
            colour = author.colour
        else:
            colour = discord.Colour.red()

        whosendit = "Envoyé par {} {}".format(author, source)
        e = discord.Embed(title=titre, colour=colour, description=message)
        if author.avatar_url:
            e.set_author(name=whosendit, icon_url=author.avatar_url)
        else:
            e.set_author(name=whosendit)
        e.set_footer(text=footer)
        to_channel_id = self.settings[server.id]["idea-claim"]
        if to_channel_id:
            to_channel = discord.Client.get_channel(self.bot, to_channel_id)
            try:
                await self.bot.send_message(to_channel, embed=e)
            except discord.InvalidArgument:
                await self.bot.say("Je ne peux envoyer ce message, je ne trouve pas"
                                " le salon " + self.settings[server.id]["idea-claim-name"] + "... oups!", delete_after=self.settings[server.id]["delete_delay"])
            except discord.HTTPException:
                await self.bot.say("ce message est trop long.", delete_after=self.settings[server.id]["delete_delay"])
            except:
                await self.bot.say("je ne peux pas livrer ce message. Désolé.", delete_after=self.settings[server.id]["delete_delay"])
            else:
                await self.bot.say("Le message a été envoyé.", delete_after=self.settings[server.id]["delete_delay"])
        else:
            await self.bot.say("Je ne peux envoyer ce message, le salon n'est pas défini.\n"
                               "Demander au propriétaire d'en définir un.", delete_after=self.settings[server.id]["delete_delay"])

    async def check_names(self, before, after):
        if before.name != after.name:
            if before.id not in self.past_names:
                self.past_names[before.id] = [after.name]
            else:
                if after.name not in self.past_names[before.id]:
                    names = deque(self.past_names[before.id], maxlen=20)
                    names.append(after.name)
                    self.past_names[before.id] = list(names)
            dataIO.save_json(self._past_names_path , self.past_names)

        if before.nick != after.nick and after.nick is not None:
            server = before.server
            if server.id not in self.past_nicknames:
                self.past_nicknames[server.id] = {}
            if before.id in self.past_nicknames[server.id]:
                nicks = deque(self.past_nicknames[server.id][before.id],
                              maxlen=20)
            else:
                nicks = []
            if after.nick not in nicks:
                nicks.append(after.nick)
                self.past_nicknames[server.id][before.id] = list(nicks)
                dataIO.save_json(self._past_nicknames_path ,
                                 self.past_nicknames)

def check_folders():
    folders = ("data", "data/mod/")
    for folder in folders:
        if not os.path.exists(folder):
            print("Création du dossier " + folder + " ...")
            os.makedirs(folder)

def check_files():
    ignore_list = {"SERVERS": [], "CHANNELS": []}

    files = {
        "ignorelist.json"     : ignore_list,
        "filter.json"         : {},
        "past_names.json"     : {},
        "past_nicknames.json" : {},
        "settings.json"       : {},
        "perms_cache.json"    : {},
        "sel_settings.json"   : {}
    }

    for filename, value in files.items():
        if not os.path.isfile("data/mod/{}".format(filename)):
            print("Création du fichier vide {}".format(filename))
            dataIO.save_json("data/mod/{}".format(filename), value)

def setup(bot):
    global logger
    check_folders()
    check_files()
    logger = logging.getLogger("sel")
    # Prevents the logger from being loaded again in case of module reload
    if logger.level == 0:
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(
            filename=sel_log_path, encoding='utf-8', mode='a')
        handler.setFormatter(
            logging.Formatter('%(asctime)s %(message)s', datefmt="[%d/%m/%Y %H:%M]"))
        logger.addHandler(handler)
    n = Sel(bot)
    bot.add_listener(n.check_names, "on_member_update")
    bot.add_cog(n)
