import discord
import os
import re
import logging
import time
import asyncio

from datetime import datetime
from collections import deque, defaultdict, OrderedDict

from __main__ import send_cmd_help, settings
from discord.ext import commands
from cogs.utils import checks
from cogs.utils import cases
from cogs.utils import tempcache
from cogs.utils.dataIO import dataIO
from cogs.utils.chat_formatting import escape_mass_mentions, box, pagify
from cogs.remindme import RemindMe
from cogs.utils.settings import Settings

mod_log_path = "data/mod/mod.log"
class Mod:
    """Outils de Modération."""
    _ignore_list_path = "data/mod/ignorelist.json"
    _filter_path = "data/mod/filter.json"
    _ownersettings_path = "data/red/ownersettings.json"
    _perms_cache_path = "data/mod/perms_cache.json"
    _past_names_path = "data/mod/past_names.json"
    _past_nicknames_path = "data/mod/past_nicknames.json"
    _reminders_path = "data/remindme/reminders.json"

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

 ### GROUPE KICK START
    @commands.group(name="kick", pass_context=True, no_pm=True, invoke_without_command=True)
    @checks.mod_or_permissions()
    async def _kick(self, ctx):
        """Groupe: Kick un utilisateur"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)
            return

    @_kick.command(no_pm=True, pass_context=True)
    async def soft(self, ctx, user: discord.Member, *, reason: str=None):
        """Kick un utilisateur."""
        author = ctx.message.author
        server = author.server

        if author == user:
            await self.bot.say("Je ne peux pas vous laisser faire ça. "
                               "L'auto-mutilation c'est mal.\N{PENSIVE FACE}", delete_after=self.settings[server.id]["delete_delay"])
            return
        elif not self.is_allowed_by_hierarchy(server, author, user):
            await self.bot.say("Je ne peux pas vous laisser faire ça. Vous n'êtes pas "
                               "plus haut que l'utilisateur en question "
                               "dans la hiérarchie.", delete_after=self.settings[server.id]["delete_delay"])
            return
        if reason is None:
            await self.bot.say("La raison est obligatoire. Y-en a t'il  "
                               "vraiment une ? \N{THINKING FACE}", delete_after=self.settings[server.id]["delete_delay"])
            await self.bot.send_cmd_help(ctx)
            return
        if server.id not in self.settings:
            return False

        try:
            await self.bot.kick(user)
            log_msg = "{}({}) kicked par {}({}) - Raison: {}".format(user.name,
                                                                     user.id, author.name, author.id, reason)
            case_number = await self.cases.new_case(server,
                                action="KICK",
                                mod=author,
                                user=user,
                                reason=reason)
            log_msg = "CASE : " + str(case_number) + " --> " + log_msg
            logger.info(log_msg)
            await self.bot.say(log_msg, delete_after=self.settings[server.id]["delete_delay"])
        except discord.errors.Forbidden:
            await self.bot.say("Je n'ai pas le droit de faire ça.", delete_after=self.settings[server.id]["delete_delay"])
        except Exception as e:
            await self.bot.say("Une erreur s'est produite:\n {}".format(e), delete_after=self.settings[server.id]["delete_delay"])
            logger.info("mod.py: commande Kick soft: {}".format(e))
            #print("mod.py: commande Kick soft: {}".format(e))

    @_kick.command(no_pm=True, pass_context=True)
    async def hard(self, ctx, user: discord.Member, *, reason: str=None):
        """Kick un utilisateur, le ban 1 jour, supprime 1j de ses messages."""
        server = ctx.message.server
        channel = ctx.message.channel
        # Vérifie que le bot a le droit de ban
        can_ban = channel.permissions_for(server.me).ban_members
        author = ctx.message.author
        oneday = 3600*24

        if author == user:
            await self.bot.say("Je ne peux pas vous laisser faire ça. "
                               "L'auto-mutilation c'est mal.\N{PENSIVE FACE}", delete_after=self.settings[server.id]["delete_delay"])
            return
        elif not self.is_allowed_by_hierarchy(server, author, user):
            await self.bot.say("Je ne peux pas vous laisser faire ça. Vous n'êtes pas "
                               "plus haut que l'utilisateur en question "
                               "dans la hiérarchie.", delete_after=self.settings[server.id]["delete_delay"])
            return
        if reason is None:
            await self.bot.say("La raison est obligatoire. Y-en a t'il  "
                               "vraiment une ? \N{THINKING FACE}", delete_after=self.settings[server.id]["delete_delay"])
            await self.bot.send_cmd_help(ctx)
            return
        try:
            invitation = await self.bot.create_invite(destination=ctx.message.channel,  xkcd=True, max_uses=2)
        except discord.Forbidden:
            await self.bot.say("Impossible de créer une invitation. Voir les logs du bot.", delete_after=self.settings[server.id]["delete_delay"])
            return
        if can_ban:

            try:
                try:  # We don't want blocked DMs preventing us from kicking
                    msg = await self.bot.send_message(user, "Vous avez été Kick car : {}\n"
                                                      "Vous pourrez rejoindre à nouveau le serveur dans 1 jour. \n".format(reason))
                except:
                    await self.bot.whisper(author, "Le message suivant n'a pas été envoyé à {}\n"
                                           "Vous avez été Kick car : {}\n"
                                           "Vous pourrez rejoindre à nouveau le serveur dans 1 jour. \n".format(user, reason))
                    pass

                @asyncio.coroutine
                def delayed_invite_unkick():
                    yield from asyncio.sleep(oneday, loop=self.bot.loop)
                    yield from self.bot.unban(server, user)
                    yield from self.unkick(ctx, author, user, invitation)

                discord.compat.create_task(
                    delayed_invite_unkick(), loop=self.bot.loop)

                self.temp_cache.add(user, server, "HARDKICK")
                await self.bot.ban(user)
                log_msg = "{}({}) hardkicked par {}({}) - Raison: {}".format(
                    user.name, user.id, author.name, author.id, reason)
                case_number = await self.cases.new_case(server,
                                    action="HARDKICK",
                                    mod=author,
                                    user=user,
                                    reason=reason)
                log_msg = "CASE : " + str(case_number) + " --> " + log_msg
                logger.info(log_msg)
                await self.bot.say(log_msg, delete_after=self.settings[server.id]["delete_delay"])
            except discord.errors.Forbidden:
                await self.bot.say("Mon role n'est pas assez élevé pour hardkick cet utilisateur.", delete_after=self.settings[server.id]["delete_delay"])
                await self.bot.delete_message(msg)
            except Exception as e:
                await self.bot.say("Une erreur s'est produite:\n {}".format(e), delete_after=self.settings[server.id]["delete_delay"])
            logger.info("mod.py: commande Kick hard: {}".format(e))
            print("mod.py: commande Kick hard: {}".format(e))
        else:
            await self.bot.say("Je n'ai pas le droit de faire ça.", delete_after=self.settings[server.id]["delete_delay"])
        print("Ajouter un selfbot pour remplacer le reminder")
 ### GROUPE KICK END

 ### GROUPE MUTE START
    @commands.group(pass_context=True, no_pm=True, invoke_without_command=True)
    @checks.mod_or_permissions()
    async def mute(self, ctx):
        """Groupe: Mute un utilisateur"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)
            return

    @mute.command(name="channel", pass_context=True, no_pm=True)
    async def channel_mute(self, ctx, user: discord.Member, *, reason: str=None):
        """Mute pour le channel courant"""
        author = ctx.message.author
        channel = ctx.message.channel
        server = ctx.message.server
        overwrites = channel.overwrites_for(user)

        if reason is None:
            await self.bot.say("La raison est obligatoire. Y-en a t'il "
                               "vraiment une ? \N{THINKING FACE}", delete_after=self.settings[server.id]["delete_delay"])
            await self.bot.send_cmd_help(ctx)
            return
        if overwrites.send_messages is False:
            await self.bot.say("Cet utilisateur ne peut pas envoyer de messages dans ce "
                               "channel.", delete_after=self.settings[server.id]["delete_delay"])
            return
        elif not self.is_allowed_by_hierarchy(server, author, user):
            await self.bot.say("Je ne peux pas vous laisser faire ça. Vous n'êtes pas "
                               "plus haut que l'utilisateur en question "
                               "dans la hiérarchie.", delete_after=self.settings[server.id]["delete_delay"])
            return

        self._perms_cache[user.id][channel.id] = overwrites.send_messages
        overwrites.send_messages = False
        try:
            await self.bot.edit_channel_permissions(channel, user, overwrites)
        except discord.Forbidden:
            await self.bot.say("Mute de l'utilisateur en Echec. J'ai besoin de la permission "
                               "Gestion de rôles et l'utilisateur doit être plus bas que moi "
                               "dans la hiérarchie des rôles.", delete_after=self.settings[server.id]["delete_delay"])
        else:
            dataIO.save_json(self._perms_cache_path, self._perms_cache)
            log_msg = "{}({}) Mute sur le channel {} par {}({}) - Raison: {}".format(
                user.name, user.id, channel, author.name, author.id, reason)
            case_number = await self.cases.new_case(server,
                                action="CMUTE",
                                channel=channel,
                                mod=author,
                                user=user,
                                reason=reason)
            log_msg = "CASE : " + str(case_number) + " --> " + log_msg
            logger.info(log_msg)
            await self.bot.say(log_msg, delete_after=self.settings[server.id]["delete_delay"])

    @mute.command(name="server", pass_context=True, no_pm=True)
    async def server_mute(self, ctx, user: discord.Member, *, reason: str=None):
        """Mute pour le serveur"""
        author = ctx.message.author
        server = ctx.message.server

        if reason is None:
            await self.bot.say("La raison est obligatoire. Y-en a t'il  "
                               "vraiment une ? \N{THINKING FACE}", delete_after=self.settings[server.id]["delete_delay"])
            return
        if not self.is_allowed_by_hierarchy(server, author, user):
            await self.bot.say("Je ne peux pas vous laisser faire ça. Vous n'êtes pas "
                               "plus haut que l'utilisateur en question "
                               "dans la hiérarchie.", delete_after=self.settings[server.id]["delete_delay"])
            return

        register = {}
        for channel in server.channels:
            if channel.type != discord.ChannelType.text:
                continue
            overwrites = channel.overwrites_for(user)
            if overwrites.send_messages is False:
                continue
            register[channel.id] = overwrites.send_messages
            overwrites.send_messages = False
            try:
                await self.bot.edit_channel_permissions(channel, user,
                                                        overwrites)
            except discord.Forbidden:
                await self.bot.say("Mute de l'utilisateur en Echec. J'ai besoin de la permission "
                                   "Gestion de rôles et l'utilisateur doit être plus bas que moi "
                                   "dans la hiérarchie des rôles.", delete_after=self.settings[server.id]["delete_delay"])
                return
            else:
                await asyncio.sleep(0.1)
        if not register:
            await self.bot.say("Cet utilisateur est déjà mute dans tous les channels.", delete_after=self.settings[server.id]["delete_delay"])
            return
        self._perms_cache[user.id] = register
        dataIO.save_json(self._perms_cache_path, self._perms_cache)
        log_msg = "{}({}) Mute sur le serveur par {}({}) - Raison: {}".format(
            user.name, user.id, author.name, author.id, reason)
        case_number = await self.cases.new_case(server,
                            action="SMUTE",
                            mod=author,
                            user=user,
                            reason=reason)
        log_msg = "CASE : " + str(case_number) + " --> " + log_msg
        logger.info(log_msg)
        await self.bot.say(log_msg, delete_after=self.settings[server.id]["delete_delay"])
 ### GROUPE MUTE END

 ### GROUPE UNMUTE START
    @commands.group(pass_context=True, no_pm=True, invoke_without_command=True)
    @checks.mod_or_permissions()
    async def unmute(self, ctx):
        """Groupe: Dé-mute un utilisateur"""
        if ctx.invoked_subcommand is None:
            #
            # HOWTO appeler une commande du bot
            # await ctx.invoke(self.channel_unmute, user=user)
            #
            await self.bot.send_cmd_help(ctx)
            return

    @unmute.command(name="channel", pass_context=True, no_pm=True)
    async def channel_unmute(self, ctx, user: discord.Member):
        """Dé-mute l'utilisateur dans le channel courant"""
        channel = ctx.message.channel
        author = ctx.message.author
        server = ctx.message.server
        overwrites = channel.overwrites_for(user)

        if overwrites.send_messages:
            await self.bot.say("Cet utilisateur ne semble pas être mute "
                               "dans ce channel.", delete_after=self.settings[server.id]["delete_delay"])
            return
        elif not self.is_allowed_by_hierarchy(server, author, user):
            await self.bot.say("Je ne peux pas vous laisser faire ça. Vous n'êtes pas "
                               "plus haut que l'utilisateur en question "
                               "dans la hiérarchie.", delete_after=self.settings[server.id]["delete_delay"])
            return

        if user.id in self._perms_cache:
            old_value = self._perms_cache[user.id].get(channel.id)
        else:
            old_value = None
        overwrites.send_messages = old_value
        is_empty = self.are_overwrites_empty(overwrites)
        try:
            if not is_empty:
                await self.bot.edit_channel_permissions(channel, user,
                                                        overwrites)
            else:
                await self.bot.delete_channel_permissions(channel, user)
        except discord.Forbidden:
            await self.bot.say("Mute de l'utilisateur en Echec. J'ai besoin de la permission "
                               "Gestion de rôles et l'utilisateur doit être plus bas que moi "
                               "dans la hiérarchie des rôles.", delete_after=self.settings[server.id]["delete_delay"])
        else:
            try:
                del self._perms_cache[user.id][channel.id]
            except KeyError:
                pass
            if user.id in self._perms_cache and not self._perms_cache[user.id]:
                del self._perms_cache[user.id]  # cleanup
            dataIO.save_json(self._perms_cache_path, self._perms_cache)
            log_msg = "{}({}) Dé-Mute sur le channel {} par {}({})".format(
                user.name, user.id, channel, author.name, author.id)
            case_number = await self.cases.new_case(server,
                                action="UNCMUTE",
                                mod=author,
                                user=user,
                                reason=None)
            log_msg = "CASE : " + str(case_number) + " --> " + log_msg
            logger.info(log_msg)
            await self.bot.say(log_msg, delete_after=self.settings[server.id]["delete_delay"])

    @unmute.command(name="server", pass_context=True, no_pm=True)
    async def server_unmute(self, ctx, user: discord.Member):
        """Dé-mute l'utilisateur dans le serveur"""
        server = ctx.message.server
        author = ctx.message.author

        if user.id not in self._perms_cache:
            await self.bot.say("Cet utilisateur ne semble pas avoir été avec la commande {0}mute. "
                               "Le dé-mute dans les channels que vous voulez avec `{0}unmute <user>`"
                               "".format(ctx.prefix), delete_after=self.settings[server.id]["delete_delay"])
            return
        elif not self.is_allowed_by_hierarchy(server, author, user):
            await self.bot.say("Je ne peux pas vous laisser faire ça. Vous n'êtes pas "
                               "plus haut que l'utilisateur en question "
                               "dans la hiérarchie.", delete_after=self.settings[server.id]["delete_delay"])
            return

        for channel in server.channels:
            if channel.type != discord.ChannelType.text:
                continue
            if channel.id not in self._perms_cache[user.id]:
                continue
            value = self._perms_cache[user.id].get(channel.id)
            overwrites = channel.overwrites_for(user)
            if overwrites.send_messages is False:
                overwrites.send_messages = value
                is_empty = self.are_overwrites_empty(overwrites)
                try:
                    if not is_empty:
                        await self.bot.edit_channel_permissions(channel, user,
                                                                overwrites)
                    else:
                        await self.bot.delete_channel_permissions(channel, user)
                except discord.Forbidden:
                    await self.bot.say("Dé-mute de l'utilisateur en Echec. J'ai besoin de la permission "
                                       "Gestion de rôles et l'utilisateur doit être plus bas que moi "
                                       "dans la hiérarchie des rôles.", delete_after=self.settings[server.id]["delete_delay"])
                    return
                else:
                    del self._perms_cache[user.id][channel.id]
                    await asyncio.sleep(0.1)
        if user.id in self._perms_cache and not self._perms_cache[user.id]:
            del self._perms_cache[user.id]  # cleanup
        dataIO.save_json(self._perms_cache_path, self._perms_cache)
        log_msg = "{}({}) Dé-Mute sur le serveur{}({})".format(user.name,
                                                               user.id, author.name, author.id)
        case_number = await self.cases.new_case(server,
                            action="UNSMUTE",
                            mod=author,
                            user=user,
                            reason=None)
        log_msg = "CASE : " + str(case_number) + " --> " + log_msg
        logger.info(log_msg)
        await self.bot.say(log_msg, delete_after=self.settings[server.id]["delete_delay"])
 ### GROUPE UNMUTE END

 ### GROUPE CLEANUP START
    @commands.group(pass_context=True)
    @checks.mod_or_permissions()
    async def cleanup(self, ctx):
        """Groupe: Efface des messages"""
        if ctx.invoked_subcommand is None:  # TODO : Est-ce vraiment nécessaire de check une sub commande ?
            await send_cmd_help(ctx) # TODO : introduire la gestion de discord.errors.HTTPException

    @cleanup.command(pass_context=True, no_pm=True)
    async def with_txt(self, ctx, text: str, number: int):
        """Efface les X messages comportant un texte précis.

        Exemple: cleanup with_txt \"test\" 5"""

        channel = ctx.message.channel
        author = ctx.message.author
        server = author.server
        is_bot = self.bot.user.bot
        has_permissions = channel.permissions_for(server.me).manage_messages

        def check(m):
            if text in m.content:
                return True
            elif m == ctx.message:
                return True
            else:
                return False

        to_delete = [ctx.message]

        if not has_permissions:
            await self.bot.say("Je n'ai pas le droit d'effacer des messages.", delete_after=self.settings[server.id]["delete_delay"])
            return

        tries_left = 5
        tmp = ctx.message

        while tries_left and len(to_delete) - 1 < number:
            async for message in self.bot.logs_from(channel, limit=100,
                                                    before=tmp):
                if len(to_delete) - 1 < number and check(message):
                    to_delete.append(message)
                tmp = message
            tries_left -= 1

        if is_bot:
            has_del = await self.mass_purge(to_delete)
        else:
            has_del = await self.slow_deletion(to_delete)

        log_msg = "{}({}) a effacé {} message(s) contenant '{}' dans le salon {}".format(author.name,
                                                                                         author.id, len(to_delete), text, channel.id)
        if has_del: 
            case_number = await self.cases.new_case(server,
                            action="CLEANED",
                            mod=author,
                            user=None,
                            reason="dans le salon {}: {} message(s) contenant '{}'".format(channel.id, len(to_delete), text))
            log_msg = "CASE : " + str(case_number) + " --> " + log_msg
        else:
            log_msg = "NO CASE something went wrong --> " + log_msg
        logger.info(log_msg)
        await self.bot.say(log_msg, delete_after=self.settings[server.id]["delete_delay"])

    @cleanup.command(pass_context=True, no_pm=True)
    async def user(self, ctx, user: discord.Member, number: int):
        """Efface les X derniers messages d'un user.

        Exemples:
        cleanup user @\u200bTwentysix 2
        cleanup user Red 6"""

        channel = ctx.message.channel
        author = ctx.message.author
        server = author.server
        is_bot = self.bot.user.bot
        has_permissions = channel.permissions_for(server.me).manage_messages
        self_delete = user == self.bot.user

        def check(m):
            if m.author == user:
                return True
            elif m == ctx.message:
                return True
            else:
                return False

        to_delete = [ctx.message]

        if not has_permissions and not self_delete:
            await self.bot.say("Je n'ai pas le droit d'effacer des messages.", delete_after=self.settings[server.id]["delete_delay"])
            return

        tries_left = 5
        tmp = ctx.message

        while tries_left and len(to_delete) - 1 < number:
            async for message in self.bot.logs_from(channel, limit=100,
                                                    before=tmp):
                if len(to_delete) - 1 < number and check(message):
                    to_delete.append(message)
                tmp = message
            tries_left -= 1

        if is_bot and not self_delete:
            # For whatever reason the purge endpoint requires manage_messages
            has_del = await self.mass_purge(to_delete)
        else:
            has_del = await self.slow_deletion(to_delete)

        log_msg = "{}({}) a effacé {} message(s) fait par {}({}) dans le salon {}".format(
            author.name, author.id, len(to_delete), user.name, user.id, channel.name)
        if has_del: 
            case_number = await self.cases.new_case(server,
                            action="CLEANED",
                            mod=author,
                            user=user,
                            reason="dans le salon {}: {} message(s) fait par {}({}) ".format(channel.name, len(to_delete), user.name, user.id))
            log_msg = "CASE : " + str(case_number) + " --> " + log_msg
        else:
            log_msg = "NO CASE something went wrong --> " + log_msg
        logger.info(log_msg)
        await self.bot.say(log_msg, delete_after=self.settings[server.id]["delete_delay"])

    @cleanup.command(pass_context=True, no_pm=True)
    async def after(self, ctx, message_id: int):
        """Efface tous les messages après un message

        Pour avoir l'identifiant d'un message, activer le menu developeur 
        dans les paramètres de Discord, onglet Apparence.
        Ensuite faites un clic droit sur le message et copiez son identifiaint.

        Cette commande fonctionne uniquement avec les bots
        tournant comme bot de comptes.
        """

        channel = ctx.message.channel
        author = ctx.message.author
        server = channel.server
        is_bot = self.bot.user.bot
        has_permissions = channel.permissions_for(server.me).manage_messages

        if not is_bot:
            await self.bot.say("Cette commande fonctionne uniquement avec les bots"
                               "tournant comme bot de comptes.", delete_after=self.settings[server.id]["delete_delay"])
            return

        to_delete = []

        after = await self.bot.get_message(channel, message_id)

        if not has_permissions:
            await self.bot.say("Je n'ai pas le droit d'effacer des messages.", delete_after=self.settings[server.id]["delete_delay"])
            return
        elif not after:
            await self.bot.say("Message non trouvé.", delete_after=self.settings[server.id]["delete_delay"])
            return

        async for message in self.bot.logs_from(channel, limit=2000,
                                                after=after):
            to_delete.append(message)

        has_del = await self.mass_purge(to_delete)

        log_msg = "{}({}) a effacé {} message(s) dans le salon {}".format(
            author.name, author.id, len(to_delete), channel.name)
        if has_del: 
            case_number = await self.cases.new_case(server,
                            action="CLEANED",
                            mod=author,
                            user=None,
                            reason="dans le salon {}: {} message(s)".format(channel.name, len(to_delete)))
            log_msg = "CASE : " + str(case_number) + " --> " + log_msg
        else:
            log_msg = "NO CASE something went wrong --> " + log_msg
        logger.info(log_msg)
        await self.bot.say(log_msg, delete_after=self.settings[server.id]["delete_delay"])

    @cleanup.command(pass_context=True, no_pm=True)
    async def mes(self, ctx, number: int):
        """Efface les X derniers messages.

        Exemple: cleanup mes 26"""

        channel = ctx.message.channel
        author = ctx.message.author
        server = author.server
        is_bot = self.bot.user.bot
        has_permissions = channel.permissions_for(server.me).manage_messages

        to_delete = []

        if not has_permissions:
            await self.bot.say("Je n'ai pas le droit d'effacer des messages.", delete_after=self.settings[server.id]["delete_delay"])
            return

        async for message in self.bot.logs_from(channel, limit=number+1):
            to_delete.append(message)

        if is_bot:
            has_del = await self.mass_purge(to_delete)
        else:
            has_del = await self.slow_deletion(to_delete)

        log_msg = "{}({}) a effacé {} message(s) dans le salon {}".format(
            author.name, author.id, number, channel.name)
        if has_del: 
            case_number = await self.cases.new_case(server,
                            action="CLEANED",
                            mod=author,
                            user=None,
                            reason="dans le salon {}: {} message(s)".format(channel.name, number))
            log_msg = "CASE : " + str(case_number) + " --> " + log_msg
        else:
            log_msg = "NO CASE something went wrong --> " + log_msg
        logger.info(log_msg)
        await self.bot.say(log_msg, delete_after=self.settings[server.id]["delete_delay"])

    @cleanup.command(pass_context=True, no_pm=True, name='bot')
    async def cleanup_bot(self, ctx, number: int):
        """Efface les commandes et messages du bot"""
        
        channel = ctx.message.channel
        author = ctx.message.author
        server = channel.server
        is_bot = self.bot.user.bot
        has_permissions = channel.permissions_for(server.me).manage_messages

        prefixes = self.bot.command_prefix
        if isinstance(prefixes, str):
            prefixes = [prefixes]
        elif callable(prefixes):
            if asyncio.iscoroutine(prefixes):
                await self.bot.say("La coroutine des prefixes n'est pas encore implementée.", delete_after=self.settings[server.id]["delete_delay"])
                return
            prefixes = prefixes(self.bot, ctx.message)

        # In case some idiot sets a null prefix
        if '' in prefixes:
            prefixes.pop('')

        def check(m):
            if m.author.id == self.bot.user.id:
                return True
            elif m == ctx.message:
                return True
            p = discord.utils.find(m.content.startswith, prefixes)
            if p and len(p) > 0:
                return m.content[len(p):].startswith(tuple(self.bot.commands))
            return False

        to_delete = [ctx.message]

        if not has_permissions:
            await self.bot.say("Je n'ai pas le droit d'effacer des messages.", delete_after=self.settings[server.id]["delete_delay"])
            return

        tries_left = 5
        tmp = ctx.message

        while tries_left and len(to_delete) - 1 < number:
            async for message in self.bot.logs_from(channel, limit=100,
                                                    before=tmp):
                if len(to_delete) - 1 < number and check(message):
                    to_delete.append(message)
                tmp = message
            tries_left -= 1

        if is_bot:
            has_del = await self.mass_purge(to_delete)
        else:
            has_del = await self.slow_deletion(to_delete)

        log_msg = "{}({}) a effacé {} command message(s) dans le salon {}".format(author.name, author.id, len(to_delete),
                                                                                  channel.name)
        if has_del: 
            case_number = await self.cases.new_case(server,
                            action="CLEANED",
                            mod=author,
                            user=None,
                            reason="dans le salon {}: {} command message(s)".format(channel.name, len(to_delete)))
            log_msg = "CASE : " + str(case_number) + " --> " + log_msg
        else:
            log_msg = "NO CASE something went wrong --> " + log_msg
        logger.info(log_msg)
        await self.bot.say(log_msg, delete_after=self.settings[server.id]["delete_delay"])

    @cleanup.command(pass_context=True, name='self')
    async def cleanup_self(self, ctx, number: int, match_pattern: str = None):
        """Efface les messages du bot.

        Par défaut, tous les messages sont effacés. Si un troisième argument est spécifié,
        il sera utilisé pour la reconnaissance de motif: Si cela commence par r( aet se termine avec ),
        alors cela sera interpré comme un regex, et les messages qui correspondent seront supprimés.
        Sinon, il est utilisé dans un test de sous-chaîne simple.

        Quelques drapeaux regex utiles à inclure dans votre motif:
        Les points correspondent aux nouvelles lignes: (?s); Ignorer le cas: (?i); Les deux: (?si)
        """
        channel = ctx.message.channel
        server = ctx.message.server
        author = ctx.message.author
        is_bot = self.bot.user.bot

        # You can always delete your own messages, this is needed to purge
        can_mass_purge = False
        if type(author) is discord.Member:
            can_mass_purge = channel.permissions_for(server.me).manage_messages

        use_re = (match_pattern and match_pattern.startswith('r(') and
                  match_pattern.endswith(')'))

        if use_re:
            match_pattern = match_pattern[1:]  # strip 'r'
            match_re = re.compile(match_pattern)

            def content_match(c):
                return bool(match_re.match(c))
        elif match_pattern:
            def content_match(c):
                return match_pattern in c
        else:
            def content_match(_):
                return True

        def check(m):
            if m.author.id != self.bot.user.id:
                return False
            elif content_match(m.content):
                return True
            return False

        to_delete = []
        # Selfbot convenience, delete trigger message
        if author == self.bot.user:
            to_delete.append(ctx.message)
            number += 1

        tries_left = 5
        tmp = ctx.message

        while tries_left and len(to_delete) < number:
            async for message in self.bot.logs_from(channel, limit=100,
                                                    before=tmp):
                if len(to_delete) < number and check(message):
                    to_delete.append(message)
                tmp = message
            tries_left -= 1

        if is_bot and can_mass_purge:
            has_del = await self.mass_purge(to_delete)
        else:
            has_del = await self.slow_deletion(to_delete)

        log_msg = "{}({}) a effacé {} message(s) envoyé par le bot dans {}".format(
            author.name, author.id, len(to_delete), channel.name)
        if has_del: 
            case_number = await self.cases.new_case(server,
                            action="CLEANED",
                            mod=author,
                            user=None,
                            reason="dans le salon {}: {} message(s)".format(channel.name, number))
            log_msg = "CASE : " + str(case_number) + " --> " + log_msg
        else:
            log_msg = "NO CASE something went wrong --> " + log_msg
        logger.info(log_msg)
        await self.bot.say(log_msg, delete_after=self.settings[server.id]["delete_delay"])
 ### GROUPE CLEANUP END

 ### GROUPE FILTER START
    @commands.group(name="filter", pass_context=True, no_pm=True)
    @checks.mod_or_permissions()
    async def _filter(self, ctx):
        """Groupe: Ajoute/supprime des mots à filtrer

        Utiliser des guillemets pour ajouter/supprimer des phrases
        Renvoit la liste des mots filtréss'il y en a."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            server = ctx.message.server
            if server.id in self.filter:
                if self.filter[server.id]:
                    words = ", ".join(self.filter[server.id])
                    words = "Les mots filtrés dans ce serveur sont:\n" + words
                    try:
                        for page in pagify(words, delims=[" ", "\n"], shorten_by=8):
                            await self.bot.say(page, delete_after=self.settings[server.id]["delete_delay"])
                    except discord.Forbidden:
                        await self.bot.say("Je ne peux pas envoyer de message dans ce channel.")

    @_filter.command(name="add", pass_context=True)
    async def filter_add(self, ctx, *words: str):
        """Ajoute des mots à filter

        Utiliser les guillemets pour ajouter des phrases
        Exemples:
        filter add mot1 mot2 mot3
        filter add \"C'est une phrase\""""
        if words == ():
            await send_cmd_help(ctx)
            return
        server = ctx.message.server
        added = 0
        if server.id not in self.filter.keys():
            self.filter[server.id] = []
        for w in words:
            if w.lower() not in self.filter[server.id] and w != "":
                self.filter[server.id].append(w.lower())
                added += 1
        if added:
            dataIO.save_json(self._filter_path , self.filter)
            await self.bot.say("Mot(s) ajouté(s) au filtre.", delete_after=self.settings[server.id]["delete_delay"])
        else:
            await self.bot.say("Mot(s) déjà dans filtre.", delete_after=self.settings[server.id]["delete_delay"])

    @_filter.command(name="remove", pass_context=True)
    async def filter_remove(self, ctx, *words: str):
        """Supprime des mots du filtre

        Utiliser les guillemets pour supprimer des phrases
        Exemples:
        filter remove mot1 mot2 mot3
        filter remove \"C'est une phrase\""""
        if words == ():
            await send_cmd_help(ctx)
            return
        server = ctx.message.server
        removed = 0
        if server.id not in self.filter.keys():
            await self.bot.say("Il n'y a pas de mots filtrés dans ce server.", delete_after=self.settings[server.id]["delete_delay"])
            return
        for w in words:
            if w.lower() in self.filter[server.id]:
                self.filter[server.id].remove(w.lower())
                removed += 1
        if removed:
            dataIO.save_json(self._filter_path , self.filter)
            await self.bot.say("Mot(s) supprimé(s) au filtre.", delete_after=self.settings[server.id]["delete_delay"])
        else:
            await self.bot.say("Ces mots ne sont pas dans le filtre.", delete_after=self.settings[server.id]["delete_delay"])
 ### GROUPE FILTER END

    async def mass_purge(self, messages):
        while messages:
            if len(messages) > 1:
                try:
                    result = await self.bot.delete_messages(messages[:100])
                    messages = messages[100:]
                except discord.errors.HTTPException as e:
                    msg = await self.bot.say(e)
                    await asyncio.sleep(15)
                    await self.bot.delete_message(msg)
                    return False
            else:
                result = await self.bot.delete_message(messages[0])
                messages = []
            await asyncio.sleep(1.5)
        return True

    async def slow_deletion(self, messages):
        for message in messages:
            try:
                result = await self.bot.delete_message(message)
                return True
            except:
                return False

    def is_sel_or_superior(self, obj):
        if isinstance(obj, discord.Message):
            user = obj.author
        elif isinstance(obj, discord.Member):
            user = obj
        elif isinstance(obj, discord.Role):
            pass
        else:
            raise TypeError('Seuls les messages, membres ou rôles peuvent être passés')

        server = obj.server
        cocap_role = settings.get_server_cocap(server)
        admin_role = settings.get_server_admin(server)
        mod_role = settings.get_server_mod(server)
        sel_role = settings.get_server_sel(server)

        if isinstance(obj, discord.Role):
            return obj.name in [cocap_role, admin_role, mod_role, sel_role]

        if user.id == settings.owner:
            return True
        elif discord.utils.get(user.roles, name=cocap_role):
            return True
        elif discord.utils.get(user.roles, name=admin_role):
            return True
        elif discord.utils.get(user.roles, name=mod_role):
            return True
        elif discord.utils.get(user.roles, name=sel_role):
            return True
        else:
            return False

    def is_allowed_by_hierarchy(self, server, mod, user):
        toggled = self.settings[server.id]["respect_hierarchy"]
        is_special = mod == server.owner or mod.id == self.bot.settings.owner

        if not toggled:
            return True
        else:
            return mod.top_role.position > user.top_role.position or is_special

    async def check_filter(self, message):
        server = message.server
        if server.id in self.filter.keys():
            for w in self.filter[server.id]:
                if w in message.content.lower():
                    try:
                        await self.bot.delete_message(message)
                        logger.info("Message deleted in server {}."
                                    "Filtered: {}"
                                    "".format(server.id, w))
                        return True
                    except:
                        pass
        return False

    async def check_duplicates(self, message):
        server = message.server
        author = message.author
        if server.id not in self.settings:
            return False
        if self.settings[server.id]["delete_repeats"]:
            if not message.content:
                return False
            if author.id not in self.cache:
                self.cache[author.id] = deque(maxlen=3)
            self.cache.move_to_end(author.id)
            while len(self.cache) > 100000:
                self.cache.popitem(last=False)  # the oldest gets discarded
            self.cache[author.id].append(message.content)
            msgs = self.cache[author.id]
            if len(msgs) == 3 and msgs[0] == msgs[1] == msgs[2]:
                try:
                    await self.bot.delete_message(message)
                    return True
                except:
                    pass
        return False

    async def check_mention_spam(self, message):
        server = message.server
        author = message.author
        if server.id not in self.settings:
            return False
        if self.settings[server.id]["ban_mention_spam"]:
            max_mentions = self.settings[server.id]["ban_mention_spam"]
            mentions = set(message.mentions)
            if len(mentions) >= max_mentions:
                try:
                    self.temp_cache.add(author, server, "BAN")
                    await self.bot.ban(author, 1)
                except:
                    logger.info("Failed to ban member for mention spam in "
                                "server {}".format(server.id))
                else:
                    await self.cases.new_case(server,
                                        action="BAN",
                                        mod=server.me,
                                        user=author,
                                        reason="Mention spam (Autoban)")
                    return True
        return False

    async def on_message(self, message):
        author = message.author
        if message.server is None or self.bot.user == author:
            return

        valid_user = isinstance(author, discord.Member) and not author.bot

        #  Bots and mods or superior are ignored from the filter
        if not valid_user or self.is_sel_or_superior(message):
            return

        deleted = await self.check_filter(message)
        if not deleted:
            deleted = await self.check_duplicates(message)
        if not deleted:
            deleted = await self.check_mention_spam(message)

    async def on_member_ban(self, member):
        server = member.server
        if not self.temp_cache.check(member, server, "BAN"):
            await self.cases.new_case(server,
                                user=member,
                                action="BAN")

    async def on_member_unban(self, server, user):
        if not self.temp_cache.check(user, server, "UNBAN"):
            await self.cases.new_case(server,
                                user=user,
                                action="UNBAN")

    def are_overwrites_empty(self, overwrites):
        """Il n'y a actuellement pas de moyens plus propres pour vérifier si un
        objet PermissionOverwrite est vide"""
        original = [p for p in iter(overwrites)]
        empty = [p for p in iter(discord.PermissionOverwrite())]
        return original == empty

    async def reminditnow(self, author: discord.Member, *text: str):
        text = " ".join(text)
        seconds = (3600*24)+1
        future = int(time.time()+seconds)
        reminders = dataIO.load_json(self._reminders_path ) 
        reminders.append(
            {"ID": author.id, "NAME":author.name, "FUTURE": future, "TEXT": text})
        logger.info("{}({}) set a reminder.".format(author.name, author.id))
        dataIO.save_json(self._reminders_path, reminders)

    async def unkick(self, ctx, author: discord.Member, user: discord.Member, invitation):
        server = ctx.message.server
        self.temp_cache.add(user, server, "UNBAN")
        await self.cases.new_case(server,
                            action="UNHARDKICK",
                            mod=author,
                            user=user,
                            reason="Fin du délai.")
        msg = "\nUn utilisateur est UN-KICKED.\nMerci d'envoyer cette invitation: \n{}\n\n à @{} ({})\n".format(
            invitation, user, user.id)
        await self.reminditnow(author, msg)

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
    logger = logging.getLogger("mod")
    # Prevents the logger from being loaded again in case of module reload
    if logger.level == 0:
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(
            filename=mod_log_path, encoding='utf-8', mode='a')
        handler.setFormatter(
            logging.Formatter('%(asctime)s %(message)s', datefmt="[%d/%m/%Y %H:%M]"))
        logger.addHandler(handler)
    n = Mod(bot)
    bot.add_cog(n)
