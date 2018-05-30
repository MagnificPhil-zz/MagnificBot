from .dataIO import dataIO
from copy import deepcopy
from datetime import datetime
from collections import defaultdict, OrderedDict
import discord
import os

class StoredMsg:
    def __init__(self, server=None):
        self.retour = []

    def myPrint(self):
        allRetours = self.retour
        self.retour = []
        return allRetours

class Cases:
    """Stocke les différentes actions dans un fichier journal."""
    # class variables shared by all instances
    _default_settings = {
        "default": {
            "BAN": {
                "State": True,
                "Repr": "Ban",
                "Deco": "\N{HAMMER}"},
            "KICK": {
                "State": True,
                "Repr": "Kick",
                "Deco": "\N{WOMANS BOOTS}"},
            "HARDKICK": {
                "State": True,
                "Repr": "Hardkick",
                "Deco": "\N{WOMANS BOOTS} \N{HAMMER}"},
            "UNHARDKICK": {
                "State": True,
                "Repr": "Un-Hardkick",
                "Deco": "\N{DOVE OF PEACE}"},
            "CMUTE": {
                "State": True,
                "Repr": "Channel mute",
                "Deco": "\N{SPEAKER WITH CANCELLATION STROKE}"},
            "SMUTE": {
                "State": True,
                "Repr": "Server mute",
                "Deco": "\N{SPEAKER WITH CANCELLATION STROKE}"},
            "UNCMUTE": {
                "State": True,
                "Repr": "Channel Unmute",
                "Deco": "\N{DOVE OF PEACE}"},
            "UNSMUTE": {
                "State": True,
                "Repr": "Server Unmute",
                "Deco": "\N{DOVE OF PEACE}"},
            "SOFTBAN": {
                "State": True,
                "Repr": "Softban",
                "Deco": "\N{WOMANS BOOTS} \N{DASH SYMBOL}"},
            "PREBAN": {
                "State": True,
                "Repr": "Preemptive ban",
                "Deco": "\N{BUST IN SILHOUETTE} \N{HAMMER}"},
            "UNBAN": {
                "State": True,
                "Repr": "Unban",
                "Deco": "\N{DOVE OF PEACE}"},
            "CLEANED": {
                "State": True,
                "Repr": "Clean",
                "Deco": "\N{WASTEBASKET}"}
        }
    }
    _owner_settings_path = "data/red/ownersettings.json"
    _settings_path = "data/mod/cases_settings.json"
    _log_path = "data/red/red.log"
    _cases_path = "data/red/cases.json"
    _owner_settings = dataIO.load_json(_owner_settings_path)

    # instance variables unique to each instance
    def __init__(self,  bot, server=None):
        self.bot = bot
        self.server = server if server != None else "default"
        self.check_folders()
        self.cases = dataIO.load_json(self._cases_path)
        self.last_case = defaultdict(dict)
        self.sms = StoredMsg()
        self._memory_only = False

        if not dataIO.is_valid_json(self._settings_path):
            self.bot_settings = deepcopy(self._default_settings)
            self.save_settings()
        else:
            current = dataIO.load_json(self._settings_path)
            if current.keys() != self._default_settings.keys():
                for key in self._default_settings.keys():
                    if key not in current.keys():
                        current[key] = self._default_settings[key]
                        print("Ajoute le champ " + str(key) +
                              " à cases_settings.json")
                dataIO.save_json(self._settings_path, current)
            self.bot_settings = dataIO.load_json(self._settings_path)

    @property
    def servers(self):
        ret = {}
        server_ids = list(
            filter(lambda x: str(x).isdigit(), self.bot_settings))
        for server in server_ids:
            ret.update({server: self.bot_settings[server]})
        return ret

    def add_server(self, sid):
        self.bot_settings[sid] = self.bot_settings["default"].copy()
        self.sms.retour.append("Serveur id: {}".format(sid))
        self.save_settings()

    def get_server(self, server: discord.Server = None):
        if server is None:
            return self.bot_settings["default"].copy()
        assert isinstance(server, discord.Server)
        if server.id not in self.bot_settings:
            msg = "Ajout du serveur dans cases_settings: {}".format(server.name)
            self.sms.retour.append(msg)
            self.add_server(server.id)
        if server.id not in self.cases:
            msg = "Ajout du serveur dans cases_logs: {}".format(server.name)
            self.sms.retour.append(msg)
            self.cases[server.id]=dict()
            dataIO.save_json(self._cases_path , self.cases)
            self.cases = dataIO.load_json(self._cases_path)
        return self.bot_settings.get(server.id)

    async def new_case(self, server: discord.Server, *, action, mod=None, user, reason=None, until=None, channel=None, force_create=False):

        actionsSet = self.get_server(server)

        action = action.upper()

        isEnabled = actionsSet[action]
        if not force_create and not isEnabled:
            return False

        mod_channel = server.get_channel(self._owner_settings[server.id]["mod-log"])
        if mod_channel is None:
            return None

        case_n = len(self.cases[server.id]) + 1
            
        case = {
            "case": case_n,
            "created": datetime.utcnow().timestamp(),
            "modified": None,
            "action":  actionsSet[action]['Repr'] + actionsSet[action]['Deco'],
            "channel": channel.id if channel else None,
            "channel_mention": channel.mention if channel else None,
            "user": str(user) if user is not None else None,
            "user_id": user.id if user is not None else None,
            "reason": reason,
            "moderator": str(mod) if mod is not None else None,
            "moderator_id": mod.id if mod is not None else None,
            "amended_by": None,
            "amended_id": None,
            "message": None,
            "until": until.timestamp() if until else None,
        }
        
        case_msg = self.format_case_msg(case)

        try:
            msg = await self.bot.send_message(mod_channel, case_msg)
            case["message"] = msg.id
        except:
            pass

        self.cases[server.id][str(case_n)] = case

        if mod:
            self.last_case[server.id][mod.id] = case_n

        dataIO.save_json(self._cases_path, self.cases)

        return case_n

    async def unStackSMS(self, server: discord.Server):
        pileSms = self.sms.myPrint()
        if pileSms:
            for sMs in pileSms:
                await self.bot.say(sMs, delete_after = self._owner_settings[server.id]["delete_delay"])
        else:
            await self.bot.say("no sms", delete_after = self._owner_settings[server.id]["delete_delay"])
        return

    def resetlogs(self, server: discord.Server = None):
        """Raz des journaux de cases"""
        if server is None:
            self.sms.retour.append("L'id du serveur doit être renseigné.")
            return
        assert isinstance(server, discord.Server)
        self.cases[server.id] = {}
        dataIO.save_json(self._cases_path, self.cases)
        self.sms.retour.append("Les journaux de cases ont été remis à zéro.")

    def actionTable(self, actionsSet, actionsKeys, msg=""):
        a = "ACTION"
        s = "SIGNIFIE"
        v = "VALEUR"
        msg += "```py\n"
        # Calculate the maxi len of Action[Repr] (explicitely written)
        maxlen = max(map(lambda x: len(x['Repr']), actionsSet.values()))
        # Calculate the maxi len of Action (the action code)
        maxlong = max(map(lambda x: len(x[0]), actionsSet.items()))

        msg += '%s -> %s : %s\n' % (a.ljust(maxlong),
                                    s.ljust(maxlen), v)
        for actionKey in actionsKeys:
            value = "activé" if actionsSet[actionKey]['State'] else "désactivé"
            msg += '%s -> %s : %s\n' % ((actionKey.upper()
                                         ).ljust(maxlong), actionsSet[actionKey]['Repr'].ljust(maxlen), value)

        msg += '```'
        return msg

    def set_cases(self, server: discord.Server = None, action: str = None, enabled: bool = None):
        """Active ou desactive la création de case"""

        if server is None:
            print("Le serveur doit être renseigné.")
            return
        else:
            self.server = server
        assert isinstance(server, discord.Server)
        actionsSet = self.get_server(self.server)
        actionsKeys = list(sorted(actionsSet.keys()))

        if action == enabled:  # No args given
            msg = "\nParamètres en cours:\n"
            self.sms.retour.append(self.actionTable(
                actionsSet, actionsKeys, msg))
            return
        elif action.upper() not in actionsKeys:
            msg = "Ce n'est pas une action valide! Les actions sont: \n"
            self.sms.retour.append(self.actionTable(
                actionsSet, actionsKeys, msg))
            return
        elif enabled == None:
            value = "activée" if actionsSet[action.upper(
            )]['State'] else "désactivée"
            self.sms.retour.append(
                "La création de Case pour %s est %s" % (action, value))
            return
        else:
            value = actionsSet[action.upper()]['State']
            if value != enabled:
                self.bot_settings[server.id][action.upper()]['State'] = enabled
                self.save_settings()
            msg = ('La création de Case pour %s %s %s.' %
                   (action.upper(),
                    'était déjà' if enabled == value else 'est maintenant',
                    'activée' if enabled else 'désactivée')
                   )
            self.sms.retour.append(msg)
        return

    def format_case_msg(self, case):

        tmp = case.copy()

        if case["moderator"] is None:
            tmp["moderator"] = "Unknown"
            tmp["moderator_id"] = "Nobody has claimed responsibility yet"

        channel = case.get("channel")
        if channel:
            tmp["action"] += ' in ' + case.get("channel_mention")

        case_msg = (
            "**Case #{case}** | {action}\n"
            "**User:** {user} ({user_id})\n"
            "**Moderator:** {moderator} ({moderator_id})\n"
        ).format(**tmp)

        created = case.get('created')
        until = case.get('until')
        if created and until:
            start = datetime.fromtimestamp(created)
            end = datetime.fromtimestamp(until)
            end_fmt = end.strftime('%Y-%m-%d %H:%M:%S UTC')
            duration = end - start
            dur_fmt = self.strfdelta(duration)
            case_msg += ("**Until:** {}\n"
                         "**Duration:** {}\n").format(end_fmt, dur_fmt)

        amended = case.get('amended_by')
        if amended:
            amended_id = case.get('amended_id')
            case_msg += "**Amended by:** %s (%s)\n" % (amended, amended_id)

        modified = case.get('modified')
        if modified:
            modified = datetime.fromtimestamp(modified)
            modified_fmt = modified.strftime('%Y-%m-%d %H:%M:%S UTC')
            case_msg += "**Last modified:** %s\n" % modified_fmt

        case_msg += "**Reason:** %s\n" % tmp["reason"]

        return case_msg

    def strfdelta(self, delta):
        s = []
        if delta.days:
            ds = '%i day' % delta.days
            if delta.days > 1:
                ds += 's'
            s.append(ds)
        hrs, rem = divmod(delta.seconds, 60*60)
        if hrs:
            hs = '%i hr' % hrs
            if hrs > 1:
                hs += 's'
            s.append(hs)
        mins, secs = divmod(rem, 60)
        if mins:
            s.append('%i min' % mins)
        if secs:
            s.append('%i sec' % secs)
        return ' '.join(s)

    def check_folders(self):
        folders = ("data", os.path.dirname(self._settings_path), "data/red")
        for folder in folders:
            if not os.path.exists(folder):
                print("Création du dossier " + folder + " ...")
                os.makedirs(folder)

    def check_files(self):
        if not os.path.isfile(self._settings_path):
            print("Creating empty cases_settings.json...")
            dataIO.save_json(self._settings_path, [])

        if not os.path.isfile(self._cases_path):
            print("Creating empty cases.json...")
            dataIO.save_json(self._cases_path, [])

    def save_settings(self):
        if not self._memory_only:
            print("Sauvegarde cases_settings.json...")
            dataIO.save_json(self._settings_path, self.bot_settings)
