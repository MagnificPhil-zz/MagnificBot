import discord
import os
import asyncio
import time
import logging

from discord.ext import commands
from __main__ import settings
from cogs.utils.dataIO import dataIO

reminders_path = "data/remindme/reminders.json"
mod_log_path = 'data/mod/mod.log'
class RemindMe:
    """Pour ne plus rien oublier."""
    # _ignore_list_path = "data/mod/ignorelist.json"
    # _filter_path = "data/mod/filter.json"
    _ownersettings_path = "data/red/ownersettings.json"
    # _perms_cache_path = "data/mod/perms_cache.json"
    # _past_names_path = "data/mod/past_names.json"
    # _past_nicknames_path = "data/mod/past_nicknames.json"
    _reminders_path = reminders_path

    def __init__(self, bot):
        self.bot = bot
        self.reminders = dataIO.load_json(self._reminders_path)
        self.settings = dataIO.load_json(self._ownersettings_path)
        self.units = {"second": 1,
                      "seconde": 1,
                      "sec": 1,
                      "minute": 60,
                      "min": 60,
                      "heure": 3600,
                      "hour": 3600,
                      "h": 3600,
                      "jour": 86400,
                      "day": 86400,
                      "j": 86400, 
                      "semaine": 604800,
                      "sem": 604800,
                      "week": 604800,
                      "moi": 2592000,
                      "month": 2592000}

    @commands.command(pass_context=True)
    async def rappelermoi(self, ctx,  quantity: int, time_unit: str, *text: str):
        """Vous envoie <text> quand c'est l'heure

        Accepte: minutes, min, heures, hours, h, jours, days, j, semaines, sem, weeks, mois, months
        """
        
        text = " ".join(text)
        time_unit = time_unit.lower()
        author = ctx.message.author
        server = ctx.message.server
        s = ""
        if time_unit.endswith("s"):
            time_unit = time_unit[:-1]
            s = "s"
        if not time_unit in self.units:
            await self.bot.say("Unité de temps invalide. Choisir dans:\n"
                               "minutes, min, heures, hours, h,\n"
                               "jours, days, j, semaines, sem, weeks,\n"
                               "mois, months", delete_after=self.settings[server.id]["delete_delay"])
            return
        if quantity < 1:
            await self.bot.say("Quantity ne peut pas être 0 ou négatif.", delete_after=self.settings[server.id]["delete_delay"])
            return
        if len(text) > 1960:
            await self.bot.say("Le texte est trop long (1960 caractères max).", delete_after=self.settings[server.id]["delete_delay"])
            return
        seconds = self.units[time_unit] * quantity
        future = int(time.time()+seconds)
        self.reminders.append(
            {"SERVER":server.id, "ID": author.id, "NAME": author.name, "MENTION": author.mention, "DISCRIMINATOR": author.discriminator, "FUTURE": future, "TEXT": text})
        logger.info("{}({}) set a reminder.".format(author.name, author.id))
        await self.bot.say("Je vous rappelle ça dans {} {}.".format(str(quantity), time_unit + s), delete_after=self.settings[server.id]["delete_delay"])
        dataIO.save_json(self._reminders_path, self.reminders)

    @commands.command(pass_context=True)
    async def oubliermoi(self, ctx):
        """Supprime toutes vos notifications à venir"""
        author = ctx.message.author
        server = ctx.message.server
        to_remove = []
        for reminder in self.reminders:
            if reminder["ID"] == author.id:
                to_remove.append(reminder)
        if not to_remove == []:
            for reminder in to_remove:
                self.reminders.remove(reminder)
            dataIO.save_json(self._reminders_path, self.reminders)
            await self.bot.say("Toutes vos notifications ont été enlevées.", delete_after=self.settings[server.id]["delete_delay"])
        else:
            await self.bot.say("Vous n'avez pas de notifications à venir.", delete_after=self.settings[server.id]["delete_delay"])
    
    async def check_reminders(self, bot):
        while "RemindMe" in self.bot.cogs:
            self.reminders = dataIO.load_json(self._reminders_path)
            to_remove = []
            #print("\ncheck : " + str(len(self.reminders)))
            for reminder in self.reminders:
                if reminder["FUTURE"] <= int(time.time()):
                    try:
                        logger.info("{}({}) has a reminder done.".format(
                            reminder["NAME"], reminder["ID"]))
                        for un in bot.servers:
                            assert isinstance(un, discord.Server)
                            if un.id == reminder["SERVER"]:
                                server = un
                                break
                        else:
                            server = None
                        if server:
                            for member in server.members:
                                if member.id == reminder["ID"]:
                                    author = member
                                    break
                        else:
                            author = "@"+reminder["NAME"]+"#"+reminder["DISCRIMINATOR"]
                            #print("Mon destinataire=", author)
                        try:
                            #print("Le destinataire:", author)
                            await self.bot.send_message(author, "RAPPEL:\n\n{}".format(reminder["TEXT"]))
                            to_remove.append(reminder)
                        except:
                            pass
                    except (discord.errors.Forbidden, discord.errors.NotFound):
                        pass
                    #     to_remove.append(reminder)
                    except discord.errors.HTTPException:
                        pass
                    # else:
                    #     to_remove.append(reminder)
            for reminder in to_remove:
                self.reminders.remove(reminder)
            if to_remove:
                dataIO.save_json(self._reminders_path, self.reminders)
            await asyncio.sleep(5)

def check_folders():
    if not os.path.exists("data/remindme"):
        print("Créaton du dossier data/remindme ...")
        os.makedirs("data/remindme")

def check_files():
    f = reminders_path
    if not os.path.isfile(f):
        print("Création du fichier vide reminders.json...")
        dataIO.save_json(f, [])

def setup(bot):
    global logger
    check_folders()
    check_files()
    logger = logging.getLogger("remindme")
    if logger.level == 0:  # Prevents the logger from being loaded again in case of module reload
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(
            filename=mod_log_path, encoding='utf-8', mode='a')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(message)s', datefmt="[%d/%m/%Y %H:%M]"))
        logger.addHandler(handler)
    n = RemindMe(bot)
    loop = asyncio.get_event_loop()
    loop.create_task(n.check_reminders(bot))
    bot.add_cog(n)
