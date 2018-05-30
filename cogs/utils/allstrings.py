from .dataIO import dataIO
from copy import deepcopy
import discord
import os
import argparse

default_strings

Access reade or write to strings


default_path = "data/red/allstrings.json"

class Allstrings:
    def __init__(self, path=default_path, parse_args=True):
        self.path = path
        self.check_folders()
        self.language = "FR"
        self.default_strings = {
            "FR": {},
            "EN": {}
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

        if parse_args:
            parser = argparse.ArgumentParser()
            parser.add_argument("--language", help="language to use: FR EN IT ...")
            args = parser.parse_args()
            if args.language:
                self.language = args.language
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
    
    @property
    def language(self):
        return self.bot_settings["language"]

    @owner.setter
    def language(self, value):
        self.bot_settings["language"] = value