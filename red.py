import asyncio
import os
import sys
sys.path.insert(0, "lib")
import logging
import logging.handlers
import traceback
import datetime
import subprocess

try:
    from discord.ext import commands
    import discord  
except ImportError:
    print("Discord.py n'est pas installé.\n"
          "Consultez le guide votre OS "
          "et faire toutes les étapes dans l'ordre.\n"
          "https://twentysix26.github.io/Red-Docs/\n")
    sys.exit(1)

from collections import Counter
from io import TextIOWrapper

from cogs.utils.settings import Settings
from cogs.utils.dataIO import dataIO
from cogs.utils.chat_formatting import inline


description     = "MagnificBot - Un bot basé sur Red de 26 par MagnificPhil"
folders         = ("data", "data/red", "cogs", "cogs/utils")
redlog          = 'data/red/red.log'
discordlog      = 'data/red/discord.log'
cogfile         = "data/red/cogs.json"
default_cogs    = ("admin", "audio", "customcom", "economy",
                    "general", "mod", "sel", "streams")

# define Python user-defined exceptions
class Error(Exception):
    """Base class for other exceptions"""
    pass

class ForbiddenToPassCommandHere(Error):
    """Raised when comands are passed in a channel where it is forbidden"""
    pass
class OnlyBotCommandChannelAllowed(Error):
    """Raised when a messsage is not a command in the bot command channel"""
    pass


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):

        def prefix_manager(bot, message):
            """
            Retourne les préfixes du message du serveur si défini.
            Si aucun n'est défini ou si le message du server est None
            cela renverra les préfixes globaux à la place.

            Nécessite une instance Bot et un objet Message
            passé en arguments.
            """
            return bot.settings.get_prefixes(message.server)

        self.counter = Counter()
        self.uptime = datetime.datetime.utcnow()  # Refreshed before login
        self._message_modifiers = []
        self.settings = Settings()
        self._intro_displayed = False
        self._shutdown_mode = None
        self.logger = set_logger(self)
        self._last_exception = None
        self.oauth_url = ""
        self.printdebug = True
        

        if 'self_bot' in kwargs:
            self.settings.self_bot = kwargs['self_bot']
        else:
            kwargs['self_bot'] = self.settings.self_bot
            if self.settings.self_bot:
                kwargs['pm_help'] = False
        super().__init__(*args, command_prefix=prefix_manager, **kwargs)

    async def check_is_command(self, message):
        _internal_channel = message.channel
        _internal_author = message.author

        view = commands.view.StringView(message.content)

        prefix = await bot._get_prefix(message)
        invoked_prefix = prefix

        if not isinstance(prefix, (tuple, list)):
            if not view.skip_string(prefix):
                return False
        else:
            invoked_prefix = discord.utils.find(view.skip_string, prefix)
            if invoked_prefix is None:
                return False


        invoker = view.get_word()
        # tmp = {
        #     'bot': self,
        #     'invoked_with': invoker,
        #     'message': message,
        #     'view': view,
        #     'prefix': invoked_prefix
        # }
        # ctx = commands.Context(**tmp)
        # del tmp

        if invoker in self.commands:
            return True
            # command = self.commands[invoker]
            # self.dispatch('command', command, ctx)
            # try:
            #     yield from command.invoke(ctx)
            # except CommandError as e:
            #     ctx.command.dispatch_error(e, ctx)
            # else:
            #     self.dispatch('command_completion', command, ctx)
        elif invoker:
            return False
            # exc = CommandNotFound('Command "{}" is not found'.format(invoker))
            # self.dispatch('command_error', exc, ctx)

    async def check_for_passthru_command(self, message):
        allowed_passthru_cmd = ('cleanup', 'mute', 'unmute', 'candidate')
        view = commands.view.StringView(message.content)
        # if self._skip_check(message.author, self.user):
        #     return

        prefix = await bot._get_prefix(message)
        invoked_prefix = prefix

        if not isinstance(prefix, (tuple, list)):
            if not view.skip_string(prefix):
                return
        else:
            invoked_prefix = discord.utils.find(view.skip_string, prefix)
            if invoked_prefix is None:
                return

        invoker = view.get_word()

        if invoker in allowed_passthru_cmd:
            return True
        else:
            return False

    async def send_message(self, *args, **kwargs):
        if self._message_modifiers:
            if "content" in kwargs:
                pass
            elif len(args) == 2:
                args = list(args)
                kwargs["content"] = args.pop()
            else:
                return await super().send_message(*args, **kwargs)

            content = kwargs['content']
            for m in self._message_modifiers:
                try:
                    content = str(m(content))
                except:   # Faulty modifiers should not
                    pass  # break send_message
            kwargs['content'] = content

        return await super().send_message(*args, **kwargs)

    async def shutdown(self, *, restart=False):
        """Quitte le Bot gracieusement avec le code de sortie 0

        Si restart a la valeur True, le code de sortie sera 26
        Le lanceur redémarre automatiquement le Bot lorsque cela se produit"""
        self._shutdown_mode = not restart
        await self.logout()

    def add_message_modifier(self, func):
        """
        Ajoute un modificateur de message au bot

        Un modificateur de message est un appelable qui accepte un message
        contenu comme premier argument positionnel.
        Avant qu'un message ne soit envoyé, la fonction sera appelé avec
        le contenu du message comme seul argument. Le contenu du message 
        sera ensuite modifé pour être la seule valeur de retour de la 
        fonction.
		Les exceptions lancées par l'appelable seront captées et
        réduites au silence.
        """
        if not callable(func):
            raise TypeError("La fonction de modificataeur de message "
                            "doit être un appelable.")

        self._message_modifiers.append(func)

    def remove_message_modifier(self, func):
        """Supprime un modificateur de message du bot"""
        if func not in self._message_modifiers:
            raise RuntimeError("Fonction non présente dans le "
                               "modificateur de message.")

        self._message_modifiers.remove(func)

    def clear_message_modifiers(self):
        """Supprime tous les modificateurs de message du bot"""
        self._message_modifiers.clear()

    async def send_cmd_help(self, ctx):
        print("went here 1")
        if ctx.invoked_subcommand:
            print("went here 2")
            pages = self.formatter.format_help_for(ctx, ctx.invoked_subcommand)
            for page in pages:
                await self.send_message(ctx.message.channel, page)
        else:
            print("went here 3")
            pages = self.formatter.format_help_for(ctx, ctx.command)
            for page in pages:
                await self.send_message(ctx.message.channel, page)

    def user_allowed(self, message):
        author = message.author

        if author.bot:
            return False

        if author == self.user:
            return self.settings.self_bot

        mod_cog = self.get_cog('Mod')
        global_ignores = self.get_cog('Owner').global_ignores

        if self.settings.owner == author.id:
            return True

        if author.id in global_ignores["blacklist"]:
            return False

        if global_ignores["whitelist"]:
            if author.id not in global_ignores["whitelist"]:
                return False

        if not message.channel.is_private:
            server = message.server
            names = (self.settings.get_server_cocap(server), 
                     self.settings.get_server_admin(server), 
                     self.settings.get_server_mod(server), 
                     self.settings.get_server_sel(server))
            results = map(
                lambda name: discord.utils.get(author.roles, name=name),
                names)
            for r in results:
                if r is not None:
                    return True

        if mod_cog is not None:
            if not message.channel.is_private:
                if message.server.id in mod_cog.ignore_list["SERVERS"]:
                    return False

                if message.channel.id in mod_cog.ignore_list["CHANNELS"]:
                    return False

        return True

    async def pip_install(self, name, *, timeout=None):
        """
        Installe un paquet pip dans le dossier local 'lib' dans un thread sécurisé.
        Sur les systèmes Mac, le dossier 'lib' n'est pas utilisé.
        Peut spécifier les secondes maximum à attendre pour que la tâche soit terminée

        Retourne un booléen indiquant si l'installation a réussi
        """

        IS_MAC = sys.platform == "darwin"
        interpreter = sys.executable

        if interpreter is None:
            raise RuntimeError("Impossible de trouver l'interpréteur de Python")

        args = [
            interpreter, "-m",
            "pip", "install",
            "--upgrade",
            "--target", "lib",
            name
        ]

        if IS_MAC: # --target is a problem on Homebrew. See PR #552
            args.remove("--target")
            args.remove("lib")

        def install():
            code = subprocess.call(args)
            sys.path_importer_cache = {}
            return not bool(code)

        response = self.loop.run_in_executor(None, install)
        return await asyncio.wait_for(response, timeout=timeout)

class Formatter(commands.HelpFormatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # OVERRIDE the formatter.HelpFormatter Class function _add_subcommands_to_page
    def _add_subcommands_to_page(self, max_width, commands):
        print("went here 4")
        for name, command in sorted(commands, key=lambda t: t[0]):
            if name in command.aliases:
                # skip aliases
                continue

            entry = '  {0:<{width}} {1}'.format(name, command.short_doc,
                                                width=max_width)
            shortened = self.shorten(entry)
            self._paginator.add_line(shortened)
      
def initialize(bot_class=Bot, formatter_class=Formatter,pm_help=False):
    formatter = formatter_class(show_check_failure=False)

    bot = bot_class(formatter=formatter, description=description, pm_help=None)

    import __main__
    __main__.send_cmd_help = bot.send_cmd_help  # Backwards
    __main__.user_allowed = bot.user_allowed    # compatibility
    __main__.settings = bot.settings            # sucks

    async def get_oauth_url():
        try:
            data = await bot.application_info()
        except Exception as e:
            return "Impossible d'extraire le lien d'invitation.Erreur: {}".format(e)
        return discord.utils.oauth_url(data.id)

    async def set_bot_owner():
        if bot.settings.self_bot:
            bot.settings.owner = bot.user.id
            return "[Selfbot mode]"

        if bot.settings.owner:
            owner = discord.utils.get(bot.get_all_members(),
                                      id=bot.settings.owner)
            if not owner:
                try:
                    owner = await bot.get_user_info(bot.settings.owner)
                except:
                    owner = None
                if not owner:
                    owner = bot.settings.owner  # Just the ID then
            return owner

        how_to = "Faites `[p]set owner` dans le chat pour le définir"

        if bot.user.bot:  # Can fetch owner
            try:
                data = await bot.application_info()
                bot.settings.owner = data.owner.id
                bot.settings.save_settings()
                return data.owner
            except:
                return "Impossible d'extraire le propriétaire. " + how_to
        else:
            return "Encore à définir. " + how_to

    @bot.event
    async def on_ready():
        if bot._intro_displayed:
            return
        bot._intro_displayed = True

        owner_cog = bot.get_cog('Owner')
        total_cogs = len(owner_cog._list_cogs())
        users = len(set(bot.get_all_members()))
        servers = len(bot.servers)
        channels = len([c for c in bot.get_all_channels()])

        login_time = datetime.datetime.utcnow() - bot.uptime
        login_time = login_time.seconds + login_time.microseconds/1E6

        print("Connexion réussie. ({}ms)\n".format(login_time))

        owner = await set_bot_owner()

        print("-------------------------")
        print("MagnificBot - Discord Bot")
        print("-------------------------")
        print(str(bot.user))
        print("\nConnecté à:")
        print("{} serveurs".format(servers))
        print("{} salons".format(channels))
        print("{} utilisateurs\n".format(users))
        prefix_label = 'Prefix'
        if len(bot.settings.prefixes) > 1:
            prefix_label += 'es'

        print("{}: {}".format(prefix_label, " ".join(bot.settings.prefixes)))
        print("Owner: " + str(owner))
        print("{}/{} modules actifs avec {} commandes".format(
            len(bot.cogs), total_cogs, len(bot.commands)))
        print("-----------------")

        if bot.settings.token and not bot.settings.self_bot:
            print("\nUtilisez cette URL pour amener votre bot sur un serveur:")
            url = await get_oauth_url()
            bot.oauth_url = url
            print(url)

        await bot.get_cog('Owner').disable_commands()

    @bot.event
    async def on_resumed():
        bot.counter["session_resumed"] += 1

    @bot.event
    async def on_command(command, ctx):
        bot.counter["processed_commands"] += 1

    @bot.event
    async def on_message(message): 
        bot.counter["messages_read"] += 1
        if bot.user_allowed(message):
            # prefixs = bot.settings.get_prefixes(message.server)
            # mess = message.content.strip()
            # isCommand = False
            # for p in prefixs:
            #     if mess.startswith(p):
            #         isCommand = True
            #         break
            isCommand = await bot.check_is_command(message)
            isPassThruCmd = await bot.check_for_passthru_command(message)
            try:
                delete_after = bot.get_cog('Owner').settings[message.server.id]['delete_delay']
            except KeyError:
                # We have no delay set
                delete_after = -1
            except AttributeError:
                # DM
                delete_after = -1

            if delete_after != -1:
                @asyncio.coroutine
                def delete():
                    yield from asyncio.sleep(delete_after, loop=bot.loop)
                    try:
                        yield from bot.delete_message(message)
                    except discord.errors.NotFound:
                        pass

                try:
                    mod_log = bot.get_cog('Owner').settings[message.server.id]["mod-log"]
                    if mod_log:
                        if message.channel.id == mod_log:
                            if not(isPassThruCmd): raise ForbiddenToPassCommandHere
                except ForbiddenToPassCommandHere:
                    try:
                        await bot.delete_message(message)
                    except discord.errors.Forbidden:
                        print("You do not have the proper permission to delete the message.")
                    except discord.errors.HTTPException:
                        print("Deleting the message failed")
                    finally:
                        if not(isPassThruCmd): 
                            message = await bot.send_message(message.channel, "Les commandes ou messages sont interdits dans ce channel")
                            discord.compat.create_task(delete(), loop=bot.loop)
                        return

                try:
                    botcmd = bot.get_cog('Owner').settings[message.server.id]["botcmd"]
                    botcmdname = bot.get_cog('Owner').settings[message.server.id]["botcmd-name"]
                    if botcmd:
                        if message.channel.id != botcmd:
                            if isCommand: 
                                if not(isPassThruCmd): 
                                    raise OnlyBotCommandChannelAllowed
                        else:
                            if not(isCommand):
                                try:
                                    await bot.delete_message(message)
                                except discord.errors.Forbidden:
                                    print("You do not have the proper permission to delete the message.")
                                except discord.errors.HTTPException:
                                    print("Deleting the message failed")
                                finally:
                                    if not(isPassThruCmd): 
                                        message = await bot.send_message(message.channel, "Les messages sont interdits dans ce channel")
                                        discord.compat.create_task(delete(), loop=bot.loop)
                                    return
                except OnlyBotCommandChannelAllowed:
                    try:
                        await bot.delete_message(message)
                    except discord.errors.Forbidden:
                        print("You do not have the proper permission to delete the message.")
                    except discord.errors.HTTPException:
                        print("Deleting the message failed")
                    finally:
                        message = await bot.send_message(message.channel, "Les commandes ne peuvent être émises que de #{}".format(botcmdname))
                        discord.compat.create_task(delete(), loop=bot.loop)
                        return

                if isCommand: discord.compat.create_task(delete(), loop=bot.loop)

            if isCommand:
                await bot.process_commands(message)

    @bot.event
    async def on_command_error(error, ctx):
        channel = ctx.message.channel
        if isinstance(error, commands.MissingRequiredArgument):
            await bot.send_message(
                channel, "Commande: Un Argument Requis Est Manquant")
            await bot.send_cmd_help(ctx)
        elif isinstance(error, commands.BadArgument):
            bot.send_message(channel, "Commande: Mauvais Argument")
            await bot.send_cmd_help(ctx)
        elif isinstance(error, commands.DisabledCommand):
            await bot.send_message(channel, "Commande: Est désactivée")
        elif isinstance(error, commands.CommandInvokeError):
            # A bit hacky, couldn't find a better way
            no_dms = "Impossible d'envoyer un message à cette utilisateur"
            is_help_cmd = ctx.command.qualified_name == "Help"
            is_forbidden = isinstance(error.original, discord.Forbidden)
            if is_help_cmd and is_forbidden and error.original.text == no_dms:
                msg = ("Je n'ai pas pu vous envoyer le message d'aide en MP. Soit"
                       " vous m'avez bloqué ou vous avez désactivé les MP dans ce serveur.")
                await bot.send_message(channel, msg)
                return

            bot.logger.exception("\n\nRED.py\n\nException in command '{}'".format(
                ctx.command.qualified_name), exc_info=error.original)
            message = ("\n\nRED.py\n\nErreur dans la commande '{}'.\n\nVérifiez votre console ou "
                       "fichier journal pour les détails."
                       "".format(ctx.command.qualified_name))
            log = ("Exception dans la commande '{}'\n"
                   "".format(ctx.command.qualified_name))
            log += "".join(traceback.format_exception(type(error), error,
                                                      error.__traceback__))
            bot._last_exception = log
            await ctx.bot.send_message(channel, inline(message))
        elif isinstance(error, commands.CommandNotFound):
            await bot.send_message(channel, "Commande: Non Trouvée")
            pass
        elif isinstance(error, commands.CheckFailure):
            await bot.send_message(channel, "Erreur: Vérification de vos droits/permissions\n")
            pass
        elif isinstance(error, commands.NoPrivateMessage):
            await bot.send_message(channel, "Commande: Pas Disponible En MP.")
        elif isinstance(error, commands.CommandOnCooldown):
            await bot.send_message(channel, "Commande: Mode Recharge. "
                                            "Réessayez dans {:.2f}s"
                                            "".format(error.retry_after))
        else:
            #bot.logger.exception(type(error).__name__, exc_info=error)
            m = exception(type(error).__name__, exc_info=error)
            bot.logger.exception(type(error).__name__, exc_info=error)
            await bot.send_message(channel, ">>>" + m)

    return bot

def check_folders():
    for folder in folders:
        if not os.path.exists(folder):
            print("Création du dossier " + folder + " ...")
            os.makedirs(folder)

def interactive_setup(settings):
    first_run = settings.bot_settings == settings.default_settings

    if first_run:
        print("MagnificBot - Première exécution\n")
        print("Si ce n'est déjà fait, créez un nouveau compte:\n"
              "https://twentysix26.github.io/Red-Docs/red_guide_bot_accounts/"
              "#creating-a-new-bot-account")
        print("et obtenez le jeton de votre bot comme décrit.")

    if not settings.login_credentials:
        print("\nInsérez le jeton de votre bot:")
        while settings.token is None and settings.email is None:
            choice = input("> ")
            if "@" not in choice and len(choice) >= 50:  # Assuming token
                settings.token = choice
            elif "@" in choice:
                settings.email = choice
                settings.password = input("\nMot de passe> ")
            else:
                print("Cela ne ressemble pas à un jeton valide.")
        settings.save_settings()

    if not settings.prefixes:
        print("\nChoisissez un préfixe Un préfixe est ce que vous tapez avant une commande."
              "\nUn préfixe typique serait le point d'exclamation.\n"
              "Peut être plusieurs caractères. Vous pourrez le changer "
              "plus tard et en ajouter plus.\nChoisissez votre préfixe:")
        confirmation = False
        while confirmation is False:
            new_prefix = ensure_reply("\nPréfixe> ").strip()
            print("\nÊtes-vous sûr de vouloir {0} comme préfixe?\nVous "
                  "serez en mesure d'émettre des commandes comme celle-ci: {0}help"
                  "\nTapez yes pour confirmer ou no pour le changer".format(
                      new_prefix))
            confirmation = get_answer()
        settings.prefixes = [new_prefix]
        settings.save_settings()

    if first_run:
        print("\nEntrez le nom du rôle de Co Capitaine. Toute personne ayant ce rôle dans Discord"
              " sera en mesure d'entrer des commandes de co-capitaine du bot")
        print("Laissez vide pour le nom par défaut (Co-Captain)")
        settings.default_cocap = input("\nCocap role> ")
        if settings.default_cocap == "":
            settings.default_cocap = "Co-Captain"
        settings.save_settings()

        print("\nEntrez le nom du rôle d'administrateur. Toute personne ayant ce rôle dans Discord"
              " sera en mesure d'entrer des commandes d'admin du bot")
        print("Laissez vide pour le nom par défaut (Admins)")
        settings.default_admin = input("\nAdmin role> ")
        if settings.default_admin == "":
            settings.default_admin = "Admins"
        settings.save_settings()

        print("\nEntrez le nom du rôle de modérateur. Toute personne ayant ce rôle dans"
              " Discord sera en mesure d'utiliser les commandes mod du bot")
        print("Laissez vide pour le nom par défaut (Modos)")
        settings.default_mod = input("\nModerator role> ")
        if settings.default_mod == "":
            settings.default_mod = "Modos"
        settings.save_settings()

        print("\nEntrez le nom du rôle Recruteur. Toute personne ayant ce rôle dans"
              " Discord sera en mesure d'utiliser les commandes sel du bot")
        print("Laissez vide pour le nom par défaut (Recruit)")
        settings.default_sel = input("\nRecruiter role> ")
        if settings.default_sel == "":
            settings.default_sel = "Recruit"
        settings.save_settings()

        print("\nLa configuration est terminée. Laissez cette fenêtre toujours ouverte pour "
              " garder MagnificBot en ligne. \nToutes les commandes devront être émises via"
              " le chat de Discord, *cette fenêtre sera maintenant en lecture seule*.\n"
              "Appuyez sur Entrée pour continuer")
        input("\n")

def set_logger(bot):
    logger = logging.getLogger("red") # TODO: Try to change the name of the logger
    logger.setLevel(logging.DEBUG)

    red_format = logging.Formatter(
        '\n\n %(asctime)s %(levelname)s %(module)s %(funcName)s %(lineno)d: '
        '%(message)s',
        datefmt="[%d/%m/%Y %H:%M]")

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(red_format)
    if bot.settings.debug:
        stdout_handler.setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    else:
        stdout_handler.setLevel(logging.INFO)
        logger.setLevel(logging.INFO)

    fhandler = logging.handlers.RotatingFileHandler(
        filename=redlog, encoding='utf-8', mode='a',
        maxBytes=10**7, backupCount=5)
    fhandler.setFormatter(red_format)

    logger.addHandler(fhandler)
    logger.addHandler(stdout_handler)

    dpy_logger = logging.getLogger("discord")
    if bot.settings.debug:
        dpy_logger.setLevel(logging.DEBUG)
    else:
        dpy_logger.setLevel(logging.WARNING)
    handler = logging.FileHandler(
        filename=discordlog, encoding='utf-8', mode='a')
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(module)s %(funcName)s %(lineno)d: '
        '%(message)s',
        datefmt="[%d/%m/%Y %H:%M]"))
    dpy_logger.addHandler(handler)

    return logger

def ensure_reply(msg):
    choice = ""
    while choice == "":
        choice = input(msg)
    return choice

def get_answer():
    choices = ("yes", "y", "no", "n")
    c = ""
    while c not in choices:
        c = input(">").lower()
    if c.startswith("y"):
        return True
    else:
        return False

def load_cogs(bot):

    try:
        registry = dataIO.load_json(cogfile)
    except:
        registry = {}

    bot.load_extension('cogs.owner')
    owner_cog = bot.get_cog('Owner')
    if owner_cog is None:
        print("Le module owner est manquant. Il contient des fonctions de base sans "
              "lesquelles MagnificBot ne peut fonctionner. Réinstaller.")
        exit(1)

    if bot.settings._no_cogs:
        bot.logger.debug("Ignore le chargement initial des modules (--no-cogs)")
        if not os.path.isfile(cogfile):
            dataIO.save_json(cogfile, {})
        return

    failed = []
    extensions = owner_cog._list_cogs()

    if not registry:  # All default cogs enabled by default
        for ext in default_cogs:
            registry["cogs." + ext] = True

    for extension in extensions:
        if extension.lower() == "cogs.owner":
            continue
        to_load = registry.get(extension, False)
        if to_load:
            try:
                owner_cog._load_cog(extension)
            except Exception as e:
                print("{}: {}".format(e.__class__.__name__, str(e)))
                bot.logger.exception(e)
                failed.append(extension)
                registry[extension] = False

    dataIO.save_json(cogfile, registry)

    if failed:
        print("\nÉchec du chargement: {}\n".format(" ".join(failed)))

def main(bot):
    check_folders()
    if not bot.settings.no_prompt:
        interactive_setup(bot.settings)
    load_cogs(bot)

    if bot.settings._dry_run:
        print("Quitte: à sec")
        bot._shutdown_mode = True
        exit(0)

    print("Se connecte à Discord...")
    bot.uptime = datetime.datetime.utcnow()

    if bot.settings.login_credentials:
        yield from bot.login(*bot.settings.login_credentials,
                             bot=not bot.settings.self_bot)
    else:
        print("Aucune information d'identification disponible pour la connexion.")
        raise RuntimeError()
    yield from bot.connect()

if __name__ == '__main__':
    sys.stdout = TextIOWrapper(sys.stdout.detach(),
                               encoding=sys.stdout.encoding,
                               errors="replace",
                               line_buffering=True)
    bot = initialize()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main(bot))
    except discord.LoginFailure:
        bot.logger.error(traceback.format_exc())
        if not bot.settings.no_prompt:
            choice = input("Informations d'identification de connexion non valides. "
                           "Si elles ont fonctionnées avant "
                           "Discord pourrait avoir des problèmes techniques  "
                           "temporaires.\nDans ce cas, appuyez sur Entrée et réessayez"
                           "plus tard.\nAutrement vous pouvez taper 'reset' pour réinitialiser "
                           "les informations d'identification actuelles et les redéfinir "
                           "au prochain démarrage.\n> ")
            if choice.lower().strip() == "reset":
                bot.settings.token = None
                bot.settings.email = None
                bot.settings.password = None
                bot.settings.save_settings()
                print("Les informations d'identification de connexion ont été réinitialisées.")
    except KeyboardInterrupt:
        loop.run_until_complete(bot.logout())
    except Exception as e:
        bot.logger.exception("Exception fatale, tentative de déconnexion gracieuse",
                             exc_info=e)
        loop.run_until_complete(bot.logout())
    finally:
        loop.close()
        if bot._shutdown_mode is True:
            exit(0)
        elif bot._shutdown_mode is False:
            exit(26) # Restart
        else:
            exit(1)