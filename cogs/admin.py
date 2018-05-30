import discord
import os
import re
import logging
import asyncio

from datetime import datetime
from collections import deque, defaultdict, OrderedDict

from discord.ext import commands
from __main__ import send_cmd_help, settings
from cogs.utils import checks
from cogs.utils import cases
from cogs.utils import tempcache
from cogs.utils.dataIO import dataIO
from cogs.utils.chat_formatting import escape_mass_mentions, box, pagify

admin_log_path = "data/mod/admin.log"

class Admin:
    """Outils d'administration."""
    _ignore_list_path = "data/mod/ignorelist.json"
    _filter_path = "data/mod/filter.json"
    _ownersettings_path = "data/red/ownersettings.json"
    _perms_cache_path = "data/mod/perms_cache.json"
    _past_names_path = "data/mod/past_names.json"
    _past_nicknames_path = "data/mod/past_nicknames.json"
    #_reminders_path = "data/remindme/reminders.json"

    def __init__(self, bot):
        self.bot = bot
        self.ignore_list = dataIO.load_json(self._ignore_list_path)
        self.filter = dataIO.load_json(self._filter_path)
        self.past_names = dataIO.load_json(self._past_names_path)
        self.past_nicknames = dataIO.load_json(self._past_nicknames_path)
        self.settings = dataIO.load_json(self._ownersettings_path)
        self.cache = OrderedDict()
        self.temp_cache = tempcache.TempCache(self.bot)
        perms_cache = dataIO.load_json(self._perms_cache_path)
        self._perms_cache = defaultdict(dict, perms_cache)
        self.cases = cases.Cases(self.bot)

 ### GROUPE ROLES START
    @commands.group(name="roles", no_pm=True, pass_context=True)
    @checks.admin_or_permissions()#@checks.admin_or_permissions(manage_roles=True)
    async def editrole(self, ctx):
        """Groupe: Paramètres des rôles"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @editrole.command(aliases=["color"], pass_context=True)
    async def colour(self, ctx, role: discord.Role, value: discord.Colour):
        """Change la couleur d'un rôle

        Utilisez des guillements si le nom du rôle contient des espaces.
        Les couleurs doivent être au format hexadecimal.
        \"http://www.w3schools.com/colors/colors_picker.asp\"
        Exemples:
        !editrole colour \"The Transistor\" #ff0000
        !editrole colour Test #ff9900"""
        author = ctx.message.author
        server = ctx.message.server
        try:
            await self.bot.edit_role(ctx.message.server, role, color=value)
            logger.info("{}({}) changed the colour of role '{}'".format(
                author.name, author.id, role.name))
            await self.bot.say("Fait.", delete_after=self.settings[server.id]["delete_delay"])
        except discord.Forbidden:
            await self.bot.say("J'ai d'abord besoin de permissions pour gérer les rôles.", delete_after=self.settings[server.id]["delete_delay"])
        except Exception as e:
            print(e)
            await self.bot.say("Quelque chose s'est mal passé.", delete_after=self.settings[server.id]["delete_delay"])

    @editrole.command(name="name", pass_context=True)
    @checks.is_owner()
    async def edit_role_name(self, ctx, role: discord.Role, name: str):
        """Change le nom d'un role

        Utilisez des guillements si le nom du rôle contient des espaces.
        Exemples:
        !editrole name \"The Transistor\" Test"""
        server = ctx.message.server
        if name == "":
            await self.bot.say("Le nom ne peut pas être vide.", delete_after=self.settings[server.id]["delete_delay"])
            return
        try:
            author = ctx.message.author
            old_name = role.name  # probably not necessary?
            await self.bot.edit_role(ctx.message.server, role, name=name)
            logger.info("{}({}) changed the name of role '{}' to '{}'".format(
                author.name, author.id, old_name, name))
            await self.bot.say("Fait.\n{} a changé le nom du role de '{}' à '{}'".format(
                author.name, old_name, name), delete_after=self.settings[server.id]["delete_delay"])
            await self.bot.say("Ne pas oublier d'avertir l'owner", delete_after=self.settings[server.id]["delete_delay"])
        except discord.Forbidden:
            await self.bot.say("J'ai d'abord besoin de permissions pour gérer les rôles.", delete_after=self.settings[server.id]["delete_delay"])
        except Exception as e:
            print(e)
            await self.bot.say("Quelque chose s'est mal passé.", delete_after=self.settings[server.id]["delete_delay"])

    @editrole.command(name="list", pass_context=True)
    async def _listroles(self, ctx):
        """Affiche tous les rôles"""
        owner_cog = self.bot.get_cog('Owner')
        await ctx.invoke(owner_cog.getserverroles)
 ### GROUPE ROLES END

 ### GROUPE USER START
    @commands.group(name="users", no_pm=True, pass_context=True)
    @checks.admin_or_permissions()
    async def _users(self, ctx):
        """Groupe: Users"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_users.command(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(manage_nicknames=True)
    async def rename(self, ctx, user: discord.Member, *, nickname=""):
        """Change le surnom de l'utilisateur

        Si pas de surnom cela supprime le surnom existant."""
        nickname = nickname.strip()
        server = ctx.message.server
        if nickname == "":
            nickname = None
        try:
            await self.bot.change_nickname(user, nickname)
            await self.bot.say("Fait.", delete_after=self.settings[server.id]["delete_delay"])
        except discord.Forbidden:
            await self.bot.say("Je ne peux pas faire ça.\n"
                               "J'ai besoin de la permission"
                               "\"Manage Nicknames\".", delete_after=self.settings[server.id]["delete_delay"])

    @_users.command(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(ban_members=True)
    async def banpre(self, ctx, user_id: int, *, reason: str = None):
        """Ban préemptif d'un user du serveur

        Un user ID doit être fourni
        Si l'utilisateur est présent dans le serveur un ban normal 
        sera fait à la place"""
        user_id = str(user_id)
        author = ctx.message.author
        server = author.server

        ban_list = await self.bot.get_bans(server)
        is_banned = discord.utils.get(ban_list, id=user_id)

        if is_banned:
            await self.bot.say("Le user est déjà ban.", delete_after=self.settings[server.id]["delete_delay"])
            return

        user = server.get_member(user_id)
        if user is not None:
            await ctx.invoke(self.ban, ctx, user=user, reason=reason)
            return

        try:
            await self.bot.http.ban(user_id, server.id, 0)
        except discord.NotFound:
            await self.bot.say("User pas trouvé. Avez-vous donné le bonuser ID ?", delete_after=self.settings[server.id]["delete_delay"])
        except discord.Forbidden:
            await self.bot.say("Je n'ai pas la permission pour faire cela.", delete_after=self.settings[server.id]["delete_delay"])
        else:
            logger.info("{}({}) preemptively banned {}"
                        "".format(author.name, author.id, user_id))
            user = await self.bot.get_user_info(user_id)
            await self.cases.new_case(server,
                                action="PREBAN",
                                mod=author,
                                user=user,
                                reason=reason)
            await self.bot.say("Fait. L'utilisateur ne sera pas capable de joindre le serveur.", delete_after=self.settings[server.id]["delete_delay"])

    @_users.command(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(ban_members=True)
    async def ban(self, ctx, user: discord.Member, days: str = None, *, reason: str = None):
        """Bans user and deletes last X days worth of messages.

        If days is not a number, it's treated as the first word of the reason.
        Minimum 0 days, maximum 7. Defaults to 0."""
        author = ctx.message.author
        server = author.server

        if author == user:
            await self.bot.say("I cannot let you do that. Self-harm is "
                               "bad \N{PENSIVE FACE}")
            return
        elif not self.is_allowed_by_hierarchy(server, author, user):
            await self.bot.say("I cannot let you do that. You are "
                               "not higher than the user in the role "
                               "hierarchy.")
            return
        if reason is None:
            await self.bot.say("La raison est obligatoire. Y-en a t'il  "
                               "vraiment une ? \N{THINKING FACE}")
            return
        if days:
            if days.isdigit():
                days = int(days)
            else:
                if reason:
                    reason = days + ' ' + reason
                else:
                    reason = days
                days = 0
        else:
            days = 0

        if days < 0 or days > 7:
            await self.bot.say("Invalid days. Must be between 0 and 7.", delete_after=self.settings[server.id]["delete_delay"])
            return

        try:
            self.temp_cache.add(user, server, "BAN")
            await self.bot.ban(user, days)
            logger.info("{}({}) banned {}({}), deleting {} days worth of messages".format(
                author.name, author.id, user.name, user.id, str(days)))
            await self.cases.new_case(server,
                                action="BAN",
                                mod=author,
                                user=user,
                                reason=reason)
            await self.bot.say("Done. It was about time.", delete_after=self.settings[server.id]["delete_delay"])
        except discord.errors.Forbidden:
            await self.bot.say("I'm not allowed to do that.", delete_after=self.settings[server.id]["delete_delay"])
        except Exception as e:
            print(e)

    @_users.command(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(ban_members=True)
    async def bansoft(self, ctx, user: discord.Member, *, reason: str, days: int):
        """Bans the user, deleting x day worth of messages. reinvite him"""
        server = ctx.message.server
        channel = ctx.message.channel
        can_ban = channel.permissions_for(server.me).kick_members
        author = ctx.message.author

        if author == user:
            await self.bot.say("I cannot let you do that. Self-harm is "
                               "bad \N{PENSIVE FACE}")
            return
        elif not self.is_allowed_by_hierarchy(server, author, user):
            await self.bot.say("I cannot let you do that. You are "
                               "not higher than the user in the role "
                               "hierarchy.")
            return
        if reason is None:
            await self.bot.say("La raison est obligatoire. Y-en a t'il  "
                               "vraiment une ? \N{THINKING FACE}")
            return
        try:
            invite = await self.bot.create_invite(server, max_age=3600*24*(days+1))
            invite = "\nInvite: " + invite
        except:
            invite = ""
        if can_ban:
            try:
                try:  # We don't want blocked DMs preventing us from banning
                    msg = await self.bot.send_message(user, "You have been banned and "
                                                      "then unbanned as a quick way to delete your messages.\n"
                                                      "You can now join the server again.{}".format(invite))
                except:
                    pass
                self.temp_cache.add(user, server, "SOFTBAN")
                await self.bot.ban(user, days)
                logger.info("{}({}) softbanned {}({}), deleting {} day(s) worth "
                            "of messages".format(author.name, author.id, user.name,
                                                 user.id, days))
                await self.cases.new_case(server,
                                    action="SOFTBAN",
                                    mod=author,
                                    user=user,
                                    reason=reason)
                self.temp_cache.add(user, server, "UNBAN")
                await self.bot.unban(server, user)
                await self.bot.say("Done. Enough chaos.", delete_after=15)
            except discord.errors.Forbidden:
                await self.bot.say("My role is not high enough to softban that user.", delete_after=self.settings[server.id]["delete_delay"])
                await self.bot.delete_message(msg)
            except Exception as e:
                print(e)
        else:
            await self.bot.say("I'm not allowed to do that.", delete_after=self.settings[server.id]["delete_delay"])
 ### GROUPE USER END

 ### GROUPE ADMSET START
    @commands.group(pass_context=True, no_pm=True)
    @checks.cocap_or_permissions()
    async def adminset(self, ctx):
        """Groupe: Paramètres d'administration"""
        if ctx.invoked_subcommand is None:
            server = ctx.message.server
            await send_cmd_help(ctx)
            roles = settings.get_server(server).copy()
            _settings = {**self.settings[server.id], **roles}
            if _settings["delete_delay"] == -1:
                _settings["delete_delay"] = "Disabled"

            msg = ("ROLES:\n"
                   "\tCoCap: {COCAP_ROLE}\n"
                   "\tAdmin: {ADMIN_ROLE}\n"
                   "\tMod: {MOD_ROLE}\n"
                   "\tSel: {SEL_ROLE}\n"
                   "ADMINS:\n"
                   "\tBan mention spam: {ban_mention_spam}\n"
                   "\tDelete repeats: {delete_repeats}\n"
                   "OWNER:\n"
                   "\tMod-log: {mod-log-name}\n"
                   "\tIdea-Claim: {idea-claim-name}\n"
                   "\tBotcmd: {botcmd-name}\n"
                   "\tDelete delay: {delete_delay}\n"
                   "\tRespects hierarchy: {respect_hierarchy}"
                   "".format(**_settings))
            await self.bot.say(box(msg), delete_after = self.settings[server.id]["delete_delay"])

    @adminset.command(pass_context=True, no_pm=True)
    async def delrepeats(self, ctx):
        """Enables auto deletion of repeated messages"""
        server = ctx.message.server
        if not self.settings[server.id]["delete_repeats"]:
            self.settings[server.id]["delete_repeats"] = True
            await self.bot.say("Messages repeated up to 3 times will "
                               "be deleted.")
        else:
            self.settings[server.id]["delete_repeats"] = False
            await self.bot.say("Repeated messages will be ignored.", delete_after=self.settings[server.id]["delete_delay"])
        dataIO.save_json(self._ownersettings_path, self.settings)

    @adminset.command(pass_context=True, no_pm=True, name='casesreset')
    async def resetcases(self, ctx):
        """Resets cases"""
        server = ctx.message.server
        self.cases.resetlogs(server)
        await self.unStackSMS(server)

    @adminset.command(pass_context=True, no_pm=True, name='cases')
    async def setCases(self, ctx, action: str = None, enabled: bool = None):
        """Active ou desactive la création de case

        Enabled peut être 'on' ou 'off'"""
        if action is None:
            await send_cmd_help(ctx)
        server = ctx.message.server
        self.cases.set_cases(server, action, enabled)
        await self.unStackSMS(server)

    @adminset.command(pass_context=True, no_pm=True)
    async def banmentionspam(self, ctx, max_mentions: int=False):
        """Enables auto ban for messages mentioning X different people

        Accepted values: 5 or superior"""
        server = ctx.message.server
        if max_mentions:
            if max_mentions < 5:
                max_mentions = 5
            self.settings[server.id]["ban_mention_spam"] = max_mentions
            await self.bot.say("Autoban for mention spam enabled. "
                               "Anyone mentioning {} or more different people "
                               "in a single message will be autobanned."
                               "".format(max_mentions))
        else:
            if self.settings[server.id]["ban_mention_spam"] is False:
                await send_cmd_help(ctx)
                return
            self.settings[server.id]["ban_mention_spam"] = False
            await self.bot.say("Autoban for mention spam disabled.", delete_after=self.settings[server.id]["delete_delay"])
        dataIO.save_json(self._ownersettings_path, self.settings)
 ### GROUPE ADMSET END

 ### GROUPE SERVERS START
    @commands.group(name="iolist", pass_context=True, no_pm=True, invoke_without_command=True)
    @checks.cocap_or_permissions()
    async def igunlist(self, ctx):
        """Groupe: ignore/unignore list"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            await self.bot.say(self.count_ignored())

  ### GROUPE IGNORE START

    @igunlist.group(name="ignore", pass_context=True, no_pm=True, invoke_without_command=True)
    @checks.cocap_or_permissions()
    async def ignore(self, ctx):
        """Adds servers/channels to ignorelist"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            await self.bot.say(self.count_ignored())

    @ignore.command(name="channel", pass_context=True)
    async def ignore_channel(self, ctx, channel: discord.Channel=None):
        """Ignores channel

        Defaults to current one"""
        current_ch = ctx.message.channel
        server = ctx.message.server
        if not channel:
            if current_ch.id not in self.ignore_list["CHANNELS"]:
                self.ignore_list["CHANNELS"].append(current_ch.id)
                dataIO.save_json(self._ignore_list_path, self.ignore_list)
                await self.bot.say("Channel added to ignore list.", delete_after=self.settings[server.id]["delete_delay"])
            else:
                await self.bot.say("Channel already in ignore list.", delete_after=self.settings[server.id]["delete_delay"])
        else:
            if channel.id not in self.ignore_list["CHANNELS"]:
                self.ignore_list["CHANNELS"].append(channel.id)
                dataIO.save_json(self._ignore_list_path, self.ignore_list)
                await self.bot.say("Channel added to ignore list.", delete_after=self.settings[server.id]["delete_delay"])
            else:
                await self.bot.say("Channel already in ignore list.", delete_after=self.settings[server.id]["delete_delay"])

    @ignore.command(name="server", pass_context=True)
    async def ignore_server(self, ctx):
        """Ignores current server"""
        server = ctx.message.server
        if server.id not in self.ignore_list["SERVERS"]:
            self.ignore_list["SERVERS"].append(server.id)
            dataIO.save_json(self._ignore_list_path, self.ignore_list)
            await self.bot.say("This server has been added to the ignore list.", delete_after=self.settings[server.id]["delete_delay"])
        else:
            await self.bot.say("This server is already being ignored.", delete_after=self.settings[server.id]["delete_delay"])
  ### GROUPE IGNORE END

  ### GROUPE UNIGNORE START
    @igunlist.group(name="unignore", pass_context=True, no_pm=True, invoke_without_command=True)
    @checks.cocap_or_permissions()
    async def unignore(self, ctx):
        """Removes servers/channels from ignorelist"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            await self.bot.say(self.count_ignored())

    @unignore.command(name="channel", pass_context=True)
    async def unignore_channel(self, ctx, channel: discord.Channel=None):
        """Removes channel from ignore list

        Defaults to current one"""
        current_ch = ctx.message.channel
        server = ctx.message.server
        if not channel:
            if current_ch.id in self.ignore_list["CHANNELS"]:
                self.ignore_list["CHANNELS"].remove(current_ch.id)
                dataIO.save_json(self._ignore_list_path, self.ignore_list)
                await self.bot.say("This channel has been removed from the ignore list.", delete_after=self.settings[server.id]["delete_delay"])
            else:
                await self.bot.say("This channel is not in the ignore list.", delete_after=self.settings[server.id]["delete_delay"])
        else:
            if channel.id in self.ignore_list["CHANNELS"]:
                self.ignore_list["CHANNELS"].remove(channel.id)
                dataIO.save_json(self._ignore_list_path, self.ignore_list)
                await self.bot.say("Channel removed from ignore list.", delete_after=self.settings[server.id]["delete_delay"])
            else:
                await self.bot.say("That channel is not in the ignore list.", delete_after=self.settings[server.id]["delete_delay"])

    @unignore.command(name="server", pass_context=True)
    async def unignore_server(self, ctx):
        """Removes current server from ignore list"""
        server = ctx.message.server
        if server.id in self.ignore_list["SERVERS"]:
            self.ignore_list["SERVERS"].remove(server.id)
            dataIO.save_json(self._ignore_list_path, self.ignore_list)
            await self.bot.say("This server has been removed from the ignore list.", delete_after=self.settings[server.id]["delete_delay"])
        else:
            await self.bot.say("This server is not in the ignore list.", delete_after=self.settings[server.id]["delete_delay"])
  ### GROUPE UNIGNORE END
 ### GROUPE SERVERS END

    def count_ignored(self):
        msg = "```Currently ignoring:\n"
        msg += str(len(self.ignore_list["CHANNELS"])) + " channels\n"
        msg += str(len(self.ignore_list["SERVERS"])) + " servers\n```\n"
        return msg

    async def unStackSMS(self, server):
        pileSms = self.cases.sms.myPrint()
        if pileSms:
            for sMs in pileSms:
                await self.bot.say(sMs)
        else:
            await self.bot.say("no sms", delete_after=self.settings[server.id]["delete_delay"])
        return

    def is_allowed_by_hierarchy(self, server, mod, user):
        toggled = self.settings[server.id]["respect_hierarchy"]
        is_special = mod == server.owner or mod.id == self.bot.settings.owner

        if not toggled:
            return True
        else:
            return mod.top_role.position > user.top_role.position or is_special

def check_folders():
    folders = ("data", "data/mod/")
    for folder in folders:
        if not os.path.exists(folder):
            print("Création du dossier " + folder + " ...")
            os.makedirs(folder)

def check_files():
    ignore_list = {"SERVERS": [], "CHANNELS": []}

    files = {
        "ignorelist.json": ignore_list,
        "filter.json": {},
        "past_names.json": {},
        "past_nicknames.json": {},
        "perms_cache.json": {}
    }

    for filename, value in files.items():
        if not os.path.isfile("data/mod/{}".format(filename)):
            print("Création du fichier vide {}".format(filename))
            dataIO.save_json("data/mod/{}".format(filename), value)

def setup(bot): 
    global logger
    check_folders()
    check_files()
    logger = logging.getLogger("admin")
    # Prevents the logger from being loaded again in case of module reload
    if logger.level == 0:
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(
            filename=admin_log_path, encoding='utf-8', mode='a')
        handler.setFormatter(
            logging.Formatter('%(asctime)s %(message)s', datefmt="[%d/%m/%Y %H:%M]"))
        logger.addHandler(handler)
    n = Admin(bot)
    bot.add_cog(n)
