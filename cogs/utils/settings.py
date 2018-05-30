from .dataIO import dataIO
from copy import deepcopy
import discord
import os
import argparse


default_path = "data/red/settings.json"


class Settings:

    def __init__(self, path=default_path, parse_args=True):
        self.path = path
        self.check_folders()
        self.default_settings = {
            "TOKEN": None,
            "EMAIL": None,
            "PASSWORD": None,
            "OWNER": None,
            "PREFIXES": [],
            "default": {"ADMIN_ROLE": "Admins",
                        "COCAP_ROLE": "Co-Captain",
                        "MOD_ROLE": "Modos",
                        "SEL_ROLE": "Recruit",
                        "PREFIXES": []}
                        }
        self._memory_only = False

        if not dataIO.is_valid_json(self.path):
            self.bot_settings = deepcopy(self.default_settings)
            self.save_settings()
        else:
            current = dataIO.load_json(self.path)
            if current.keys() != self.default_settings.keys():
                for key in self.default_settings.keys():
                    if key not in current.keys():
                        current[key] = self.default_settings[key]
                        print("Ajout le champ " + str(key) +
                              " à red settings.json")
                dataIO.save_json(self.path, current)
            self.bot_settings = dataIO.load_json(self.path)

        if "default" not in self.bot_settings:
            self.update_old_settings_v1()

        if "LOGIN_TYPE" in self.bot_settings:
            self.update_old_settings_v2()
        if parse_args:
            self.parse_cmd_arguments()

    def parse_cmd_arguments(self):
        parser = argparse.ArgumentParser(description="MagnificBot - Discord Bot")
        parser.add_argument("--owner", help="ID du propriétaire. Seul celui qui héberge "
                                            "le bot devrait être propriétaire, cela a "
                                            "des implications de sécurité")
        parser.add_argument("--co-owner", action="append", default=[],
                            help="ID d'un copropriétaire, seuls les gens qui ont"
                                 "accès au système qui héberge le bot"
                                 "devraient être copropriétaires, comme cela leur donne"
                                 "un accès complet aux données du système."
                                 "Cela a de graves implications de sécurité si"
                                 "mal utilisé. Peut être multiple.")
        parser.add_argument("--prefix", "-p", action="append",
                            help="Préfixe Global. Peut être multiple")
        parser.add_argument("--admin-role", help="Role vu comme admin par le "
                                                 "bot.")
        parser.add_argument("--mod-role", help="Role vu comme mod par le bot.")
        parser.add_argument("--sel-role", help="vu comme sel par le bot."
                                                "Utilisé pour le recrutement.")
        parser.add_argument("--no-prompt",
                            action="store_true",
                            help="Désactive les entrées de la console. Les caractéristiques "
                                 "nécessitant une intéraction par la console pourrait être désactivée")
        parser.add_argument("--no-cogs",
                            action="store_true",
                            help="Démarre le bot sans modules, seulement le noyau")
        parser.add_argument("--self-bot",
                            action='store_true',
                            help="Indique si le bot doit se connecter en tant que selfbot")
        parser.add_argument("--memory-only",
                            action="store_true",
                            help="Les arguments passés et les modifications futures"
								 " des paramètres ne seront pas sauvegardées sur le"
								 " disque.")
        parser.add_argument("--dry-run",
                            action="store_true",
                            help="Fait s'arrêter le bot avec le code 0 jsute avant le "
                                 "login. C'est utile pour tester les processus de  "
                                 "démarrage.")
        parser.add_argument("--debug",
                            action="store_true",
                            help="Active le mode debug ")

        args = parser.parse_args()

        if args.owner:
            self.owner = args.owner
        if args.prefix:
            self.prefixes = sorted(args.prefix, reverse=True)
        if args.admin_role:
            self.default_admin = args.admin_role
        if args.mod_role:
            self.default_mod = args.mod_role
        if args.sel_role:
            self.default_sel = args.sel_role

        self.no_prompt = args.no_prompt
        self.self_bot = args.self_bot
        self._memory_only = args.memory_only
        self._no_cogs = args.no_cogs
        self.debug = args.debug
        self._dry_run = args.dry_run
        self.co_owners = args.co_owner

        self.save_settings()

    def check_folders(self):
        folders = ("data", os.path.dirname(self.path), "cogs", "cogs/utils")
        for folder in folders:
            if not os.path.exists(folder):
                print("Création du dossier " + folder + " ...")
                os.makedirs(folder)

    def save_settings(self):
        if not self._memory_only:
            dataIO.save_json(self.path, self.bot_settings)

    def update_old_settings_v1(self):
        # This converts the old settings format
        sel = self.bot_settings["SEL_ROLE"]
        mod = self.bot_settings["MOD_ROLE"]
        admin = self.bot_settings["ADMIN_ROLE"]
        cocap = self.bot_settings["COCAP_ROLE"]
        del self.bot_settings["SEL_ROLE"]
        del self.bot_settings["MOD_ROLE"]
        del self.bot_settings["ADMIN_ROLE"]
        del self.bot_settings["COCAP_ROLE"]
        self.bot_settings["default"] = {"SEL_ROLE": sel,
                                        "MOD_ROLE": mod,
                                        "ADMIN_ROLE": admin,
                                        "COCAP_ROLE": cocap,
                                        "PREFIXES": []
                                        }
        self.save_settings()

    def update_old_settings_v2(self):
        # The joys of backwards compatibility
        settings = self.bot_settings
        if settings["EMAIL"] == "EmailHere":
            settings["EMAIL"] = None
        if settings["PASSWORD"] == "":
            settings["PASSWORD"] = None
        if settings["LOGIN_TYPE"] == "token":
            settings["TOKEN"] = settings["EMAIL"]
            settings["EMAIL"] = None
            settings["PASSWORD"] = None
        else:
            settings["TOKEN"] = None
        del settings["LOGIN_TYPE"]
        self.save_settings()

    @property
    def owner(self):
        return self.bot_settings["OWNER"]

    @owner.setter
    def owner(self, value):
        self.bot_settings["OWNER"] = value

    @property
    def token(self):
        return os.environ.get("RED_TOKEN", self.bot_settings["TOKEN"])

    @token.setter
    def token(self, value):
        self.bot_settings["TOKEN"] = value
        self.bot_settings["EMAIL"] = None
        self.bot_settings["PASSWORD"] = None

    @property
    def email(self):
        return os.environ.get("RED_EMAIL", self.bot_settings["EMAIL"])

    @email.setter
    def email(self, value):
        self.bot_settings["EMAIL"] = value
        self.bot_settings["TOKEN"] = None

    @property
    def password(self):
        return os.environ.get("RED_PASSWORD", self.bot_settings["PASSWORD"])

    @password.setter
    def password(self, value):
        self.bot_settings["PASSWORD"] = value

    @property
    def login_credentials(self):
        if self.token:
            return (self.token,)
        elif self.email and self.password:
            return (self.email, self.password)
        else:
            return tuple()

    @property
    def prefixes(self):
        return self.bot_settings["PREFIXES"]

    @prefixes.setter
    def prefixes(self, value):
        assert isinstance(value, list)
        self.bot_settings["PREFIXES"] = value

    @property
    def default_admin(self):
        if "default" not in self.bot_settings:
            self.update_old_settings()
        return self.bot_settings["default"].get("ADMIN_ROLE", "")

    @default_admin.setter
    def default_admin(self, value):
        if "default" not in self.bot_settings:
            self.update_old_settings()
        self.bot_settings["default"]["ADMIN_ROLE"] = value

    @property
    def default_mod(self):
        if "default" not in self.bot_settings:
            self.update_old_settings_v1()
        return self.bot_settings["default"].get("MOD_ROLE", "")

    @default_mod.setter
    def default_mod(self, value):
        if "default" not in self.bot_settings:
            self.update_old_settings_v1()
        self.bot_settings["default"]["MOD_ROLE"] = value
    
    @property
    def default_sel(self):
        if "default" not in self.bot_settings:
            self.update_old_settings_v1()
        return self.bot_settings["default"].get("SEL_ROLE", "")

    @default_sel.setter
    def default_sel(self, value):
        if "default" not in self.bot_settings:
            self.update_old_settings_v1()
        self.bot_settings["default"]["SEL_ROLE"] = value

    @property
    def default_cocap(self):
        if "default" not in self.bot_settings:
            self.update_old_settings_v1()
        return self.bot_settings["default"].get("COCAP_ROLE", "")

    @default_cocap.setter
    def default_cocap(self, value):
        if "default" not in self.bot_settings:
            self.update_old_settings_v1()
        self.bot_settings["default"]["COCAP_ROLE"] = value

    @property
    def servers(self):
        ret = {}
        server_ids = list(
            filter(lambda x: str(x).isdigit(), self.bot_settings))
        for server in server_ids:
            ret.update({server: self.bot_settings[server]})
        return ret

    def get_server(self, server):
        if server is None:
            return self.bot_settings["default"].copy()
        assert isinstance(server, discord.Server)
        return self.bot_settings.get(server.id,
                                     self.bot_settings["default"]).copy()

    def get_server_cocap(self, server):
        if server is None:
            return self.default_cocap
        assert isinstance(server, discord.Server)
        if server.id not in self.bot_settings:
            return self.default_cocap
        return self.bot_settings[server.id].get("COCAP_ROLE", "")

    def set_server_cocap(self, server, value):
        if server is None:
            return
        assert isinstance(server, discord.Server)
        if server.id not in self.bot_settings:
            self.add_server(server.id)
        self.bot_settings[server.id]["COCAP_ROLE"] = value
        self.save_settings()

    def get_server_admin(self, server):
        if server is None:
            return self.default_admin
        assert isinstance(server, discord.Server)
        if server.id not in self.bot_settings:
            return self.default_admin
        return self.bot_settings[server.id].get("ADMIN_ROLE", "")

    def set_server_admin(self, server, value):
        if server is None:
            return
        assert isinstance(server, discord.Server)
        if server.id not in self.bot_settings:
            self.add_server(server.id)
        self.bot_settings[server.id]["ADMIN_ROLE"] = value
        self.save_settings()

    def get_server_mod(self, server):
        if server is None:
            return self.default_mod
        assert isinstance(server, discord.Server)
        if server.id not in self.bot_settings:
            return self.default_mod
        return self.bot_settings[server.id].get("MOD_ROLE", "")

    def set_server_mod(self, server, value):
        if server is None:
            return
        assert isinstance(server, discord.Server)
        if server.id not in self.bot_settings:
            self.add_server(server.id)
        self.bot_settings[server.id]["MOD_ROLE"] = value
        self.save_settings()

    def get_server_sel(self, server):
        if server is None:
            return self.default_sel
        assert isinstance(server, discord.Server)
        if server.id not in self.bot_settings:
            return self.default_sel
        return self.bot_settings[server.id].get("SEL_ROLE", "")

    def set_server_sel(self, server, value):
        if server is None:
            return
        assert isinstance(server, discord.Server)
        if server.id not in self.bot_settings:
            self.add_server(server.id)
        self.bot_settings[server.id]["SEL_ROLE"] = value
        self.save_settings()

    def get_server_prefixes(self, server):
        if server is None or server.id not in self.bot_settings:
            return self.prefixes
        return self.bot_settings[server.id].get("PREFIXES", [])

    def set_server_prefixes(self, server, prefixes):
        if server is None:
            return
        assert isinstance(server, discord.Server)
        if server.id not in self.bot_settings:
            self.add_server(server.id)
        self.bot_settings[server.id]["PREFIXES"] = prefixes
        self.save_settings()

    def get_prefixes(self, server):
        """Renvoie les préfixes du serveur si définis, sinon ceux globaux"""
        p = self.get_server_prefixes(server)
        return p if p else self.prefixes

    def add_server(self, sid):
        self.bot_settings[sid] = self.bot_settings["default"].copy()
        self.save_settings()
