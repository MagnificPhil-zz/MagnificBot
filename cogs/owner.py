import discord
import importlib
import traceback
import logging
import asyncio
import threading
import datetime
import glob
import os
import aiohttp

from collections import defaultdict

from discord.ext import commands
from __main__ import settings
from cogs.utils import checks
from cogs.utils.converters import GlobalUser
from cogs.utils.dataIO import dataIO
from cogs.utils.chat_formatting import pagify, box

class CogNotFoundError(Exception):
    pass


class CogLoadError(Exception):
    pass


class NoSetupError(CogLoadError):
    pass


class CogUnloadError(Exception):
    pass


class OwnerUnloadWithoutReloadError(CogUnloadError):
    pass

log = logging.getLogger("red")

disabled_commands_path  = "data/red/disabled_commands.json"
global_ignores_path     = "data/red/global_ignores.json"
ownersettings_path      = "data/red/ownersettings.json"
blacklist_path          = "data/mod/blacklist.json"
whitelist_path          = "data/mod/whitelist.json"

class Owner:
    """Toutes les commandes du propriétaire qui sont en rapport avec 
       les opérations de déboggage du bot."""
    _default_settings = {
        "ban_mention_spam": 5,
        "bot-cmd" : None,
        "bot-cmd-name" : None,
        "delete_delay" : -1,
        "delete_repeats": False,
        "idea-claim": None,
        "idea-claim-name": None,
        "mod-log": None,
        "mod-log-name" : None,
        "respect_hierarchy": True
    }
    _disabled_commands_path = disabled_commands_path
    _global_ignores_path    = global_ignores_path
    _ownersettings_path     = ownersettings_path
    _cogfile                = "data/red/cogs.json"

    def __init__(self, bot):
        self.disabled_commands  = dataIO.load_json(self._disabled_commands_path)
        self.global_ignores     = dataIO.load_json(self._global_ignores_path)
        settings                = dataIO.load_json(self._ownersettings_path)
        self.settings           = defaultdict(lambda: self._default_settings.copy(), settings)
        self.setowner_lock      = False
        self.bot                = bot
        self.server             = None
        self.session            = aiohttp.ClientSession(loop=self.bot.loop)

    def __unload(self):
        self.session.close()
    
    def whatServerImOn(self, ctx): #TODO : Try to not use this
        if not self.server:
            self.server=ctx.message.server
        else:
             self.server = None

 ### GROUP COMMAND COGS START ###
    @commands.group(name="cogs", pass_context=True, invoke_without_command=True)
    @checks.is_owner()
    async def _modul(self, ctx):
        """Groupe: Cogs"""
        self.whatServerImOn(ctx)
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)
            return

    @_modul.command(pass_context=True)
    async def load(self, ctx, *, cog_name: str):
        """Charge un module"""
        server=ctx.message.server
        module = cog_name.strip()
        if "cogs." not in module:
            module = "cogs." + module
        try:
            self._load_cog(module)
        except CogNotFoundError:
            await self.bot.say("Ce module ne peut être trouvé.", delete_after=self.settings[server.id]["delete_delay"])
        except CogLoadError as e:
            log.exception(e)
            traceback.print_exc()
            await self.bot.say("Il y a eu un problème lors du chargement du module. Vérifiez"
                               " votre console ou journaux pour plus d'information.", delete_after=self.settings[server.id]["delete_delay"])
        except Exception as e:
            log.exception(e)
            traceback.print_exc()
            await self.bot.say("Le module a été trouvé et peut-être chargé mais "
                               "quelque chose s'est mal passé. Vérifiez"
                               " votre console ou journaux pour plus d'information.", delete_after=self.settings[server.id]["delete_delay"])
        else:
            self.set_cog(module, True)
            await self.disable_commands()
            await self.bot.say("Le module {} a été chargé.".format(cog_name.strip()), delete_after=self.settings[server.id]["delete_delay"])
    
    @_modul.group(invoke_without_command=True, pass_context=True)
    async def unload(self, ctx, *, cog_name: str):
        """Unloads a cog

        Example: unload mod"""
        server = ctx.message.server
        module = cog_name.strip()
        if "cogs." not in module:
            module = "cogs." + module
        if not self._does_cogfile_exist(module):
            await self.bot.say("That cog file doesn't exist. I will not"
                               " turn off autoloading at start just in case"
                               " this isn't supposed to happen.", delete_after=self.settings[server.id]["delete_delay"])
        else:
            self.set_cog(module, False)
        try:  # No matter what we should try to unload it
            self._unload_cog(module)
        except OwnerUnloadWithoutReloadError:
            await self.bot.say("I cannot allow you to unload the Owner plugin"
                               " unless you are in the process of reloading.", delete_after=self.settings[server.id]["delete_delay"])
        except CogUnloadError as e:
            log.exception(e)
            traceback.print_exc()
            await self.bot.say('Unable to safely unload that cog.', delete_after=self.settings[server.id]["delete_delay"])
        else:
            await self.bot.say("The cog has been unloaded.", delete_after=self.settings[server.id]["delete_delay"])

    @unload.command(name="all", pass_context=True)
    async def unload_all(self, ctx):
        """Unloads all cogs"""
        server=ctx.message.server
        cogs = self._list_cogs()
        still_loaded = []
        for cog in cogs:
            self.set_cog(cog, False)
            try:
                self._unload_cog(cog)
            except OwnerUnloadWithoutReloadError:
                pass
            except CogUnloadError as e:
                log.exception(e)
                traceback.print_exc()
                still_loaded.append(cog)
        if still_loaded:
            still_loaded = ", ".join(still_loaded)
            await self.bot.say("I was unable to unload some cogs: "
                               "{}".format(still_loaded), delete_after=self.settings[server.id]["delete_delay"])
        else:
            await self.bot.say("All cogs are now unloaded.", delete_after=self.settings[server.id]["delete_delay"])

    @_modul.command(name="reload", pass_context=True)
    async def _reload(self, ctx, *, cog_name: str):
        """Reloads a cog

        Example: reload audio"""
        server = ctx.message.server
        module = cog_name.strip()
        if "cogs." not in module:
            module = "cogs." + module

        try:
            self._unload_cog(module, reloading=True)
        except:
            pass

        try:
            self._load_cog(module)
        except CogNotFoundError:
            await self.bot.say("That cog cannot be found.", delete_after=self.settings[server.id]["delete_delay"])
        except NoSetupError:
            await self.bot.say("That cog does not have a setup function.", delete_after=self.settings[server.id]["delete_delay"])
        except CogLoadError as e:
            log.exception(e)
            traceback.print_exc()
            await self.bot.say("That cog could not be loaded. Check your"
                               " console or logs for more information.", delete_after=self.settings[server.id]["delete_delay"])
        else:
            self.set_cog(module, True)
            await self.disable_commands()
            await self.bot.say("The cog has been reloaded.", delete_after=self.settings[server.id]["delete_delay"])

    @_modul.command(name="show", pass_context=True)
    async def _show_cogs(self, ctx):
        """Shows loaded/unloaded cogs"""
        # This function assumes that all cogs are in the cogs folder,
        # which is currently true.

        # Extracting filename from __module__ Example: cogs.owner
        server = ctx.message.server
        loaded = [c.__module__.split(".")[1] for c in self.bot.cogs.values()]
        # What's in the folder but not loaded is unloaded
        unloaded = [c.split(".")[1] for c in self._list_cogs()
                    if c.split(".")[1] not in loaded]

        if not unloaded:
            unloaded = ["None"]

        msg = ("+ Loaded\n"
               "{}\n\n"
               "- Unloaded\n"
               "{}"
               "".format(", ".join(sorted(loaded)),
                         ", ".join(sorted(unloaded)))
               )
        for page in pagify(msg, [" "], shorten_by=16):
            await self.bot.say(box(page.lstrip(" "), lang="diff"), delete_after=self.settings[server.id]["delete_delay"])
 ### GROUP COMMAND COGS END ###
    
 ### GROUP COMMAND SET START ###
    @commands.group(name="set", pass_context=True)
    @checks.is_owner()
    async def _set(self, ctx):
        """Groupe: Set"""
        if ctx.message.server is None:
            source = "via MP"
            await self.bot.say("Cette commande n'est pas authorisée {}".format(source))
            return
        if ctx.invoked_subcommand is None: 
            await self.bot.send_cmd_help(ctx)
            msg = self._get_owner_params(ctx)
            await self.bot.whisper(box(msg))
            return

    @_set.command(pass_context=True)
    async def owner(self, ctx):
        """Sets owner"""
        server = ctx.message.server
        if self.bot.settings.no_prompt is True:
            await self.bot.say("Console interaction is disabled. Start Red "
                               "without the `--no-prompt` flag to use this "
                               "command.", delete_after=self.settings[server.id]["delete_delay"])
            return
        if self.setowner_lock:
            await self.bot.say("A set owner command is already pending.", delete_after=self.settings[server.id]["delete_delay"])
            return

        if self.bot.settings.owner is not None:
            await self.bot.say(
            "The owner is already set. Remember that setting the owner "
            "to someone else other than who hosts the bot has security "
            "repercussions and is *NOT recommended*. Proceed at your own risk."
                , delete_after=self.settings[server.id]["delete_delay"])
            await asyncio.sleep(3)

        await self.bot.say("Confirm in the console that you're the owner.", delete_after=self.settings[server.id]["delete_delay"])
        self.setowner_lock = True
        t = threading.Thread(target=self._wait_for_answer,
                             args=(ctx.message.author,))
        t.start()

    @_set.command(pass_context=True)
    async def defaultselrole(self, ctx, *, role_name: str):
        """Défini le rôle par défaut de recruteur

           C'est utilisé si un role spécifique de serveur n'est pas défini."""
        server = ctx.message.server
        self.bot.settings.default_sel = role_name
        self.bot.settings.save_settings()
        await self.bot.say("le rôle par défaut de recruteur a été défini.", delete_after=self.settings[server.id]["delete_delay"])
    
    @_set.command(pass_context=True)
    async def defaultmodrole(self, ctx, *, role_name: str):
        """Sets the default mod role name

           This is used if a server-specific role is not set"""
        server = ctx.message.server
        self.bot.settings.default_mod = role_name
        self.bot.settings.save_settings()
        await self.bot.say("The default mod role name has been set.", delete_after=self.settings[server.id]["delete_delay"])

    @_set.command(pass_context=True)
    async def defaultadminrole(self, ctx, *, role_name: str):
        """Sets the default admin role name

           This is used if a server-specific role is not set"""
        server = ctx.message.server
        self.bot.settings.default_admin = role_name
        self.bot.settings.save_settings()
        await self.bot.say("The default admin role name has been set.", delete_after=self.settings[server.id]["delete_delay"])

    @_set.command(pass_context=True)
    async def defaultcocaprole(self, ctx, *, role_name: str):
        """Sets the default admin role name

           This is used if a server-specific role is not set"""
        server = ctx.message.server
        self.bot.settings.default_cocap = role_name
        self.bot.settings.save_settings()
        await self.bot.say("The default cocaptain role name has been set.", delete_after=self.settings[server.id]["delete_delay"])

    @_set.command(pass_context=True)
    async def prefix(self, ctx, *prefixes):
        """Sets Red's global prefixes

        Accepts multiple prefixes separated by a space. Enclose in double
        quotes if a prefix contains spaces.
        Example: set prefix ! $ ? "two words" """
        server = ctx.message.server
        if prefixes == ():
            await self.bot.send_cmd_help(ctx)
            return

        self.bot.settings.prefixes = sorted(prefixes, reverse=True)
        self.bot.settings.save_settings()
        log.debug("Setting global prefixes to:\n\t{}"
                  "".format(self.bot.settings.prefixes))

        p = "prefixes" if len(prefixes) > 1 else "prefix"
        await self.bot.say("Global {} set".format(p), delete_after=self.settings[server.id]["delete_delay"])

    @_set.command(pass_context=True)
    async def name(self, ctx, *, name):
        """Sets Red's name"""
        server = ctx.message.server
        name = name.strip()
        if name != "":
            try:
                await self.bot.edit_profile(self.bot.settings.password,
                                            username=name)
            except:
                await self.bot.say("Failed to change name. Remember that you"
                                   " can only do it up to 2 times an hour."
                                   "Use nicknames if you need frequent "
                                   "changes. {}set nickname"
                                   "".format(ctx.prefix), delete_after=self.settings[server.id]["delete_delay"])
            else:
                await self.bot.say("Done.", delete_after=self.settings[server.id]["delete_delay"])
        else:
            await self.bot.send_cmd_help(ctx)

    @_set.command(pass_context=True, no_pm=True)
    async def nickname(self, ctx, *, nickname=""):
        """Sets Red's nickname

        Leaving this empty will remove it."""
        server = ctx.message.server
        nickname = nickname.strip()
        if nickname == "":
            nickname = None
        try:
            await self.bot.change_nickname(ctx.message.server.me, nickname)
            await self.bot.say("Done.", delete_after=self.settings[server.id]["delete_delay"])
        except discord.Forbidden:
            await self.bot.say("I cannot do that, I lack the "
                               "\"Change Nickname\" permission.", delete_after=self.settings[server.id]["delete_delay"])

    @_set.command(pass_context=True)
    async def game(self, ctx, *, game=None):
        """Sets Red's playing status

        Leaving this empty will clear it."""

        server = ctx.message.server

        current_status = server.me.status if server is not None else None

        if game:
            game = game.strip()
            await self.bot.change_presence(game=discord.Game(name=game),
                                           status=current_status)
            log.debug('Status set to "{}" by owner'.format(game))
        else:
            await self.bot.change_presence(game=None, status=current_status)
            log.debug('status cleared by owner')
        await self.bot.say("Done.", delete_after=self.settings[server.id]["delete_delay"])

    @_set.command(pass_context=True)
    async def status(self, ctx, *, status=None):
        """Sets Red's status

        Statuses:
            online
            idle
            dnd
            invisible"""

        statuses = {
                    "online"    : discord.Status.online,
                    "idle"      : discord.Status.idle,
                    "dnd"       : discord.Status.dnd,
                    "invisible" : discord.Status.invisible
                   }

        server = ctx.message.server

        current_game = server.me.game if server is not None else None

        if status is None:
            await self.bot.change_presence(status=discord.Status.online,
                                           game=current_game)
            await self.bot.say("Status reset.", delete_after=self.settings[server.id]["delete_delay"])
        else:
            status = statuses.get(status.lower(), None)
            if status:
                await self.bot.change_presence(status=status,
                                               game=current_game)
                await self.bot.say("Status changed.", delete_after=self.settings[server.id]["delete_delay"])
            else:
                await self.bot.send_cmd_help(ctx)

    @_set.command(pass_context=True)
    async def stream(self, ctx, streamer=None, *, stream_title=None):
        """Sets Red's streaming status

        Leaving both streamer and stream_title empty will clear it."""

        server = ctx.message.server

        current_status = server.me.status if server is not None else None

        if stream_title:
            stream_title = stream_title.strip()
            if "twitch.tv/" not in streamer:
                streamer = "https://www.twitch.tv/" + streamer
            game = discord.Game(type=1, url=streamer, name=stream_title)
            await self.bot.change_presence(game=game, status=current_status)
            log.debug('Owner has set streaming status and url to "{}" and {}'.format(stream_title, streamer))
        elif streamer is not None:
            await self.bot.send_cmd_help(ctx)
            return
        else:
            await self.bot.change_presence(game=None, status=current_status)
            log.debug('stream cleared by owner')
        await self.bot.say("Done.", delete_after=self.settings[server.id]["delete_delay"])

    @_set.command(pass_context=True)
    async def avatar(self, ctx, url):
        """Sets Red's avatar"""
        server = ctx.message.server
        try:
            async with self.session.get(url) as r:
                data = await r.read()
            await self.bot.edit_profile(self.bot.settings.password, avatar=data)
            await self.bot.say("Done.", delete_after=self.settings[server.id]["delete_delay"])
            log.debug("changed avatar")
        except Exception as e:
            await self.bot.say("Error, check your console or logs for "
                               "more information.", delete_after=self.settings[server.id]["delete_delay"])
            log.exception(e)
            traceback.print_exc()

    @_set.command(name="token", pass_context=True)
    async def _token(self, ctx, token):
        """Sets Red's login token"""
        server = ctx.message.server
        if len(token) < 50:
            await self.bot.say("Invalid token.", delete_after=self.settings[server.id]["delete_delay"])
        else:
            self.bot.settings.token = token
            self.bot.settings.save_settings()
            await self.bot.say("Token set. Restart me.", delete_after=self.settings[server.id]["delete_delay"])
            log.debug("Token changed.")
 ### GROUP COMMAND SET END ###
 
 ### GROUP COMMAND SETSRV START ###
    @commands.group(name="setsrv", pass_context=True)
    @checks.is_owner()
    async def _setsrv(self, ctx):
        """Groupe: Set"""
        if ctx.message.server is None:
            source = "via MP"
            await self.bot.say("Cette commande n'est pas authorisée {}".format(source))
            return
        if ctx.invoked_subcommand is None: 
            await self.bot.send_cmd_help(ctx)
            msg = self._get_srv_owner_params(ctx)
            await self.bot.whisper(box(msg))
            return

    @_setsrv.command(name="role", pass_context=True, no_pm=True)
    async def getserverroles(self, ctx):
        """Affiche tous les rôles"""
        server = ctx.message.server
        if ctx.message.server is None:
            await self.bot.whisper("Cette commande ne fonctionne pas en MP.")
        else:
            roles = ctx.message.server.roles
            msg = "Les roles sont :\n"
            for role in roles:
                rolename = role.name if "everyone" not in role.name else " Everyone"
                msg += "\t" + rolename + " : " + role.id + "\n "  
            #await self.bot.whisper(msg)
            await self.bot.say(msg, delete_after=self.settings[server.id]["delete_delay"])
    

    @_setsrv.command(pass_context=True, no_pm=True)
    async def serverprefix(self, ctx, *prefixes):
        """Sets Red's prefixes for this server

        Accepts multiple prefixes separated by a space. Enclose in double
        quotes if a prefix contains spaces.
        Example: set serverprefix ! $ ? "two words"

        Issuing this command with no parameters will reset the server
        prefixes and the global ones will be used instead."""
        server = ctx.message.server

        if prefixes == ():
            self.bot.settings.set_server_prefixes(server, [])
            self.bot.settings.save_settings()
            current_p = ", ".join(self.bot.settings.prefixes)
            await self.bot.say("Server prefixes reset. Current prefixes: "
                               "`{}`".format(current_p), delete_after=self.settings[server.id]["delete_delay"])
            return

        prefixes = sorted(prefixes, reverse=True)
        self.bot.settings.set_server_prefixes(server, prefixes)
        self.bot.settings.save_settings()
        log.debug("Setting server's {} prefixes to:\n\t{}"
                  "".format(server.id, self.bot.settings.prefixes))

        p = "Prefixes" if len(prefixes) > 1 else "Prefix"
        await self.bot.say("{} set for this server.\n"
                           "To go back to the global prefixes, do"
                           " `{}set serverprefix` "
                           "".format(p, prefixes[0]), delete_after=self.settings[server.id]["delete_delay"])

    @_setsrv.command(name="rolecocap", pass_context=True, no_pm=True)
    async def _server_cocaprole(self, ctx, *, role: discord.Role):
        """Sets the cocaptain role for this server"""
        server = ctx.message.server
        if server.id not in self.bot.settings.servers:
            await self.bot.say("Remember to set adminrole & modrole & selrole  too.", delete_after=self.settings[server.id]["delete_delay"])
        self.bot.settings.set_server_cocap(server, role.name)
        await self.bot.say("Cocaptain role set to '{}'".format(role.name), delete_after=self.settings[server.id]["delete_delay"])

    @_setsrv.command(name="roleadmin", pass_context=True, no_pm=True)
    async def _server_adminrole(self, ctx, *, role: discord.Role):
        """Sets the admin role for this server"""
        server = ctx.message.server
        if server.id not in self.bot.settings.servers:
            await self.bot.say("Remember to set modrole & selrole  too.", delete_after=self.settings[server.id]["delete_delay"])
        self.bot.settings.set_server_admin(server, role.name)
        await self.bot.say("Admin role set to '{}'".format(role.name), delete_after=self.settings[server.id]["delete_delay"])

    @_setsrv.command(name="rolemod", pass_context=True, no_pm=True)
    async def _server_modrole(self, ctx, *, role: discord.Role):
        """Sets the mod role for this server"""
        server = ctx.message.server
        if server.id not in self.bot.settings.servers:
            await self.bot.say("Remember to set adminrole & selrole  too.", delete_after=self.settings[server.id]["delete_delay"])
        self.bot.settings.set_server_mod(server, role.name)
        await self.bot.say("Mod role set to '{}'".format(role.name), delete_after=self.settings[server.id]["delete_delay"])
    
    @_setsrv.command(name="rolesel", pass_context=True, no_pm=True)
    async def _server_selrole(self, ctx, *, role: discord.Role):
        """Sets the sel role for this server"""
        server = ctx.message.server
        if server.id not in self.bot.settings.servers:
            await self.bot.say("Remember to set adminrole & modrole too.", delete_after=self.settings[server.id]["delete_delay"])
        self.bot.settings.set_server_sel(server, role.name)
        await self.bot.say("Sel role set to '{}'".format(role.name), delete_after=self.settings[server.id]["delete_delay"])

    @_setsrv.command(name="delete_delay", pass_context=True)
    async def deletedelay(self, ctx, time: int=None):
        """Sets the delay until the bot removes the command message.
            Must be between -1 and 60.

        A delay of -1 means the bot will not remove the message."""
        server = ctx.message.server
        if time is not None:
            time = min(max(time, -1), 60)  # Enforces the time limits
            self.settings[server.id]["delete_delay"] = time
            if time == -1:
                await self.bot.say("Command deleting disabled.", delete_after=self.settings[server.id]["delete_delay"])
            else:
                await self.bot.say("Delete delay set to {}"
                                   " seconds.".format(time), delete_after=self.settings[server.id]["delete_delay"])
            dataIO.save_json(self._ownersettings_path, self.settings)
        else:
            try:
                delay = self.settings[server.id]["delete_delay"]
            except KeyError:
                await self.bot.say("Delete delay not yet set up on this"
                                   " server.", delete_after=self.settings[server.id]["delete_delay"])
            else:
                if delay != -1:
                    await self.bot.say("Bot will delete command messages after"
                                       " {} seconds. Set this value to -1 to"
                                       " stop deleting messages".format(delay), delete_after=self.settings[server.id]["delete_delay"])
                else:
                    await self.bot.say("I will not delete command messages.", delete_after=self.settings[server.id]["delete_delay"])

    @_setsrv.command(pass_context=True, no_pm=True)
    async def hierarchy(self, ctx):
        """Toggles role hierarchy check for mods / admins"""
        server = ctx.message.server
        toggled = self.settings[server.id].get("respect_hierarchy",
                                               self._default_settings["respect_hierarchy"])
        if not toggled:
            self.settings[server.id]["respect_hierarchy"] = True
            await self.bot.say("Role hierarchy will be checked when "
                               "moderation commands are issued.", delete_after=self.settings[server.id]["delete_delay"])
        else:
            self.settings[server.id]["respect_hierarchy"] = False
            await self.bot.say("Role hierarchy will be ignored when "
                               "moderation commands are issued.", delete_after=self.settings[server.id]["delete_delay"])
        dataIO.save_json(self._ownersettings_path, self.settings)

    @_setsrv.command(pass_context=True, no_pm=True)
    async def modlog(self, ctx, channel: discord.Channel=None):
        """Sets a channel as mod log

        Leaving the channel parameter empty will deactivate it"""
        server = ctx.message.server
        if channel:
            self.settings[server.id]["mod-log"] = channel.id
            self.settings[server.id]["mod-log-name"] = channel.name
            await self.bot.say("Mod events will be sent to {}"
                               "".format(channel.mention), delete_after=self.settings[server.id]["delete_delay"])
        else:
            self.settings[server.id]["mod-log"] = None
            self.settings[server.id]["mod-log-name"] = None
            await self.bot.say("Mod log deactivated.", delete_after=self.settings[server.id]["delete_delay"])
        dataIO.save_json(self._ownersettings_path, self.settings)

    @_setsrv.command(pass_context=True, no_pm=True)
    async def botcmd(self, ctx, channel: discord.Channel=None):
        """Sets a channel as bot command

        Leaving the channel parameter empty will deactivate it"""
        server = ctx.message.server
        if channel:
            self.settings[server.id]["botcmd"] = channel.id
            self.settings[server.id]["botcmd-name"] = channel.name
            await self.bot.say("Bot commands will only be permitted from {}"
                               "".format(channel.mention), delete_after=self.settings[server.id]["delete_delay"])
        else:
            self.settings[server.id]["botcmd"] = None
            self.settings[server.id]["botcmd-name"] = None
            await self.bot.say("Bot commands will be permitted from anywhere.", delete_after=self.settings[server.id]["delete_delay"])
        dataIO.save_json(self._ownersettings_path, self.settings)

    @_setsrv.command(pass_context=True, no_pm=True)
    async def ideaclaim(self, ctx, channel: discord.Channel=None):
        """Sets a channel as Idea Claim

        Leaving the channel parameter empty will deactivate it"""
        server = ctx.message.server
        if channel:
            self.settings[server.id]["idea-claim"] = channel.id
            self.settings[server.id]["idea-claim-name"] = channel.name
            await self.bot.say("Ideas and Suggestion channel set to {}"
                               "".format(channel.mention), delete_after=self.settings[server.id]["delete_delay"])
        else:
            self.settings[server.id]["ideaclaim"] = None
            self.settings[server.id]["idea-claim-name"] = None
            await self.bot.say("Ideas and Suggestion channel unset.", delete_after=self.settings[server.id]["delete_delay"])
        dataIO.save_json(self._ownersettings_path, self.settings)
 ### GROUP COMMAND SETSRV END ###

 ### GROUP COMMAND BWLIST START ###
    @commands.group(name="bwlist", pass_context=True, invoke_without_command=True)
    @checks.is_owner()
    async def _bwlist(self, ctx):
        """Groupe: Black & White List"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

  ### GROUP COMMAND BLACKLIST START ###
    @_bwlist.group(name="black", pass_context=True, invoke_without_command=True)
    @checks.is_owner()
    async def blacklist(self, ctx):
        """Groupe: blacklist

        Blacklisted users will be unable to issue commands"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @blacklist.command(name="add", pass_context=True)
    async def _blacklist_add(self, ctx, user: GlobalUser):
        """Adds user to Red's global blacklist"""
        server = ctx.message.server
        if user.id not in self.global_ignores["blacklist"]:
            self.global_ignores["blacklist"].append(user.id)
            self.save_global_ignores()
            await self.bot.say("User has been blacklisted.", delete_after=self.settings[server.id]["delete_delay"])
        else:
            await self.bot.say("User is already blacklisted.", delete_after=self.settings[server.id]["delete_delay"])

    @blacklist.command(name="remove", pass_context=True)
    async def _blacklist_remove(self, ctx, user: GlobalUser):
        """Removes user from Red's global blacklist"""
        server = ctx.message.server
        if user.id in self.global_ignores["blacklist"]:
            self.global_ignores["blacklist"].remove(user.id)
            self.save_global_ignores()
            await self.bot.say("User has been removed from the blacklist.", delete_after=self.settings[server.id]["delete_delay"])
        else:
            await self.bot.say("User is not blacklisted.", delete_after=self.settings[server.id]["delete_delay"])

    @blacklist.command(name="list", pass_context=True)
    async def _blacklist_list(self, ctx):
        """Lists users on the blacklist"""
        server = ctx.message.server
        blacklist = self._populate_list(self.global_ignores["blacklist"])

        if blacklist:
            for page in blacklist:
                await self.bot.say(box(page), delete_after=self.settings[server.id]["delete_delay"])
        else:
            await self.bot.say("The blacklist is empty.", delete_after=self.settings[server.id]["delete_delay"])

    @blacklist.command(name="clear", pass_context=True)
    async def _blacklist_clear(self, ctx):
        """Clears the global blacklist"""
        server = ctx.message.server
        self.global_ignores["blacklist"] = []
        self.save_global_ignores()
        await self.bot.say("Blacklist is now empty.", delete_after=self.settings[server.id]["delete_delay"])
  ### GROUP COMMAND BLACKLIST END ###

  ### GROUP COMMAND WHITELIST START ###
    @_bwlist.group(name="white", pass_context=True, invoke_without_command=True)
    @checks.is_owner()
    async def whitelist(self, ctx):
        """Groupe: Whitelist

        If the whitelist is not empty, only whitelisted users will
        be able to use Red"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @whitelist.command(name="add", pass_context=True)
    async def _whitelist_add(self, ctx, user: GlobalUser):
        """Adds user to Red's global whitelist"""
        server = ctx.message.server
        if user.id not in self.global_ignores["whitelist"]:
            if not self.global_ignores["whitelist"]:
                msg = "\nNon-whitelisted users will be ignored."
            else:
                msg = ""
            self.global_ignores["whitelist"].append(user.id)
            self.save_global_ignores()
            await self.bot.say("User has been whitelisted." + msg, delete_after=self.settings[server.id]["delete_delay"])
        else:
            await self.bot.say("User is already whitelisted.", delete_after=self.settings[server.id]["delete_delay"])

    @whitelist.command(name="remove", pass_context=True)
    async def _whitelist_remove(self, ctx, user: GlobalUser):
        """Removes user from Red's global whitelist"""
        server = ctx.message.server
        if user.id in self.global_ignores["whitelist"]:
            self.global_ignores["whitelist"].remove(user.id)
            self.save_global_ignores()
            await self.bot.say("User has been removed from the whitelist.", delete_after=self.settings[server.id]["delete_delay"])
        else:
            await self.bot.say("User is not whitelisted.", delete_after=self.settings[server.id]["delete_delay"])

    @whitelist.command(name="list", pass_context=True)
    async def _whitelist_list(self, ctx):
        """Lists users on the whitelist"""
        server = ctx.message.server
        whitelist = self._populate_list(self.global_ignores["whitelist"])

        if whitelist:
            for page in whitelist:
                await self.bot.say(box(page), delete_after=self.settings[server.id]["delete_delay"])
        else:
            await self.bot.say("The whitelist is empty.", delete_after=self.settings[server.id]["delete_delay"])

    @whitelist.command(name="clear", pass_context=True)
    async def _whitelist_clear(self, ctx):
        """Clears the global whitelist"""
        server = ctx.message.server
        self.global_ignores["whitelist"] = []
        self.save_global_ignores()
        await self.bot.say("Whitelist is now empty.", delete_after=self.settings[server.id]["delete_delay"])
  ### GROUP COMMAND WHITELIST END ###
 ### GROUP COMMAND BWLIST END ###

 ### GROUP COMMAND BOT START ###
    @commands.group(name="bot", pass_context=True)
    @checks.is_owner()
    async def _srv(self, ctx):
        """Groupe: Bot"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)
            return

    @_srv.command(pass_context=True)
    async def shutdown(self, ctx, silently : bool=False):
        """Arrête le Bot"""
        server = ctx.message.server
        wave = "\N{WAVING HAND SIGN}"
        skin = "\N{EMOJI MODIFIER FITZPATRICK TYPE-3}"
        try: # We don't want missing perms to stop our shutdown
            if not silently:
                await self.bot.say("Shutting down... " + wave + skin, delete_after=self.settings[server.id]["delete_delay"])
        except:
            pass
        await self.bot.shutdown()

    @_srv.command(pass_context=True)
    async def restart(self, ctx, silently : bool=False):
        """Essaye de redémarre le bot

        Le bot s'arrête avec le code de sortie 26
        Le redémarrage n'est pas garanti: Cela doit être
        par le gestionnaire de process utilisé."""
        server = ctx.message.server
        try:
            if not silently:
                await self.bot.say("Redémarrage...", delete_after=self.settings[server.id]["delete_delay"])
        except:
            pass
        await self.bot.shutdown(restart=True)

    @_srv.command(pass_context=True)
    async def join(self, ctx):
        """Shows Red's invite URL"""
        server = ctx.message.server
        if self.bot.user.bot:
            await self.bot.whisper("Invite URL: " + self.bot.oauth_url)
        else:
            await self.bot.say("I'm not a bot account. I have no invite URL.", delete_after=self.settings[server.id]["delete_delay"])

    @_srv.command(pass_context=True, no_pm=True)
    async def leave(self, ctx):
        """Leaves server"""
        message = ctx.message
        server = ctx.message.server
        await self.bot.say("Are you sure you want me to leave this server?\n Type yes to confirm.", delete_after=self.settings[server.id]["delete_delay"])
        response = await self.bot.wait_for_message(author=message.author)

        if response.content.lower().strip() == "yes":
            await self.bot.say("Alright. Bye :wave:", delete_after=self.settings[server.id]["delete_delay"])
            log.debug('Leaving "{}"'.format(message.server.name))
            await self.bot.leave_server(message.server)
        else:
            await self.bot.say("Ok I'll stay here then.", delete_after=self.settings[server.id]["delete_delay"])

    @_srv.command(pass_context=True)
    async def servers(self, ctx):
        """Lists and allows to leave servers"""
        owner = ctx.message.author
        server = ctx.message.server
        servers = sorted(list(self.bot.servers),
                         key=lambda s: s.name.lower())
        msg = ""
        for i, server in enumerate(servers):
            msg += "{}: {}\n".format(i, server.name)
        msg += "\nTo leave a server just type its number."

        for page in pagify(msg, ['\n']):
            await self.bot.say(page, delete_after=self.settings[server.id]["delete_delay"])

        while msg is not None:
            msg = await self.bot.wait_for_message(author=owner, timeout=15)
            try:
                msg = int(msg.content)
                await self.leave_confirmation(servers[msg], owner, ctx)
                break
            except (IndexError, ValueError, AttributeError):
                pass

    @_srv.command(pass_context=True)
    async def info(self, ctx):
        """Shows info about Red"""
        server = ctx.message.server
        author_repo = "https://github.com/Twentysix26"
        red_repo = author_repo + "/Red-DiscordBot"
        server_url = "https://discord.gg/red"
        dpy_repo = "https://github.com/Rapptz/discord.py"
        python_url = "https://www.python.org/"
        since = datetime.datetime(2016, 1, 2, 0, 0)
        days_since = (datetime.datetime.utcnow() - since).days
        dpy_version = "[{}]({})".format(discord.__version__, dpy_repo)
        py_version = "[{}.{}.{}]({})".format(*os.sys.version_info[:3],
                                             python_url)

        owner_set = self.bot.settings.owner is not None
        owner = self.bot.settings.owner if owner_set else None
        if owner:
            owner = discord.utils.get(self.bot.get_all_members(), id=owner)
            if not owner:
                try:
                    owner = await self.bot.get_user_info(self.bot.settings.owner)
                except:
                    owner = None
        if not owner:
            owner = "Unknown"

        about = (
            "This is an instance of [Red, an open source Discord bot]({}) "
            "created by [Twentysix]({}) and improved by many.\n\n"
            "Red is backed by a passionate community who contributes and "
            "creates content for everyone to enjoy. [Join us today]({}) "
            "and help us improve!\n\n"
            "".format(red_repo, author_repo, server_url))

        embed = discord.Embed(colour=discord.Colour.red())
        embed.add_field(name="Instance owned by", value=str(owner))
        embed.add_field(name="Python", value=py_version)
        embed.add_field(name="discord.py", value=dpy_version)
        embed.add_field(name="About Red", value=about, inline=False)
        embed.set_footer(text="Bringing joy since 02 Jan 2016 (over "
                         "{} days ago!)".format(days_since))

        try:
            await self.bot.say(embed=embed, delete_after=self.settings[server.id]["delete_delay"])
        except discord.HTTPException:
            await self.bot.say("I need the `Embed links` permission "
                               "to send this", delete_after=self.settings[server.id]["delete_delay"])

    @_srv.command(pass_context=True)
    async def uptime(self, ctx):
        """Shows Red's uptime"""
        server = ctx.message.server
        since = self.bot.uptime.strftime("%Y-%m-%d %H:%M:%S")
        passed = self.get_bot_uptime()
        await self.bot.say("Been up for: **{}** (since {} UTC)"
                           "".format(passed, since), delete_after=self.settings[server.id]["delete_delay"])

    @_srv.command(pass_context=True)
    async def version(self, ctx):
        """Shows Red's current version"""
        server = ctx.message.server
        response = self.bot.loop.run_in_executor(None, self._get_version)
        result = await asyncio.wait_for(response, timeout=10)
        try:
            await self.bot.say(embed=result, delete_after=self.settings[server.id]["delete_delay"])
        except discord.HTTPException:
            await self.bot.say("I need the `Embed links` permission "
                               "to send this", delete_after=self.settings[server.id]["delete_delay"])
 ### GROUP COMMAND BOT END ###

 ### GROUP COMMAND COMMAND START ###
    @commands.group(name="cmd", pass_context=True)
    @checks.is_owner()
    async def _comd(self, ctx):
        """Groupe: Cmd
        
        Sans sous-commande donne la liste des commandes désactivées"""
        if ctx.invoked_subcommand is None:
            server = ctx.message.server
            await self.bot.send_cmd_help(ctx)
            await self.bot.say("Pas de commande désactivée.", delete_after=self.settings[server.id]["delete_delay"])
            if self.disabled_commands:
                msg = "Commande(s) désactivée(s):\n```xl\n"
                for cmd in self.disabled_commands:
                    msg += "{}, ".format(cmd)
                msg = msg.strip(", ")
                await self.bot.say("{}```".format(msg), delete_after=self.settings[server.id]["delete_delay"])
            return

    @_comd.command(pass_context=True)
    async def disable(self, ctx, *, command):
        """Désactive des commandes/sous-commandes"""
        server = ctx.message.server
        comm_obj = await self.get_command(command)
        if comm_obj is KeyError:
            await self.bot.say("That command doesn't seem to exist.", delete_after=self.settings[server.id]["delete_delay"])
        elif comm_obj is False:
            await self.bot.say("You cannot disable owner restricted commands.", delete_after=self.settings[server.id]["delete_delay"])
        else:
            comm_obj.enabled = False
            comm_obj.hidden = True
            self.disabled_commands.append(command)
            self.save_disabled_commands()
            await self.bot.say("Command has been disabled.", delete_after=self.settings[server.id]["delete_delay"])

    @_comd.command(pass_context=True)
    async def enable(self, ctx, *, command):
        """Enables commands/subcommands"""
        server = ctx.message.server
        if command in self.disabled_commands:
            self.disabled_commands.remove(command)
            self.save_disabled_commands()
            await self.bot.say("Command enabled.", delete_after=self.settings[server.id]["delete_delay"])
        else:
            await self.bot.say("That command is not disabled.", delete_after=self.settings[server.id]["delete_delay"])
            return
        try:
            comm_obj = await self.get_command(command)
            comm_obj.enabled = True
            comm_obj.hidden = False
        except:  # In case it was in the disabled list but not currently loaded
            pass # No point in even checking what returns
 ### GROUP COMMAND COMMAND END ###

 ### GROUP COMMAND DVP END ###
    @commands.group(name="dvp", pass_context=True)
    @checks.is_owner()
    async def _dvp(self, ctx):
        """Groupe: Dvp"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)
            return

    @_dvp.command(pass_context=True)
    async def traceback(self, ctx, public: bool=False):
        """Sends to the owner the last command exception that has occurred

        If public (yes is specified), it will be sent to the chat instead"""
        if not public:
            destination = ctx.message.author
        else:
            destination = ctx.message.channel
        server = ctx.message.server
        if self.bot._last_exception:
            for page in pagify(self.bot._last_exception):
                await self.bot.send_message(destination, box(page, lang="py"))
        else:
            await self.bot.say("No exception has occurred yet.", delete_after=self.settings[server.id]["delete_delay"])

    @_dvp.command(pass_context=True)
    async def debug(self, ctx, *, code):
        """Evaluates code"""
        def check(m):
            if m.content.strip().lower() == "more":
                return True

        author = ctx.message.author
        channel = ctx.message.channel
        server = ctx.message.server

        code = code.strip('` ')
        result = None

        global_vars = globals().copy()
        global_vars['bot'] = self.bot
        global_vars['ctx'] = ctx
        global_vars['message'] = ctx.message
        global_vars['author'] = ctx.message.author
        global_vars['channel'] = ctx.message.channel
        global_vars['server'] = ctx.message.server

        try:
            result = eval(code, global_vars, locals())
        except Exception as e:
            await self.bot.say(box('{}: {}'.format(type(e).__name__, str(e)),
                                   lang="py"), delete_after=self.settings[server.id]["delete_delay"])
            return

        if asyncio.iscoroutine(result):
            result = await result

        result = str(result)

        if not ctx.message.channel.is_private:
            censor = (self.bot.settings.email,
                      self.bot.settings.password,
                      self.bot.settings.token)
            r = "[EXPUNGED]"
            for w in censor:
                if w is None or w == "":
                    continue
                result = result.replace(w, r)
                result = result.replace(w.lower(), r)
                result = result.replace(w.upper(), r)

        result = list(pagify(result, shorten_by=16))

        for i, page in enumerate(result):
            if i != 0 and i % 4 == 0:
                last = await self.bot.say("There are still {} messages. "
                                          "Type `more` to continue."
                                          "".format(len(result) - (i+1)), delete_after=self.settings[server.id]["delete_delay"])
                msg = await self.bot.wait_for_message(author=author,
                                                      channel=channel,
                                                      check=check,
                                                      timeout=10)
                if msg is None:
                    try:
                        await self.bot.delete_message(last)
                    except:
                        pass
                    finally:
                        break
            await self.bot.say(box(page, lang="py"), delete_after=self.settings[server.id]["delete_delay"])
 ### GROUP COMMAND DVP END ###

 ### COMMANDES INTERNES START ###
    async def leave_confirmation(self, server, owner, ctx):
        await self.bot.say("Are you sure you want me "
                           "to leave {}? (yes/no)".format(server.name), delete_after=self.settings[server.id]["delete_delay"])

        msg = await self.bot.wait_for_message(author=owner, timeout=15)

        if msg is None:
            await self.bot.say("I guess not.", delete_after=self.settings[server.id]["delete_delay"])
        elif msg.content.lower().strip() in ("yes", "y"):
            await self.bot.leave_server(server)
            if server != ctx.message.server:
                await self.bot.say("Done.", delete_after=self.settings[server.id]["delete_delay"])
        else:
            await self.bot.say("Alright then.", delete_after=self.settings[server.id]["delete_delay"])

    async def get_command(self, command):
        command = command.split()
        try:
            comm_obj = self.bot.commands[command[0]]
            if len(command) > 1:
                command.pop(0)
                for cmd in command:
                    comm_obj = comm_obj.commands[cmd]
        except KeyError:
            return KeyError
        for check in comm_obj.checks:
            if hasattr(check, "__name__") and check.__name__ == "is_owner_check":
                return False
        return comm_obj

    async def disable_commands(self):  # runs at boot
        for cmd in self.disabled_commands:
            cmd_obj = await self.get_command(cmd)
            try:
                cmd_obj.enabled = False
                cmd_obj.hidden = True
            except:
                pass

    def _get_owner_params(self, ctx):
        server = ctx.message.server
        roles = settings.get_server(server).copy()
        _settings = {**self.settings[server.id], **roles}
        if "DEF_COCAP_ROLE" not in _settings:
            _settings["DEF_COCAP_ROLE"] = self.bot.settings.default_cocap
        if  "DEF_ADMIN_ROLE" not in _settings:
            _settings["DEF_ADMIN_ROLE"] = self.bot.settings.default_admin
        if "DEF_MOD_ROLE" not in _settings:
            _settings["DEF_MOD_ROLE"] = self.bot.settings.default_mod
        if "DEF_SEL_ROLE" not in _settings:
            _settings["DEF_SEL_ROLE"] = self.bot.settings.default_sel
        if "prefix" not in _settings:
            _settings["prefix"] = str(self.bot.settings.prefixes)
        if "token" not in _settings:
            _settings["token"] = self.bot.settings.token

        msg = ("OwnerSET:\n"
                    "\tDEFAULT ROLES\n"
                        "\t\tCocap: {DEF_COCAP_ROLE}\n"
                        "\t\tAdmin: {DEF_ADMIN_ROLE}\n"
                        "\t\tMod: {DEF_MOD_ROLE}\n"
                        "\t\tSel: {DEF_SEL_ROLE}\n"
                    "\tBOT:\n"
                        "\t\tPrefix: {prefix}\n"
                        "\t\tToken: {token}\n"
                "".format(**_settings))
        return msg

    def _get_srv_owner_params(self, ctx):
        server = ctx.message.server
        roles = settings.get_server(server).copy()
        _settings = {**self.settings[server.id], **roles}
        if "respect_hierarchy" not in _settings:
            _settings["respect_hierarchy"] = self._default_settings["respect_hierarchy"]
        if "delete_delay" not in _settings or "delete_delay" == -1:
            _settings["delete_delay"] = "Disabled"
        # if _settings["delete_delay"] == -1:
        #     _settings["delete_delay"] = "Disabled"
        if "name" not in _settings:
            _settings["name"] = str(self.bot.user)
        if "status" not in _settings:
            _settings["status"] = server.me.status if server is not None else "None"
        if "game" not in _settings:
            _settings["game"] = server.me.game if server is not None else "None"
        if "owner" not in _settings:
            _settings["owner"] = discord.utils.get(self.bot.get_all_members(),
                                                    id=self.bot.settings.owner)
        if "serverprefix" not in _settings:
            _settings["serverprefix"] = str(", ".join(self.bot.settings.prefixes))

        msg = ("ServerOwnerSET:\n"
                    "\tROLES:\n"
                        "\t\tCoCap: {COCAP_ROLE}\n"
                        "\t\tAdmin: {ADMIN_ROLE}\n"
                        "\t\tMod: {MOD_ROLE}\n"
                        "\t\tSel: {SEL_ROLE}\n"
                    "\tBOT:\n"
                        "\t\tName: {name}\n"
                        "\t\tStatus: {status}\n"
                        "\t\tGame: {game}\n"
                        "\t\tOwner: {owner}\n"
                        "\t\tServerPrefix: {serverprefix}\n"
                    "\tDIVERS:\n"
                        "\t\tMod-log: {mod-log-name}\n"
                        "\t\tIdea-Claim: {idea-claim-name}\n"
                        "\t\tBotcmd: {botcmd-name}\n"
                        "\t\tDelete delay: {delete_delay}\n"
                        "\t\tRespects hierarchy: {respect_hierarchy}\n"
               "OtherSET:\n"
                    "\tDelete repeats: {delete_repeats}\n"
                    "\tBan mention spam: {ban_mention_spam}\n"
                "".format(**_settings))
        return msg

    def _populate_list(self, _list):
        """Used for both whitelist / blacklist

        Returns a paginated list"""
        users = []
        total = len(_list)

        for user_id in _list:
            user = discord.utils.get(self.bot.get_all_members(), id=user_id)
            if user:
                users.append("{} ({})".format(user, user.id))

        if users:
            not_found = total - len(users)
            users = ", ".join(users)
            if not_found:
                users += "\n\n ... and {} users I could not find".format(not_found)
            return list(pagify(users, delims=[" ", "\n"]))

        return []

    def _load_cog(self, cogname):
        if not self._does_cogfile_exist(cogname):
            raise CogNotFoundError(cogname)
        try:
            mod_obj = importlib.import_module(cogname)
            importlib.reload(mod_obj)
            self.bot.load_extension(mod_obj.__name__)
        except SyntaxError as e:
            raise CogLoadError(*e.args)
        except:
            raise

    def set_cog(self, cog, value):  #TODO: add the by server conf
        data = dataIO.load_json(self._cogfile)
        data[cog] = value
        dataIO.save_json(self._cogfile, data)

    def _unload_cog(self, cogname, reloading=False):
        if not reloading and cogname == "cogs.owner":
            raise OwnerUnloadWithoutReloadError(
                "Can't unload the owner plugin :P")
        try:
            self.bot.unload_extension(cogname)
        except:
            raise CogUnloadError

    def _list_cogs(self):
        cogs = [os.path.basename(f) for f in glob.glob("cogs/*.py")]
        return ["cogs." + os.path.splitext(f)[0] for f in cogs]

    def _does_cogfile_exist(self, module):
        if "cogs." not in module:
            module = "cogs." + module
        if module not in self._list_cogs():
            return False
        return True

    def _wait_for_answer(self, author):
        print(author.name + " requested to be set as owner. If this is you, "
              "type 'yes'. Otherwise press enter.")
        print()
        print("*DO NOT* set anyone else as owner. This has security "
              "repercussions.")

        choice = "None"
        while choice.lower() != "yes" and choice == "None":
            choice = input("> ")

        if choice == "yes":
            self.bot.settings.owner = author.id
            self.bot.settings.save_settings()
            print(author.name + " has been set as owner.")
            self.setowner_lock = False
            self.owner.hidden = True
        else:
            print("The set owner request has been ignored.")
            self.setowner_lock = False

    def _get_version(self):
        if not os.path.isdir(".git"):
            msg = "This instance of Red hasn't been installed with git."
            e = discord.Embed(title=msg,
                              colour=discord.Colour.red())
            return e

        commands = " && ".join((
            r'git config --get remote.origin.url',         # Remote URL
            r'git rev-list --count HEAD',                  # Number of commits
            r'git rev-parse --abbrev-ref HEAD',            # Branch name
            r'git show -s -n 3 HEAD --format="%cr|%s|%H"'  # Last 3 commits
        ))
        result = os.popen(commands).read()
        url, ncommits, branch, commits = result.split("\n", 3)
        if url.endswith(".git"):
            url = url[:-4]
        if url.startswith("git@"):
            domain, _, resource = url[4:].partition(':')
            url = 'https://{}/{}'.format(domain, resource)
        repo_name = url.split("/")[-1]

        embed = discord.Embed(title="Updates of " + repo_name,
                              description="Last three updates",
                              colour=discord.Colour.red(),
                              url="{}/tree/{}".format(url, branch))

        for line in commits.split('\n'):
            if not line:
                continue
            when, commit, chash = line.split("|")
            commit_url = url + "/commit/" + chash
            content = "[{}]({}) - {} ".format(chash[:6], commit_url, commit)
            embed.add_field(name=when, value=content, inline=False)

        embed.set_footer(text="Total commits: " + ncommits)

        return embed

    def get_bot_uptime(self, *, brief=False):
        # Courtesy of Danny
        now = datetime.datetime.utcnow()
        delta = now - self.bot.uptime
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        if not brief:
            if days:
                fmt = '{d} days, {h} hours, {m} minutes, and {s} seconds'
            else:
                fmt = '{h} hours, {m} minutes, and {s} seconds'
        else:
            fmt = '{h}h {m}m {s}s'
            if days:
                fmt = '{d}d ' + fmt

        return fmt.format(d=days, h=hours, m=minutes, s=seconds)

    def save_global_ignores(self):
        dataIO.save_json(self._global_ignores_path, self.global_ignores)

    def save_disabled_commands(self):
        dataIO.save_json(self._disabled_commands_path, self.disabled_commands)
 ### COMMANDES INTERNES END ###

def _import_old_data(data):
    """Migration from mod.py"""
    try:
        data["blacklist"] = dataIO.load_json(blacklist_path)
    except FileNotFoundError:
        pass

    try:
        data["whitelist"] = dataIO.load_json(whitelist_path)
    except FileNotFoundError:
        pass

    return data

def check_files():
    if not os.path.isfile(disabled_commands_path):
        print("Creating empty disabled_commands.json...")
        dataIO.save_json(disabled_commands_path, [])
    
    if not os.path.isfile(ownersettings_path):
        print("Creating empty owner_settingss.json...")
        dataIO.save_json(ownersettings_path, [])

    if not os.path.isfile(global_ignores_path):
        print("Creating empty global_ignores.json...")
        data = {"blacklist": [], "whitelist": []}
        try:
            data = _import_old_data(data)
        except Exception as e:
            log.error("Failed to migrate blacklist / whitelist data from "
                      "mod.py: {}".format(e))

        dataIO.save_json(global_ignores_path, data)

def setup(bot):
    check_files()
    n = Owner(bot)
    bot.add_cog(n)
