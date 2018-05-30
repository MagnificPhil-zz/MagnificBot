import discord
from discord.ext import commands
from discord.utils import find
from __main__ import send_cmd_help
import platform, asyncio, string, operator, random, textwrap
import os, re, aiohttp
from cogs.utils.dataIO import dataIO, fileIO
from cogs.utils import checks
# from cogs.economy import Banque, Bank
import threading
import locale

try:
    import scipy
    import scipy.misc
    import scipy.cluster
except:
    raise RuntimeError("Scipy n'est pas installé. Lancez la commande 'pip3 install numpy' puis 'pip3 install scipy' et essayez à nouveau")

try:
    from PIL import Image, ImageDraw, ImageFont, ImageColor, ImageOps
except:
    raise RuntimeError("Pillow n'est pas installé. Lancez la commande 'pip3 install pillow' et essayez à nouveau")
import time

PATH_LIST = ['data', 'xp']
BASEPATH = os.path.join(*PATH_LIST)
FONTPATH = os.path.join(BASEPATH, 'font')
GENPATH = os.path.join(BASEPATH, 'gen')

DEFAULT_SETTINGS = os.path.join(*PATH_LIST, "settings.json")
SERVERS = os.path.join(*PATH_LIST, "servers.json")
BADGES = os.path.join(*PATH_LIST, "badges.json")
BLOCK = os.path.join(*PATH_LIST, "block.json")
USERS = os.path.join(*PATH_LIST, "users.json")

# fonts
font_file = os.path.join(FONTPATH, 'font.ttf')
font_bold_file = os.path.join(FONTPATH, 'font_bold.ttf')
font_unicode_file = os.path.join(FONTPATH, 'unicode.ttf')

# None anymore! lol :c
bg_credits = {
}

prefix = fileIO("data/red/settings.json", "load")['PREFIXES']
default_avatar_url = "http://puu.sh/qB89K/c37cd0de38.jpg"

##############################################################################
# 
# SETUP (public)
#
##############################################################################

def chemin (path_to:str = None, file_to:str = None):
    
    if path_to is None:
        path_to = os.path.join(*PATH_LIST)
    if file_to is not None:
        path_to = os.path.join(path_to, file_to)
    else:
        path_to = os.path.join(path_to, "settings.json")
    return path_to

def check_folders(foldr:str):
    msg = "Checking "+foldr+" folder..."
    if not os.path.exists(foldr):
        msg += "\n"+"Creating "+foldr+" folder..."
        os.makedirs(foldr)
        msg += " done"+""
    else:
        msg += " OK"+""
    print(msg)

def check_files():

    if not fileIO(SERVERS, "check"):
        print("Creating servers.json...")
        fileIO(SERVERS, "save", {})
    else:
        print("json SERVERS file CHECKED")

    if not fileIO(USERS, "check"):
        print("Creating users.json...")
        fileIO(USERS, "save", {})
    else:
        print("json USERS file CHECKED")

    if not fileIO(BLOCK, "check"):
        print("Creating block.json...")
        fileIO(BLOCK, "save", {})
    else:
        print("json BLOCK file CHECKED")

    # Ce sont les valeurs par défauts 
    # Doivent être appliquées à chaque nouveau serveur
    default = {
        "general": {
            "badge_type" : "circles",
            "bg_price" : 0,
            "cooldown" : 10,
            "disabled_server" : False,
            "freq_xp" : 60,
            "int_rank" : 100,
            "lvl_msg" : True,
            "lvl_msg_lock" : "tous",
            "max_xp" : 25,
            "mention" : True,
            "min_xp" : 15,
            "private_lvl_msg" : False,
            "text_only" : False,
            "processed" : False,
            "locale": "fr"
        },
        "bgs": {
            "profile": {
                "alice": "http://puu.sh/qAoLx/7335f697fb.png",
                "bluestairs": "http://puu.sh/qAqpi/5e64aa6804.png",
                "lamp": "http://puu.sh/qJJIb/05e4e02edd.jpg",
                "coastline": "http://puu.sh/qJJVl/f4bf98d408.jpg",
                "redblack": "http://puu.sh/qI0lQ/3a5e04ff05.jpg",
                "default": "http://puu.sh/qNrD6/ee0ef9462d.jpg",
                "iceberg": "http://puu.sh/qAr6p/1d4e031a9e.png",
                "miraiglasses": "http://puu.sh/qArax/ce8a8bf12e.png",
                "miraikuriyama": "http://puu.sh/qArbY/59b883fe71.png",
                "mountaindawn": "http://puu.sh/qJJLa/568b9a318b.jpg",
                "waterlilies": "http://puu.sh/qJJSL/43b0f852c0.jpg"
            },
            "rank": {
                "aurora" : "http://puu.sh/qJJv4/82aeb6de54.jpg",
                "default" : "http://puu.sh/qJJgx/abeda18e15.jpg",
                "nebula": "http://puu.sh/qJJqh/4a530e48ef.jpg",
                "mountain" : "http://puu.sh/qJvR4/52a5797b4f.jpg"
            },
            "levelup": {
                "default" : "http://puu.sh/qJJjz/27f499f989.jpg",
            },
        },
    }

    if not os.path.isfile(DEFAULT_SETTINGS):
        print("Creating default settings.json...")
        fileIO(DEFAULT_SETTINGS, "save", default)
    else:
        print("json SETTINGS file CHECKED")


    if not fileIO(BADGES, "check"):
        print("Creating badges.json...")
        fileIO(BADGES, "save", {})
    else:
        print("json BADGES file CHECKED")

def setup(bot):
    print("\n *************** \n STARTING XP COG \n *************** \n")
    check_folders(BASEPATH)
    check_folders(FONTPATH)
    check_folders(GENPATH)
    check_files()
    print("\n *************** \n XP COG INITIATED \n *************** \n")
    n = XP(bot)
    bot.add_listener(n.on_message,"on_message")
    bot.add_cog(n)

class XP:
    """Permet de gagner de l'XP, 
       de gérer des Niveaux.

       Profils avec des images."""

##############################################################################
# 
# COMMANDES DISPONIBLE POUR LES UTILISATEURS (PUBLIC)
#
##############################################################################

    @commands.command(pass_context=True, no_pm=True)
    async def rang(self,ctx,user : discord.Member=None):
        """Affiche le rang d'un joueur."""
        if user == None:
            user = ctx.message.author
        channel = ctx.message.channel
        server = user.server
        curr_time = time.time()

        if self.settings["disabled_server"]:
            await self.bot.say("**Les commandes d'XP pour ce serveur sont désactivées!**")
            return

        # Création de l'utilisateur s'il n'existe pas
        await self._create_user(user, server)

        if self.settings["text_only"]:
            await self.bot.say(await self.rank_text(user, server))
            self.block[user.id]["rang"] = curr_time
        else:
            if "rang" not in self.block[user.id]:
                self.block[user.id]["rang"] = 0

            elapsed_time = curr_time - self.block[user.id]["rang"]
            if elapsed_time > int(self.settings["cooldown"]):
                t = threading.Thread(target = await self.draw_rank(user, server))
                self.threads.append(t)
                t.start()
                await self.bot.send_typing(channel)            
                await self.bot.send_file(channel, GENPATH+'/rank{}.png'.format(user.id), content='**Statistiques & Classement pour {}**'.format(self._is_mention(user)))
                self._clear_folder()
                self.block[user.id]["rang"] = curr_time
                fileIO(BLOCK, "save", self.block)
            else:
                await self.bot.say("**{}, attendez {}s de temporisation!**".format(self._is_mention(user), int(int(self.settings["cooldown"]) - elapsed_time))) 

    @commands.command(pass_context=True, no_pm=True)
    async def badges_lst(self, ctx):
        '''Donne la liste des badges.'''
        msg = "```xl\n"
        for badge in self.badges.keys():
            msg += "+ {}\n".format(badge)
        msg += "```"
        await self.bot.say(msg) 

    @commands.command(pass_context=True, no_pm=True)
    async def top10(self,ctx, global_rank:str = None):
        '''Affiche le classement. Utiliser "global" pour le général'''
        server = ctx.message.server

        if self.settings["disabled_server"]:
            await self.bot.say("**Les commandes d'XP pour ce serveur sont désactivées!**")
            return

        users = []
        if global_rank == "global":
            msg = "**Classement Global pour {}**\n".format(self.bot.user.name)
            for userid in self.users.keys():
                for server in self.bot.servers:
                    temp_user = find(lambda m: m.id == userid, server.members)
                    if temp_user != None:
                        break
                if temp_user != None:
                    users.append((temp_user.name, self.users[userid]["global_xp"]))
            sorted_list = sorted(users, key=lambda us: us[1], reverse=True)
        else:
            msg = "**Classement pour {}**\n".format(server.name)
            for userid in self.users.keys():
                if server.id in self.users[userid]["servers"]:
                    temp_user = find(lambda m: m.id == userid, server.members)
                    server_exp = self.users[userid]["servers"][server.id]["total_xp"]
                    if temp_user != None:
                        users.append((temp_user.name, server_exp))
            sorted_list = sorted(users, key=lambda us: us[1], reverse=True)

        msg += "```ruby\n"
        rank = 1
        labels = ["♔", "♕", "♖", "♗", "♘", "♙", " ", " ", " ", " "]
        for user in sorted_list[:10]:
            msg += u'{:<2}{:<2}{:<2}   # {:<5}\n'.format(rank, labels[rank-1], u"➤", user[0])
            msg += u'{:<2}{:<2}{:<2}    {:<5}\n'.format(" ", " ", " ", "Total de Points: " + str(user[1]))
            rank += 1
        msg +="```"
        await self.bot.say(msg)       

    @commands.command(pass_context=True, no_pm=True)
    async def reput(self, ctx, user : discord.Member):
        """Donne des points de réputation à un joueur."""
        org_user = ctx.message.author
        channel = ctx.message.channel
        server = user.server
        curr_time = time.time()
        
        if self.settings["disabled_server"]:
            await self.bot.say("**Les commandes d'XP pour ce serveur sont désactivées!**")
            return
        if user.id == org_user.id and org_user.id != self.owner:
            await self.bot.say("**Vous ne pouvez donner des points de réputation à vous-même!**")
            return
        if user.bot:
            await self.bot.say("**Vous ne pouvez donner des points de réputation à un bot!**")
            return

        # Création de l'utilisateur s'il n'existe pas
        await self._create_user(user, server)

        if org_user.id not in self.block:
            self.block[org_user.id] = {
                "chat" : 0,
                "nom" : org_user.name,
                "rang" : 0,
                "rep" : 0.0
            }
            fileIO(BLOCK, "save", self.block) 

        delta = float(curr_time) - float(self.block[org_user.id]["rep"])
        if delta >= 86400.0 and delta>0:
            self.block[org_user.id]["rep"] = curr_time
            self.users[user.id]["rep"] += 1
            fileIO(BLOCK, "save", self.block)
            fileIO(USERS, "save", self.users)
            await self.bot.say("**Vous venez de donner 1 point de réputation à {} !**".format(user.mention))
        else:
            # calulate time left
            seconds = 86400 - delta
            m, s = divmod(seconds, 60)
            h, m = divmod(m, 60)
            await self.bot.say("**Vous devez attendre {} heures, {} minutes, et {} secondes avant de redonner de la réputation!**".format(int(h), int(m), int(s)))

    @commands.command(pass_context=True, no_pm=True)
    async def profil(self,ctx, *, user : discord.Member=None):
        """Affiche le profil d'un joueur."""
        if user == None:
            user = ctx.message.author
        channel = ctx.message.channel
        server = user.server
        curr_time = time.time()

        if self.settings["disabled_server"]:
            await self.bot.say("**Les commandes d'XP pour ce serveur sont désactivées!**")
            return

        # Création de l'utilisateur s'il n'existe pas
        await self._create_user(user, server)

        if self.settings["text_only"]:
            await self.bot.say(await self.profile_text(user, server))
        else :
            if "profile" not in self.block[user.id]:
                self.block[user.id]["profile"] = 0

            elapsed_time = curr_time - self.block[user.id]["profile"]
            if elapsed_time > int(self.settings["cooldown"]):
                t = threading.Thread(target = await self.draw_profile(user, server))
                self.threads.append(t)
                t.start()
                await self.bot.send_typing(channel)         
                await self.bot.send_file(channel, GENPATH+'/profile{}.png'.format(user.id), content='**Profil utilisateur de {}**'.format(self._is_mention(user)))
                self._clear_folder()
                self.block[user.id]["profile"] = curr_time
                fileIO(BLOCK, "save", self.block)
            else:
                await self.bot.say("**{}, attendez {}s de temporisation!**".format(self._is_mention(user), int(int(self.settings["cooldown"]) - elapsed_time)))       
    
    @commands.command(pass_context=True, no_pm=True)
    async def profil_det(self, ctx, user : discord.Member = None):
        """Donne des détails plus spécifiques sur un profil."""

        if not user:
            user = ctx.message.author
        server = ctx.message.server
        userinfo = self.users[user.id]
        
        if self.settings["disabled_server"]:
            await self.bot.say("**Les commandes d'XP pour ce serveur sont désactivées!**")
            return

        # Création de l'utilisateur s'il n'existe pas
        await self._create_user(user, server)

        msg = "```xl\n"
        msg += "Nom: {}\n".format(user.name)
        msg += "Titre: {}\n".format(userinfo["titre"])
        msg += "Réput.: {}\n".format(userinfo["rep"])
        msg += "Niveau Serveur: {}\n".format(userinfo["servers"][server.id]["level"])
        msg += "Exp en cours: {}\n".format(userinfo["current_xp"])
        msg += "XP Serveur Totale: {}\n".format(userinfo["servers"][server.id]["total_xp"])
        msg += "XP Globale: {}\n".format(userinfo["global_xp"])
        msg += "Info: {}\n".format(userinfo["info"])
        msg += "Arrière plan Profil: {}\n".format(userinfo["profile_background"])
        msg += "Arrière plan Rang: {}\n".format(userinfo["rank_background"])
        msg += "Arrière plan Niveau sup.: {}\n".format(userinfo["levelup_background"])
        if "rep_color" in userinfo.keys() and userinfo["rep_color"]:
            msg += "Couleur section réputation: {}\n".format(self._rgb_to_hex(userinfo["rep_color"]))
        if "badge_col_color" in userinfo.keys() and userinfo["badge_col_color"]:
            msg += "Couleur section badge: {}\n".format(self._rgb_to_hex(userinfo["badge_col_color"]))
        if "profile_exp_color" in userinfo.keys() and userinfo["profile_exp_color"]:
            msg += "Couleur profile exp: {}\n".format(self._rgb_to_hex(userinfo["profile_exp_color"]))
        if "rank_exp_color" in userinfo.keys() and userinfo["rank_exp_color"]:
            msg += "Couleur Rang exp: {}\n".format(self._rgb_to_hex(userinfo["rank_exp_color"]))
        msg += "Badges: "
        msg += ", ".join(userinfo["badges"])
        msg += "```"
        await self.bot.say(msg)

    @commands.group(pass_context=True)
    async def pref(self, ctx):
        """Préférences de profil joueur.

           pref info <info>
           pref titre <titre>
           COULEURS : -------------------------------------------------
           pref sidebar <rep_color> <badge_col_color> (1)
           pref rang_xp <exp_color> (1)
           pref profil_exp <exp_color> (1)
           (1) ... auto - pour faire selon la couleur d'arrière plan
           ARRIÈRE PLANS : --------------------------------------------
           pref liste_bgs
           pref rang_bg <image_name>
           pref profil_bg <image_name>
           pref level_bg <image_name>

        """
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            return
            
    @pref.command(pass_context=True, no_pm=True)
    async def liste_bgs(self, ctx):
        '''Donne une liste d'arrière plans.'''
        server = ctx.message.server

        if self.settings["disabled_server"]:
            await self.bot.say("**Les commandes d'XP pour ce serveur sont désactivées!**")
            return

        msg = ""
        for category in self.backgrounds.keys():
            msg += "**{}**".format(category.upper())
            msg += "```ruby\n"
            msg += ", ".join(sorted(self.backgrounds[category].keys()))
            msg += "```\n"
        await self.bot.say(msg)

    @commands.cooldown(rate = '1', per = '3')
    @pref.command(pass_context=True, no_pm=True)
    async def sidebar(self, ctx, rep_color:str, badge_col_color:str):
        """Définit les couleurs de badges et de réput."""

        user = ctx.message.author
        server = ctx.message.server

        if self.settings["disabled_server"]:
            await self.bot.say("**Les commandes d'XP pour ce serveur sont désactivées!**")
            return

        if self.settings["text_only"]:
            await self.bot.say("**Seules les commandes pour la version texte sont permises.**")
            return

        default_rep = (92,130,203,230)
        default_badge_col = (128,151,165,230)
        default_a = 230
        valid = True
        hex_color = None
        rep_rank = int(random.randint(2,3))
        color_ranks = [rep_rank, 0] # ajoute un peu d'aléatoire à la couleur de réputation en plus des couleurs proéminentes

        # Création de l'utilisateur s'il n'existe pas
        await self._create_user(user, server)

        # TODO : toujours horrible, à corriger plus tard
        if rep_color == "auto":
            hex_color = await self._auto_color(self.users[user.id]["profile_background"], color_ranks)
            color = self._hex_to_rgb(hex_color[0], default_a)
            color = self._moderate_color(color, default_a, 5)
            self.users[user.id]["rep_color"] = color                 
        elif rep_color == "default":
            self.users[user.id]["rep_color"] = default_rep
        elif self._is_hex(rep_color):
            self.users[user.id]["rep_color"] = self._hex_to_rgb(rep_color, default_a)
        else: 
            await self.bot.say("**Ce n'est pas une couleur valide de réputation!**")
            valid = False

        if badge_col_color == "auto":
            if hex_color != None:
                hex_color = hex_color[1] # récupère les autres couleurs
            else:
                hex_color = await self._auto_color(self.users[user.id]["profile_background"], [0])
                hex_color = hex_color[0] 
            color = self._hex_to_rgb(hex_color, default_a)
            color = self._moderate_color(color, default_a, 15)           
            self.users[user.id]["badge_col_color"] = color
        elif badge_col_color == "default":
            self.users[user.id]["badge_col_color"] = default_badge_col
        elif self._is_hex(badge_col_color):
            self.users[user.id]["badge_col_color"] = self._hex_to_rgb(badge_col_color, default_a)
        else: 
            await self.bot.say("**Ce n'est pas une couleur valide de colonne de badge!**")
            valid = False

        if valid:
            await self.bot.say("**{}, Votre couleur de barre de côté a été définit!**".format(self._is_mention(user)))
            fileIO(USERS, "save", self.users)

    @commands.cooldown(rate = '1', per = '3')
    @pref.command(pass_context=True, no_pm=True)
    async def profil_exp(self, ctx, exp_color:str):
        """Définit la couleur de profil d'expérience."""
        user = ctx.message.author
        server = ctx.message.server
        default_exp = (255, 255, 255, 230)
        default_a = 230
        valid = True
        color_rank = int(random.randint(2,3))

        if self.settings["disabled_server"]:
            await self.bot.say("Les commandes d'XP pour ce serveur sont désactivées.")
            return

        if self.settings["text_only"]:
            await self.bot.say("**Seules les commandes pour la version texte sont permises.**")
            return

        # Création de l'utilisateur s'il n'existe pas
        await self._create_user(user, server)

        if exp_color == "auto":
            hex_color = await self._auto_color(self.users[user.id]["profile_background"], [color_rank])
            color = self._hex_to_rgb(hex_color[0], default_a)
            color = self._moderate_color(color, default_a, 0)
            self.users[user.id]["profile_exp_color"] = color                 
        elif exp_color == "default":
            self.users[user.id]["profile_exp_color"] = default_exp
        elif self._is_hex(exp_color):
            self.users[user.id]["profile_exp_color"] = self._hex_to_rgb(exp_color, default_a)
        else: 
            await self.bot.say("**Ce n'est pas une couleur valide d'XP!**")
            valid = False

        if valid:
            await self.bot.say("**{}, les couleurs de profil d'xp sont définies!**".format(self._is_mention(user)))
            fileIO(USERS, "save", self.users)

    @commands.cooldown(rate = '1', per = '3')
    @pref.command(pass_context=True, no_pm=True)
    async def rang_xp(self, ctx, exp_color:str):
        """Définit la couleur du rang d'expérience."""
        user = ctx.message.author
        server = ctx.message.server
        default_exp = (255, 255, 255, 230)
        default_a = 230
        valid = True
        color_rank = int(random.randint(2,3))
        
        if self.settings["disabled_server"]:
            await self.bot.say("Les commandes d'XP pour ce serveur sont désactivées.")
            return

        if self.settings["text_only"]:
            await self.bot.say("**Seules les commandes pour la version texte sont permises.**")
            return

        # Création de l'utilisateur s'il n'existe pas
        await self._create_user(user, server)

        if exp_color == "auto":
            hex_color = await self._auto_color(self.users[user.id]["rank_background"], [color_rank])
            color = self._hex_to_rgb(hex_color[0], default_a)
            color = self._moderate_color(color, default_a, 0)
            self.users[user.id]["rank_exp_color"] = color          
        elif exp_color == "default":
            self.users[user.id]["rank_exp_color"] = default_exp
        elif self._is_hex(exp_color):
            self.users[user.id]["rank_exp_color"] = self._hex_to_rgb(exp_color, default_a)
        else: 
            await self.bot.say("**Ce n'est pas une couleur valide d'xp!**")
            valid = False

        if valid:
            await self.bot.say("**{}, vos couleurs de rang d'xp sont définit!**".format(self._is_mention(user)))
            fileIO(USERS, "save", self.users)

    @pref.command(pass_context=True, no_pm=True)
    async def info(self, ctx, *, info):
        """Définit les infos du joueur."""
        user = ctx.message.author
        server = ctx.message.server
        max_char = 150

        if self.settings["disabled_server"]:
            await self.bot.say("Les commandes d'XP pour ce serveur sont désactivées.")
            return

        # Création de l'utilisateur s'il n'existe pas
        await self._create_user(user, server)

        if len(info) < max_char:
            self.users[user.id]["info"] = info
            fileIO(USERS, "save", self.users)
            await self.bot.say("**Votre section info est définie!**")
        else:
            await self.bot.say("**Votre description a trop de caractères!\n"
                "Cela ne peut dépasser : {}**".format(max_char))

    @pref.command(pass_context=True, no_pm=True)
    async def level_bg(self, ctx, *, image_name:str):
        """Définit votre arrière plan de niveau."""
        user = ctx.message.author
        server = ctx.message.server

        if self.settings["disabled_server"]:
            await self.bot.say("Les commandes d'XP pour ce serveur sont désactivées.")
            return

        if self.settings["text_only"]:
            await self.bot.say("**Seules les commandes pour la version texte sont permises.**")
            return            

        # Création de l'utilisateur s'il n'existe pas
        await self._create_user(user, server)

        if image_name in self.backgrounds["levelup"].keys():
            if await self._process_purchase(ctx):
                self.users[user.id]["levelup_background"] = self.backgrounds["levelup"][image_name]
                fileIO(USERS, "save", self.users)
                await self.bot.say("**Votre nouvel arrière plan de niveau est défini!**")
        else:
            await self.bot.say("Ce n'est pas un arrière plan valide.\n"
                "Voir la liste des arrières disponibles {}pref liste_bgs.".format(prefix))

    @pref.command(pass_context=True, no_pm=True)
    async def profil_bg(self, ctx, *, image_name:str):
        """Définit votre arrière plan de profil."""
        user = ctx.message.author
        server = ctx.message.server

        if self.settings["disabled_server"]:
            await self.bot.say("Les commandes d'XP pour ce serveur sont désactivées.")
            return

        if self.settings["text_only"]:
            await self.bot.say("**Seules les commandes pour la version texte sont permises.**")
            return

        # Création de l'utilisateur s'il n'existe pas
        await self._create_user(user, server)

        if image_name in self.backgrounds["profile"].keys():
            if await self._process_purchase(ctx):
                self.users[user.id]["profile_background"] = self.backgrounds["profile"][image_name]
                fileIO(USERS, "save", self.users)
                await self.bot.say("**Votre nouvel arrière plan de profil est défini!**")
        else:
            await self.bot.say("Ce n'est pas un arrière plan valide.\n"
                "Voir la liste des arrières disponibles {}pref liste_bgs.".format(prefix))

    @pref.command(pass_context=True, no_pm=True)
    async def rang_bg(self, ctx, *, image_name:str):
        """Définit l'arrière plan de rang."""
        user = ctx.message.author
        server = ctx.message.server

        if self.settings["disabled_server"]:
            await self.bot.say("Les commandes d'XP pour ce serveur sont désactivées.")
            return

        if self.settings["text_only"]:
            await self.bot.say("**Seules les commandes pour la version texte sont permises.**")
            return
            
        # Création de l'utilisateur s'il n'existe pas
        await self._create_user(user, server)

        if image_name in self.backgrounds["rank"].keys():
            if await self._process_purchase(ctx):
                self.users[user.id]["rank_background"] = self.backgrounds["rank"][image_name]
                fileIO(USERS, "save", self.users)
                await self.bot.say("**Votre nouvel arrière plan de rang est défini!**")
        else:
            await self.bot.say("Ce n'est pas un arrière plan valide.\n"
                "Voir la liste des arrières disponibles {}pref liste_bgs.".format(prefix))

    @pref.command(pass_context=True, no_pm=True)
    async def titre(self, ctx, *, titre):
        """Définit votre titre."""
        user = ctx.message.author
        server = ctx.message.server
        max_char = 20

        if self.settings["disabled_server"]:
            await self.bot.say("Les commandes d'XP pour ce serveur sont désactivées.")
            return

        # Création de l'utilisateur s'il n'existe pas
        await self._create_user(user, server)

        if len(titre) < max_char:
            self.users[user.id]["titre"] = titre
            fileIO(USERS, "save", self.users)
            await self.bot.say("**Votre titre est défini!**")
        else:
            await self.bot.say("**Votre titre a trop de caractères! Cela ne doit pas dépasser {}**".format(max_char))

##############################################################################
# 
# COMMANDES DISPONIBLE POUR LES ADMINISTRATEURS (PUBLIC)
#
##############################################################################

    @checks.admin_or_permissions(manage_server=True)
    @commands.group(pass_context=True)
    async def admpref(self, ctx):
        """Réglages (admin)

           admpref voir
           admpref mention
           admpref bg_prix <price>
           admpref toggle
           admpref texte [tous_on/tous_off]
           admpref alerte [tous_on/tous_off]
           admpref en_mp [tous_on/tous_off]
           admpref lock 

        """
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            return

    @checks.admin_or_permissions(manage_server=True)
    @admpref.command(pass_context=True, no_pm=True)
    async def voir(self, ctx):
        """Affiche les réglages existants."""
        disabled_servers = []
        private_levels = []
        enabled_levels = []
        locked_channels = []
        server = ctx.message.server

        if self.servers[server.id]["settings"]["disabled_server"]:
            disabled_servers.append("\n\t{} -> Inactif".format(server.name))
        else:
            disabled_servers.append("\n\t{} -> Actif".format(server.name))
        if self.servers[server.id]["settings"]["lvl_msg_lock"] != "tous":
            for channel in server.channels:
                if self.servers[server.id]["settings"]["lvl_msg_lock"] == int(channel.id):
                    locked_channels.append("\n\t{} -> #{}".format(server.name, channel.name))
        else:
            locked_channels.append("\n\t{} -> TOUS les channels".format(server.name))  
        if self.servers[server.id]["settings"]["lvl_msg"]:
            enabled_levels.append("\n\t{} -> Actif".format(server.name))
        else:
            enabled_levels.append("\n\t{} -> Inactif".format(server.name))
        if self.servers[server.id]["settings"]["private_lvl_msg"]:
            private_levels.append("\n\t{} -> Actif".format(server.name))
        else:
            private_levels.append("\n\t{} -> Inactif".format(server.name))
        # construction du message
        msg = "```xl\n"
        msg += "Mentionner: {}\n".format(str(self.settings["mention"]))
        msg += "Prix des arrière plans: {}\n".format(locale.currency( self.settings["bg_price"], grouping=True ))
        msg += "Type de badge: {}\n".format(self.settings["badge_type"])
        msg += "État des Serveurs: {}\n".format(", ".join(disabled_servers))
        msg += "Activation des Messages de niveaux: {}\n".format(", ".join(enabled_levels))
        msg += "Messages de niveaux en Privé: {}\n".format(", ".join(private_levels))
        msg += "Affiche les messages de niveaux dans : {}\n".format(", ".join(locked_channels))
        msg += "```"
        await self.bot.say(msg)

    @checks.admin_or_permissions(manage_server=True)
    @admpref.command(pass_context=True, no_pm=True)
    async def lock(self, ctx):
        '''N'affiche les niv. que dans le channel courant.'''
        channel = ctx.message.channel

        if channel.id in self.settings["lvl_msg_lock"]:
            self.settings["lvl_msg_lock"] = "tous"
            await self.bot.say("**Affichage** des messages de niveaux dans un channel unique **désactivé**.".format(channel.name))
        else:
            self.settings["lvl_msg_lock"] = channel.id
            await self.bot.say("**Affichage** des messages de niveaux uniquement dans **#{}**.".format(channel.name))

        self._save_settings_bgs(ctx)

    @checks.admin_or_permissions(manage_server=True)
    @admpref.command(pass_context=True, no_pm=True)
    async def bg_prix(self, ctx, price:int):
        '''Définit un prix pour changer d'arrière plan.'''
        if price < 0:
            await self.bot.say("**Ce n'est pas un prix valide.**")
        else:
            self.settings["bg_price"] = price
            await self.bot.say("Prix de l'arrière plan définit à **{}!**".format(locale.currency( price, grouping=True )))
            self._save_settings_bgs(ctx)

    # @checks.admin_or_permissions(manage_server=True)
    # @admpref.command(pass_context=True, no_pm=True)
    # async def def_level(self, ctx, user : discord.Member, level:int):
        '''Définit le niveau d'un utilisateur.'''
        # org_user = ctx.message.author
        # server = user.server

        # if self.settings["disabled_server"]:
        #     await self.bot.say("Les commandes d'XP pour ce serveur sont désactivées.")
        #     return

        # if level < 0:
        #     await self.bot.say("**Entrez un nombre positif svp.**")
        #     return
            
        # # Création de l'utilisateur s'il n'existe pas
        # await self._create_user(user, server)

        # # on se débarasse de l'ancien exp
        # old_server_exp = 0
        # for i in range(self.users[user.id]["servers"][server.id]["level"]):
        #     old_server_exp += self._required_exp(i)
        # self.users[user.id]["total_exp"] -= old_server_exp
        # self.users[user.id]["total_exp"] -= self.users[user.id]["servers"][server.id]["current_exp"]

        # # on ajoute le nouvel exp
        # total_exp = 0
        # for i in range(level):
        #     total_exp += self._required_exp(i)
        # self.users[user.id]["servers"][server.id]["current_exp"] = 0
        # self.users[user.id]["servers"][server.id]["level"] = level
        # self.users[user.id]["total_exp"] += total_exp

        # fileIO(USERS, "save", self.users)
        # await self.bot.say("**Pour le joueur {} le niveau est définit à {}.**".format(self._is_mention(user), level))

    @checks.admin_or_permissions(manage_server=True)
    @admpref.command(pass_context=True, no_pm=True)
    async def mention(self, ctx):
        '''Active/désactive @mention dans les messages.'''
        if self.settings["mention"]:
            self.settings["mention"] = False
            await self.bot.say("**Mentions désactivées.**")
        else:
            self.settings["mention"] = True
            await self.bot.say("**Mentions activées.**")
        self._save_settings_bgs()

    @checks.admin_or_permissions(manage_server=True)
    @admpref.command(pass_context=True, no_pm=True)
    async def toggle(self, ctx):
        """Active/désactive XP pour le serveur courant."""
        server = ctx.message.server
        if self.settings["disabled_server"]:
            self.settings["disabled_server"] = False
            await self.bot.say("**XP activé sur {}.**".format(server.name))
        else:
            self.settings["disabled_server"] = True
            await self.bot.say("**XP désactivé sur {}.**".format(server.name))
        self._save_settings_bgs(ctx)

    @checks.admin_or_permissions(manage_server=True)
    @admpref.command(pass_context = True, no_pm=True)
    async def texte(self, ctx):
        """Active/désactive la version texte des messages."""
        server = ctx.message.server
        user = ctx.message.author

        if self.settings["text_only"]:
            self.settings["text_only"] = False
            await self.bot.say("**Version uniquement texte des messages désactivée pour {}.**".format(server.name))
        else:
            self.settings["text_only"] = True
            await self.bot.say("**Version uniquement texte des messages activée pour {}.**".format(server.name)) 
        # if user.id == self.owner:
        # else:
        #     await self.bot.say("**Vous n'avez pas les permissions nécessaires.**")      
        self._save_settings_bgs(ctx)

    @checks.admin_or_permissions(manage_server=True)
    @admpref.command(pass_context = True, no_pm=True)
    async def alerte(self, ctx, all:str=None):
        """Active/désactive les messages de niveaux."""
        server = ctx.message.server

        if self.settings["lvl_msg"]:
            self.settings["lvl_msg"] = False
            await self.bot.say("**Les messages de niveaux sont désactivés pour {}.**".format(server.name))
        else:
            self.settings["lvl_msg"] = True
            await self.bot.say("**Les messages de niveaux sont activés pour {}.**".format(server.name)) 
        self._save_settings_bgs(ctx)

    @checks.admin_or_permissions(manage_server=True)
    @admpref.command(pass_context = True, no_pm=True)
    async def en_mp(self, ctx, all:str=None):
        """Active/désactive les messages de niveaux en MP."""
        server = ctx.message.server
 
        if self.settings["private_lvl_msg"]:
            self.settings["private_lvl_msg"] = False
            await self.bot.say("**Les messages de niveaux en privé sont désactivés pour {}.**".format(server.name))
        else:
            self.settings["private_lvl_msg"] = True
            await self.bot.say("**Les messages de niveaux en privé sont activés pour {}.**".format(server.name))

        self._save_settings_bgs(ctx)             

    @commands.group(pass_context=True)
    async def abadge(self, ctx):
        """Gestion des Badges (admin)

            abadge ajout <name> <priority_num> <text_color> <bg_color> [border_color] (1)
            abadge suppr <name>
            abadge type <name>
            abadge donne <user> <badge_name>
            abadge prend <user> <badge_name>

            (1) Colors in Hex.

        """
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            return 

    @checks.admin_or_permissions(manage_server=True)
    @abadge.command(no_pm=True)
    async def ajout(self, name:str, priority_num: int, text_color:str, bg_color:str, border_color:str = None):
        """Ajoute un badge."""

        if not self._is_hex(text_color):
            await self.bot.say("**La couleur Hexa n'est pas valide!**")
            return

        if not self._is_hex(bg_color) and not await self._valid_image_url(bg_color):
            await self.bot.say("**Arrière plan non valide. Entrez l'hexa ou l'url de l'image!**")
            return

        if not border_color and self._is_hex(border_color):
            await self.bot.say("**La couleur de bordure n'est pas valide!**")
            return

        if name in self.badges:
            await self.bot.say("**{} badge mis-à-jour.**".format(name))
        else:
            await self.bot.say("**{} badge ajouté.**".format(name))

        self.badges[name] = {
            "priority_num": priority_num,
            "text_color" : text_color,
            "bg_color": bg_color,
            "border_color": border_color
        }

        fileIO(BADGES, "save", self.badges)

    @checks.admin_or_permissions(manage_server=True)
    @abadge.command(pass_context=True, no_pm=True)
    async def type(self, ctx, name:str):
        """circles, bars, ou squares."""
        valid_types = ["circles", "bars", "squares"]
        if name.lower() not in valid_types:
            await self.bot.say("**C'est n'est pas un type de badge valide!**\n"
                "les types valides sont : **{}**".format(join(valid_types)))
            return 

        self.settings["badge_type"] = name.lower()
        await self.bot.say("**Type de badge définit en {}**".format(name.lower()))
        
        self._save_settings_bgs(ctx) 

    @checks.admin_or_permissions(manage_server=True)
    @abadge.command(pass_context = True, no_pm=True)
    async def suppr(self, ctx, name:str):
        """Supprime un badge."""
        channel = ctx.message.channel
        server = user.server

        if self.settings["disabled_server"]:
            await self.bot.say("Les commandes d'XP pour ce serveur sont désactivées.")
            return

        if name in self.badges:
            del self.badges[name]

            # remove the badge if there
            for userid in self.users.keys():
                if name in self.users[userid]["badges"]:
                    self.users[userid]["badges"].remove(name)

            await self.bot.say("**Le badge {} est supprimé.**".format(name))
            fileIO(USERS, "save", self.users)
            fileIO(BADGES, "save", self.badges)
        else:
            await self.bot.say("**Ce badge n'existe pas.**")

    @checks.admin_or_permissions(manage_server=True)
    @abadge.command(pass_context = True, no_pm=True)
    async def donne(self, ctx, user : discord.Member, badge_name: str):
        """Donne un badge à un joueur."""
        org_user = ctx.message.author
        server = org_user.server

        if self.settings["disabled_server"]:
            await self.bot.say("Les commandes d'XP pour ce serveur sont désactivées.")
            return

        # Création de l'utilisateur s'il n'existe pas
        await self._create_user(user, server)

        if badge_name not in self.badges:
            await self.bot.say("**Ce badge n'existe pas!**")
        elif badge_name in self.users[user.id]["badges"]:
            await self.bot.say("**{} a déjà ce badge!**".format(self.user.mention))
        else:     
            self.users[user.id]["badges"].append(badge_name)
            fileIO(USERS, "save", self.users)
            await self.bot.say("**{} viens de donner à {} le badge {} !**".format(self._is_mention(org_user), self._is_mention(user), badge_name))

    @checks.admin_or_permissions(manage_server=True)
    @abadge.command(pass_context = True, no_pm=True)
    async def prend(self, ctx, user : discord.Member, badge_name: str):
        """Reprend un badge à un utilisateur."""
        org_user = ctx.message.author
        server = org_user.server

        if self.settings["disabled_server"]:
            await self.bot.say("Les commandes d'XP pour ce serveur sont désactivées.")
            return

        # Création de l'utilisateur s'il n'existe pas
        await self._create_user(user, server)

        if badge_name not in self.badges:
            await self.bot.say("**Ce bdage n'existe pas!**")
        elif badge_name not in self.users[user.id]["badges"]:
            await self.bot.say("**{} n'a pas ce badge!**".format(self._is_mention(user)))
        else:
            self.users[user.id]["badges"].remove(badge_name)
            fileIO(USERS, "save", self.users)
            await self.bot.say("**{} a prit le badge {} de {}! :upside_down:**".format(self._is_mention(org_user), badge_name, self._is_mention(user)))

    @commands.group(pass_context=True)
    async def abackg(self, ctx):
        """Gestion des arrière-plans (admin)

           abackg profil_add <name> <url> (1)
           abackg profil_del <name>
           abackg rang_add <name> <url> (2)
           abackg rang_del <name>
           abackg level_add <name> <url> (3)
           abackg level_del <name>

           (1) Proportions: (290px x 290px)
           (2) Proportions: (360px x 100px)
           (3) Proportions: (85px x 105px)

        """
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            return

    @checks.admin_or_permissions(manage_server=True)
    @abackg.command(pass_context=True, no_pm=True)
    async def profil_add(self, ctx, name:str, url:str):
        """Ajoute un arrière plan de profil."""
        if name in self.backgrounds["profile"].keys():
            await self.bot.say("**Le nom de cet arrière plan de profil existe déjà!**")
        elif not await self._valid_image_url(url):
            await self.bot.say("**Ce n'est pas une url d'image valide!**")  
        else:          
            self.backgrounds["profile"][name] = url
            self._save_settings_bgs(ctx)                          
            await self.bot.say("**Nouvel arrière plan de profil (`{}`) ajouté.**".format(name))

    @checks.admin_or_permissions(manage_server=True)
    @abackg.command(pass_context=True, no_pm=True)
    async def profil_del(self, ctx, name:str):
        '''Supprime un arrière plan de profil.'''
        if name in self.backgrounds["profile"].keys():
            del self.backgrounds["profile"][name]
            self._save_settings_bgs(ctx)
            await self.bot.say("**L'arrière plan de profil (`{}`) est supprimé.**".format(name))
        else:                                 
            await self.bot.say("**Ce nom d'arrière plan de profil n'existe pas.**")

    @checks.admin_or_permissions(manage_server=True)
    @abackg.command(pass_context=True, no_pm=True)
    async def rang_add(self, ctx, name:str, url:str):
        """Ajoute un arrière plan de rang."""
        if name in self.backgrounds["rank"].keys():
            await self.bot.say("**Le nom de cet arrière plan de rang existe déjà!**")
        elif not await self._valid_image_url(url):
            await self.bot.say("**Ce n'est pas une url d'image valide!**") 
        else:
            self.backgrounds["rank"][name] = url
            self._save_settings_bgs(ctx)
            await self.bot.say("**Nouvel arrière plan de rang (`{}`) ajouté.**".format(name))

    @checks.admin_or_permissions(manage_server=True)
    @abackg.command(pass_context=True, no_pm=True)
    async def rang_del(self, ctx, name:str):
        '''Supprime un arrière plan de rang.'''
        if name in self.backgrounds["rank"].keys():
            del self.backgrounds["rank"][name]
            self._save_settings_bgs(ctx)
            await self.bot.say("**L'arrière plan de rang (`{}`) est supprimé.**".format(name))
        else:                                 
            await self.bot.say("**Ce nom d'arrière plan de rang n'existe pas.**")

    @checks.admin_or_permissions(manage_server=True)
    @abackg.command(pass_context=True, no_pm=True)
    async def level_add(self, ctx, name:str, url:str):
        '''Ajoute un arrière plan de niveaux.'''
        if name in self.backgrounds["levelup"].keys():
            await self.bot.say("**Le nom de cet arrière plan de niveau existe déjà!**")
        elif not await self._valid_image_url(url):
            await self.bot.say("**Ce n'est pas une url d'image valide!**") 
        else:
            self.backgrounds["levelup"][name] = url
            self._save_settings_bgs(ctx)
            await self.bot.say("**Nouvel arrière plan de niveau (`{}`) ajouté.**".format(name))

    @checks.admin_or_permissions(manage_server=True)
    @abackg.command(pass_context=True, no_pm=True)
    async def level_del(self, ctx, name:str):
        '''Supprime un arrière plan de niveaux.'''
        if name in self.backgrounds["levelup"].keys():
            del self.backgrounds["levelup"][name]
            self._save_settings_bgs(ctx)
            await self.bot.say("**L'arrière plan de niveau (`{}`) est supprimé.**".format(name))
        else:                                 
            await self.bot.say("**Ce nom d'arrière plan de niveau n'existe pas.**")

##############################################################################
# 
# FONCTIONS EXTERNES A LA CLASSE (PUBLIC)
#
##############################################################################

    # Charge un nouveau message dans le model
    async def on_message(self, message): 
        t = threading.Thread(target = await self._handle_on_message(message))
        self.threads.append(t)
        t.start()

    async def rank_text(self, user, server):
        userinfo = self.users[user.id]
        msg = "```ruby\n"
        msg += "Nom: {}\n".format(user.name)
        msg += "Réput.: {}\n".format(self.users[user.id]["rep"])   
        msg += "Rang Serveur: {}\n".format(await self._find_server_rank(user, server))
        msg += "Niveau Serveur: {}\n".format(self.users[user.id]["servers"][server.id]["level"])
        msg += "Serveur exp: {}\n".format(userinfo["servers"][server.id]["total_xp"])
        msg += "```"
        return msg

    async def draw_levelup(self, user, server):
        userinfo = self.users[user.id]
        # get urls
        bg_url = userinfo["levelup_background"]
        profile_url = user.avatar_url         

        # create image objects
        bg_image = Image
        profile_image = Image   
    
        await self._make_temp_image(bg_url, "level", user)

        bg_image = Image.open(GENPATH+'/temp_level_bg{}.png'.format(user.id)).convert('RGBA')            
        profile_image = Image.open(GENPATH+'/temp_level_profile{}.png'.format(user.id)).convert('RGBA')

        # set canvas
        bg_color = (255,255,255, 0)
        result = Image.new('RGBA', (85, 105), bg_color)
        process = Image.new('RGBA', (85, 105), bg_color)

        # draw
        draw = ImageDraw.Draw(process)

        # puts in background
        bg_image = bg_image.resize((85, 105), Image.ANTIALIAS)
        bg_image = bg_image.crop((0,0, 85, 105))
        result.paste(bg_image, (0,0))

        # draw transparent overlay   
        draw.rectangle([(0, 40), (85, 105)], fill=(30, 30 ,30, 220)) # white portion
        draw.rectangle([(15, 11), (68, 64)], fill=(255,255,255,160), outline=(100, 100, 100, 100)) # profile rectangle

        # put in profile picture
        profile_size = (50, 50)
        profile_image = profile_image.resize(profile_size, Image.ANTIALIAS)
        process.paste(profile_image, (17, 13))

        # fonts
        level_fnt2 = ImageFont.truetype(font_bold_file, 20)
        level_fnt = ImageFont.truetype(font_bold_file, 32)

        # write label text
        draw.text((self._center(0, 85, "Level Up!", level_fnt2), 65), "Level Up!", font=level_fnt2, fill=(240,240,240,255)) # Level
        lvl_text = "LVL {}".format(userinfo["servers"][server.id]["level"])
        draw.text((self._center(0, 85, lvl_text, level_fnt), 80), lvl_text, font=level_fnt, fill=(240,240,240,255)) # Level Number

        result = Image.alpha_composite(result, process)
        result.save(GENPATH+'/level{}.png'.format(user.id),'PNG', quality=100)

    async def draw_rank(self, user, server):

        # fonts
        name_fnt = ImageFont.truetype(font_bold_file, 22)
        header_u_fnt = ImageFont.truetype(font_unicode_file, 18)
        sub_header_fnt = ImageFont.truetype(font_bold_file, 14)
        badge_fnt = ImageFont.truetype(font_bold_file, 12)
        large_fnt = ImageFont.truetype(font_bold_file, 33)
        level_label_fnt = ImageFont.truetype(font_bold_file, 22)
        general_info_fnt = ImageFont.truetype(font_bold_file, 15)
        general_info_u_fnt = ImageFont.truetype(font_unicode_file, 11)
        credit_fnt = ImageFont.truetype(font_bold_file, 10)

        userinfo = self.users[user.id]

        # get urls
        bg_url = userinfo["rank_background"]
        profile_url = user.avatar_url         

        # create image objects
        bg_image = Image
        profile_image = Image      
    
        await self._make_temp_image(bg_url, "rank", user)

        bg_image = Image.open(GENPATH+'/temp_rank_bg{}.png'.format(user.id)).convert('RGBA')            
        profile_image = Image.open(GENPATH+'/temp_rank_profile{}.png'.format(user.id)).convert('RGBA')

        # set canvas
        bg_color = (255,255,255, 0)
        result = Image.new('RGBA', (360, 100), bg_color)
        process = Image.new('RGBA', (360, 100), bg_color)
        
        # puts in background
        bg_image = bg_image.resize((360, 100), Image.ANTIALIAS)
        bg_image = bg_image.crop((0,0, 360, 100))
        result.paste(bg_image, (0,0))

        # draw
        draw = ImageDraw.Draw(process)

        # draw transparent overlay
        vert_pos = 5
        left_pos = 70
        right_pos = 360 - vert_pos
        titre_height = 22
        gap = 3

        draw.rectangle([(left_pos - 20,vert_pos), (right_pos, vert_pos + titre_height)], fill=(230,230,230,230)) # titre box
        content_top = vert_pos + titre_height + gap
        content_bottom = 100 - vert_pos
        draw.rectangle([(left_pos - 20, content_top), (right_pos, content_bottom)], fill=(30, 30 ,30, 220), outline=(230,230,230,230)) # content box

        # stick in credits if needed
        if bg_url in bg_credits.keys():
            credit_text = " ".join("{}".format(bg_credits[bg_url]))
            draw.text((2, 92), credit_text,  font=credit_fnt, fill=(0,0,0,190))

        # draw level circle
        multiplier = 6  
        lvl_circle_dia = 94
        circle_left = 15
        circle_top = int((100 - lvl_circle_dia)/2)
        raw_length = lvl_circle_dia * multiplier

        # create mask
        mask = Image.new('L', (raw_length, raw_length), 0)
        draw_thumb = ImageDraw.Draw(mask)
        draw_thumb.ellipse((0, 0) + (raw_length, raw_length), fill = 255, outline = 0)

        # drawing level bar calculate angle
        start_angle = -90 # from top instead of 3oclock
        angle = int(360 * (userinfo["current_xp"]/self._get_next_level(userinfo["servers"][server.id]["level"]))) + start_angle
     
        lvl_circle = Image.new("RGBA", (raw_length, raw_length))
        draw_lvl_circle = ImageDraw.Draw(lvl_circle)
        draw_lvl_circle.ellipse([0, 0, raw_length, raw_length], fill=(180, 180, 180, 180), outline = (255, 255, 255, 220))
        # determines exp bar color
        if "rank_exp_color" not in userinfo.keys() or not userinfo["rank_exp_color"]:
            exp_fill = (255, 255, 255, 230)
        else:
            exp_fill = tuple(userinfo["rank_exp_color"])
        draw_lvl_circle.pieslice([0, 0, raw_length, raw_length], start_angle, angle, fill=exp_fill, outline = (255, 255, 255, 230))
        # put on level bar circle
        lvl_circle = lvl_circle.resize((lvl_circle_dia, lvl_circle_dia), Image.ANTIALIAS)
        lvl_bar_mask = mask.resize((lvl_circle_dia, lvl_circle_dia), Image.ANTIALIAS)
        process.paste(lvl_circle, (circle_left, circle_top), lvl_bar_mask)       

        # draws mask
        total_gap = 10
        border = int(total_gap/2)
        profile_size = lvl_circle_dia - total_gap
        raw_length = profile_size * multiplier

        # put in profile picture
        output = ImageOps.fit(profile_image, (raw_length, raw_length), centering=(0.5, 0.5))
        output = output.resize((profile_size, profile_size), Image.ANTIALIAS)
        mask = mask.resize((profile_size, profile_size), Image.ANTIALIAS)      
        profile_image = profile_image.resize((profile_size, profile_size), Image.ANTIALIAS)
        process.paste(profile_image, (circle_left + border, circle_top + border), mask)
        
        # draw level box
        level_left = 277
        level_right = right_pos
        draw.rectangle([(level_left, vert_pos), (level_right, vert_pos + titre_height)], fill="#AAA") # box
        lvl_text = "NIVEAU {}".format(userinfo["servers"][server.id]["level"])     
        draw.text((self._center(level_left, level_right, lvl_text, level_label_fnt), vert_pos + 2), lvl_text,  font=level_label_fnt, fill=(110,110,110,255)) # Level #

        # draw text
        grey_color = (110,110,110,255)
        white_color = (230,230,230,255)

        # reputation points
        left_text_align = 130
        rep_align = self._center(110, 190, "Réput.", level_label_fnt)
        # _name(self, user, max_length)
        text_name = self._name(user, 21) 
        # print(text_name)
        # _truncate_text(self, text, max_length)
        truncated = self._truncate_text(text_name, 21) 
        # print(truncated)
        # _write_unicode(text, init_x, y, font, unicode_font, fill)
        self._write_unicode(truncated, 
            left_text_align - 20, 
            vert_pos + 2,
            name_fnt,
            header_u_fnt,
            grey_color, draw) # Name 
        draw.text((rep_align, 37), "Réput.".format(await self._find_server_rank(user, server)), font=level_label_fnt, fill=white_color) # Rep Label
        rep_label_width = level_label_fnt.getsize("Réput.")[0]
        rep_text = "+{}".format(userinfo["rep"])
        draw.text((self._center(rep_align, rep_align + rep_label_width, rep_text, large_fnt) , 63), rep_text, font=large_fnt, fill=white_color) # Rep
       
        # divider bar
        draw.rectangle([(190, 45), (191, 85)], fill=(160,160,160,240))      

        # labels
        label_align = 210
        draw.text((label_align, 38), "Rang Serveur:", font=general_info_fnt, fill=white_color) # Server Rank
        draw.text((label_align, 58), "XP Serveur:", font=general_info_fnt, fill=white_color) # Server Exp
        draw.text((label_align, 78), "Crédits:", font=general_info_fnt, fill=white_color) # Credit
        # info
        right_text_align = 290
        rank_txt = "#{}".format(await self._find_server_rank(user, server))
        draw.text((right_text_align, 38), self._truncate_text(rank_txt, 12) , font=general_info_fnt, fill=white_color) # Rank
        exp_txt = "{}".format(userinfo["servers"][server.id]["total_xp"])
        draw.text((right_text_align, 58), self._truncate_text(exp_txt, 12), font=general_info_fnt, fill=white_color) # Exp
        try:
            credits = self._get_solde(user)
        except:
            credits = 0
        credit_txt = "{}".format(credits)
        draw.text((right_text_align, 78), self._truncate_text(credit_txt, 12),  font=general_info_fnt, fill=white_color) # Credits

        result = Image.alpha_composite(result, process)
        result.save(GENPATH+'/rank{}.png'.format(user.id),'PNG', quality=100)

##############################################################################
# 
# FONCTIONS INTERNES A LA CLASSE (PRIVATE)
#
##############################################################################
    # essayer d'importer les fonctions bancaires avec 
    # from economy import bank
    async def _process_purchase(self, ctx):
        user = ctx.message.author
        server = ctx.message.server
        try:
            bank = self.bot.get_cog('Economy').bank
            if bank.account_exists(user):
                if not bank.can_spend(user, self.settings["bg_price"]):
                    await self.bot.say("**Fonds insuffisants.**\n"
                        "Coûts du changement d'arrière plan: **{}**".format(self.settings["bg_price"]))
                    return False
                else:
                    new_balance = bank.get_balance(user) - self.settings["bg_price"]
                    bank.set_credits(user, new_balance)
                    return True            
            else:
                if self.settings["bg_price"] == 0:
                    return True
                else:
                    await self.bot.say("{} n'a pas de compte bancaire.\n"
                        "Créer votre compte à la banque : **{}bank register**".format(prefix))
                    return False
        except:
            if self.settings["bg_price"] == 0:
                return True
            else:
                msg = "Il y a une **erreur** avec le module bancaire.\n"
                "Régler le problème pour permettre les achats ou\n"
                "définir le prix à 0. \n\n"
                "Actuellement il est de **{}**".format(prefix, self.settings["bg_price"])
                await self.bot.say(msg)
                return False  

    async def _make_temp_image(self, bg_url:str, whatfor:str, user ):
        async with aiohttp.get(bg_url) as r:
            image = await r.content.read()
            with open(GENPATH+'/temp_'+whatfor+'_bg{}.png'.format(user.id),'wb') as f:
                f.write(image)
            try:
                async with aiohttp.get(profile_url) as r:
                    image = await r.content.read()
            except:
                async with aiohttp.get(default_avatar_url) as r:
                    image = await r.content.read()
            with open(GENPATH+'/temp_'+whatfor+'_profile{}.png'.format(user.id),'wb') as f:
                f.write(image)

    async def _handle_on_message(self, message):
        
        text = message.content
        channel = message.channel
        server = message.server
        user = message.author
        curr_time = time.time()

        # Si l'utilisateur est un bot
        if user.bot:
            return

        # Première fois : création de l'entrée serveur 
        # Donne les réglages par défaut
        # et création des fichiers USERS et BLOCK rattachés
        try:
            if server.id not in self.servers:
                await self._create_server(server)
        except:
            pass

        self.settings = self.servers[server.id]["settings"]
        self.backgrounds = self.servers[server.id]["bgs"]

        # Inscrire les joueurs automatiquement ?
        if not self.servers[server.id]["settings"]["processed"]:
            await self._register_users(server)

        # Si le serveur est désactivé
        if self.servers[server.id]["settings"]["disabled_server"]:
            return

        # Création de l'utilisateur s'il n'existe pas.
        await self._create_user(user, server)

        # timeout pour ne pas spam l'xp 
        actual_interval = float(curr_time) - float(self.block[user.id]["chat"])

        if actual_interval >= float(self.settings["freq_xp"]):
            await self._process_xp(message)
            self.block[user.id]["chat"] = curr_time
            fileIO(BLOCK, "save", self.block)
        else:
            remaining_time = int(float(self.settings["freq_xp"]) - actual_interval) 


    async def _find_server_rank(self, user, server):
        targetid = user.id
        users = []
        for userid in self.users.keys():  # Je passe en revue tous les userid du fichiers USERS
            if server.id in self.users[userid]["servers"]: # Je cherche uniquement les occurences de server.id
                temp_user = find(lambda m: m.id == userid, server.members) # je cherche l'utilisateur dans les membres du serveurs
                server_exp = self.users[userid]["servers"][server.id]["total_xp"] # récupère l'xp du user pour ce serveur
                if temp_user != None:
                    users.append((userid, temp_user.name, server_exp)) # Récupère une liste : (user : totalXP) pour ce serveur             
        sorted_list = sorted(users, key=lambda us: us[2], reverse =True) # tri la liste

        # récupère l'index de l'utilisateur concerné = rang
        rank = 1
        for user in sorted_list:
            if user[0] == targetid:
                return rank
            rank+=1

    async def _find_global_rank(self, user, server):
        users = []
        for userid in self.users.keys():
            temp_user = find(lambda m: m.id == userid, server.members) # je cherche l'utilisateur dans les membres du serveurs
            global_xp = self.users[userid]["global_xp"] # récupère l'xp du user pour ce serveur
            if temp_user != None:
                users.append((userid, temp_user.name, self.users[userid]["global_xp"]))
        sorted_list = sorted(users, key=lambda us: us[2], reverse=True)

        rank = 1
        for stats in sorted_list:
            if stats[0] == user.id:
                return rank
            rank+=1

    async def _process_xp(self, message):

        channel = message.channel
        server = channel.server
        user = message.author

        # tirage au sort d'un montant d'xp    
        loto_xp = self._get_random_xp()

        # ajoute l'xp au montant total d'xp gagné
        # au global
        # au local
        self.users[user.id]["global_xp"] += loto_xp
        self.users[user.id]["servers"][server.id]["total_xp"] += loto_xp

        # calcul la taille de l'intervalle d'xp en fonction du level
        xp_requis = self._get_next_level(self.users[user.id]["servers"][server.id]["level"])

        xp_acquis = self.users[user.id]["current_xp"] + loto_xp

        if xp_acquis >= xp_requis:
            self.users[user.id]["servers"][server.id]["level"] += 1
            self.users[user.id]["current_xp"] = int(xp_acquis - xp_requis)
            print("{} a gagné un niveau".format(user.name))

            # Doit-on faire un msg # TODO : Gestion des rewards avec les badges en fonction de l'XP
            if self.settings["lvl_msg"]:
                await self._level_msg(user, channel, server)
        else:
            self.users[user.id]["current_xp"] = xp_acquis
            #print("{} a gagné {} points".format(user.name, loto_xp))

        fileIO(USERS, "save", self.users)

    # Gère la création d'un utilisateur
    async def _create_user(self, user, server):

        # Si l'utilisateur est un bot
        if user.bot:
            return
        
        if user.id not in self.users: 
            info = "Je suis une personne mystérieuse. Pour changer les infos taper " + str(prefix[0]) + "pref."
            new_account = {
                "nom": user.name,
                "servers": {},
                "global_xp": 0,
                "current_xp": 0,
                "profile_background": self.backgrounds["profile"]["default"],
                "rank_background": self.backgrounds["rank"]["default"],
                "levelup_background": self.backgrounds["levelup"]["default"],
                "titre": "",
                "info": info, # TODO : généraliser l'accès  .format(prefix)
                "rep": 0,
                "badges":[],
                "rep_color": [],
                "badge_col_color": []
            }
            self.users[user.id] = new_account
            

        if server.id not in self.users[user.id]["servers"]:
            self.users[user.id]["servers"][server.id] = {
                "total_xp": 0,
                "level": 0,
            }

            fileIO(USERS, "save", self.users)

        if user.id not in self.block:
            self.block[user.id] = {
                "nom" : user.name,
                "chat" : 0.0,
                "rep" : 0.0,
                "rang" : 0
            }

            fileIO(BLOCK, "save", self.block)

    async def _register_users(self, serveur):
        for joueur in serveur.members:
            await self._create_user(joueur, serveur)

        self.servers[serveur.id]["settings"]["processed"]=True
        dataIO.save_json(SERVERS,self.servers)
        print("Membres du serveur {} sont inscrits : {}".format(serveur.name, self.servers[serveur.id]["settings"]["processed"]))  

    async def _create_server(self, serveur):
        self._save_settings()
        print("SERVERS JSON UPDATED WITH {}".format(serveur.name))

    async def _level_msg(self, user, channel, server):
    
        server_identifier = ""

        # Peux t on mentionner l'utilisateur
        name = self._is_mention(user)
        verbe = "vient"
        
        # Doit il aller dans un channel spécifique
        if self.settings["lvl_msg_lock"] is not None: 
            print("channel lock")
            channel_id = self.settings["lvl_msg_lock"]
            channel = find(lambda m: m.id == channel_id, server.channels)

        # Le message doit-il être privé
        if  self.settings["private_lvl_msg"]:
            print("privé")
            server_identifier = " sur {}".format(server.name)
            channel = user
            name = "Tu"
            verbe = "viens"
        
        # Doit-il être uniquement en version texte
        if self.settings["text_only"]: 
            await self.bot.send_typing(channel)
            await self.bot.send_message(channel, 
                content='**BRAVO ! {}** {} de gagner un niveau (LEVEL {})**'.format(name, verbe, self.users[user.id]["servers"][server.id]["level"]))
        else:
            await self.draw_levelup(user, server)
            await self.bot.send_typing(channel)        
            await self.bot.send_file(channel, 
                GENPATH+"/level{}.png".format(user.id), 
                content='**BRAVO ! {}** {} de gagner un niveau **(LEVEL {})**'.format(name, verbe, self.users[user.id]["servers"][server.id]["level"]))
            self._clear_folder()

    async def _valid_image_url(self, url):
        max_byte = 1000

        try:
            async with aiohttp.get(url) as r:
                image = await r.content.read()
            with open(GENPATH+'/test.png','wb') as f:
                f.write(image)
            image = Image.open(GENPATH+'/test.png').convert('RGBA')
            os.remove(GENPATH+'/test.png')
            return True
        except:          
            return False
        
    async def profile_text(self, user, server):
        userinfo = self.users[user.id]
        msg = "```ruby\n"
        msg += "Nom: {}\n".format(user.name)
        msg += "Titre: {}\n".format(userinfo["titre"])
        msg += "Réput.: {}\n".format(userinfo["rep"])            
        msg += "Rang Global: {}\n".format(await self._find_global_rank(user, server))
        msg += "Rang Serveur: {}\n".format(await self._find_server_rank(user, server))
        msg += "Niveau Serveur: {}\n".format(userinfo["servers"][server.id]["level"])
        msg += "Xp Serveur: {}\n".format(userinfo["total_xp"])
        msg += "Xp actuelle: {}\n".format(userinfo["current_exp"])
        try:
            credits = self._get_solde(user)
        except:
            credits = 0
        msg += "Crédits: {}\n".format(credits)
        msg += "Info: {}\n".format(userinfo["info"])
        msg += "Badges: "
        msg += ", ".join(userinfo["badges"])
        msg += "```"
        return msg

    async def draw_profile(self, user, server):
        name_fnt = ImageFont.truetype(font_bold_file, 22)
        header_u_fnt = ImageFont.truetype(font_unicode_file, 18)
        titre_fnt = ImageFont.truetype(font_file, 18)
        sub_header_fnt = ImageFont.truetype(font_bold_file, 14)
        badge_fnt = ImageFont.truetype(font_bold_file, 12)
        exp_fnt = ImageFont.truetype(font_bold_file, 13)
        large_fnt = ImageFont.truetype(font_bold_file, 33)
        level_label_fnt = ImageFont.truetype(font_bold_file, 22)
        general_info_fnt = ImageFont.truetype(font_bold_file, 15)
        general_info_u_fnt = ImageFont.truetype(font_unicode_file, 11)
        rep_fnt = ImageFont.truetype(font_bold_file, 30)
        text_fnt = ImageFont.truetype(font_bold_file, 12)
        text_u_fnt = ImageFont.truetype(font_unicode_file, 8)
        credit_fnt = ImageFont.truetype(font_bold_file, 10)

        # get urls
        userinfo = self.users[user.id]
        bg_url = userinfo["profile_background"]
        profile_url = user.avatar_url 

        # create image objects
        bg_image = Image
        profile_image = Image  

        await self._make_temp_image(bg_url, "profile", user) 

        bg_image = Image.open(GENPATH+'/temp_profile_bg{}.png'.format(user.id)).convert('RGBA')            
        profile_image = Image.open(GENPATH+'/temp_profile_profile{}.png'.format(user.id)).convert('RGBA')

        # set canvas
        bg_color = (255,255,255,0)
        result = Image.new('RGBA', (290, 290), bg_color)
        process = Image.new('RGBA', (290, 290), bg_color)

        # draw
        draw = ImageDraw.Draw(process)

        # puts in background
        bg_image = bg_image.resize((290, 290), Image.ANTIALIAS)
        bg_image = bg_image.crop((0,0, 290, 290))
        result.paste(bg_image, (0,0))

        # draw filter
        draw.rectangle([(0,0),(290, 290)], fill=(0,0,0,10))

        # draw transparent overlay
        vert_pos = 110
        left_pos = 70
        right_pos = 285
        titre_height = 22
        gap = 3

        # determines rep section color
        if "rep_color" not in userinfo.keys() or not userinfo["rep_color"]:
            rep_fill = (92,130,203,230)
        else:
            rep_fill = tuple(userinfo["rep_color"])
        # determines badge section color, should be behind the titrebar
        if "badge_col_color" not in userinfo.keys() or not userinfo["badge_col_color"]:
            badge_fill = (128,151,165,230)
        else:
            badge_fill = tuple(userinfo["badge_col_color"])

        draw.rectangle([(left_pos - 20, vert_pos + titre_height), (right_pos, 156)], fill=(40,40,40,230)) # titre box
        draw.rectangle([(100,159), (285, 212)], fill=(30, 30 ,30, 220)) # general content
        draw.rectangle([(100,215), (285, 285)], fill=(30, 30 ,30, 220)) # info content
        draw.rectangle([(105, 94), (290, 110)], fill=(rep_fill[0],rep_fill[1],rep_fill[2],160)) # XP/PROCHAIN NIVEAU

        # stick in credits if needed
        if bg_url in bg_credits.keys():
            credit_text = "  ".join("Background by {}".format(bg_credits[bg_url]))
            credit_init = 290 - credit_fnt.getsize(credit_text)[0]
            draw.text((credit_init, 0), credit_text,  font=credit_fnt, fill=(0,0,0,100))
        draw.rectangle([(5, vert_pos), (right_pos, vert_pos + titre_height)], fill=(230,230,230,230)) # name box in front

        # draw level circle
        multiplier = 8
        lvl_circle_dia = 104
        circle_left = 1
        circle_top = 42
        raw_length = lvl_circle_dia * multiplier

        # create mask
        mask = Image.new('L', (raw_length, raw_length), 0)
        draw_thumb = ImageDraw.Draw(mask)
        draw_thumb.ellipse((0, 0) + (raw_length, raw_length), fill = 255, outline = 0)

        # drawing level bar calculate angle
        start_angle = -90 # from top instead of 3oclock
        angle = int(360 * (userinfo["current_xp"]/self._get_next_level(userinfo["servers"][server.id]["level"]))) + start_angle

        # level outline
        lvl_circle = Image.new("RGBA", (raw_length, raw_length))
        draw_lvl_circle = ImageDraw.Draw(lvl_circle)
        draw_lvl_circle.ellipse([0, 0, raw_length, raw_length], fill=(badge_fill[0], badge_fill[1], badge_fill[2], 180), outline = (255, 255, 255, 250))
        # determines exp bar color
        if "profile_exp_color" not in userinfo.keys() or not userinfo["profile_exp_color"]:
            exp_fill = (255, 255, 255, 230)
        else:
            exp_fill = tuple(userinfo["profile_exp_color"])
        draw_lvl_circle.pieslice([0, 0, raw_length, raw_length], start_angle, angle, fill=exp_fill, outline = (255, 255, 255, 255))
        # put on level bar circle
        lvl_circle = lvl_circle.resize((lvl_circle_dia, lvl_circle_dia), Image.ANTIALIAS)
        lvl_bar_mask = mask.resize((lvl_circle_dia, lvl_circle_dia), Image.ANTIALIAS)
        process.paste(lvl_circle, (circle_left, circle_top), lvl_bar_mask)  

        # draws boxes
        draw.rectangle([(5,133), (100, 285)], fill= badge_fill) # badges
        draw.rectangle([(10,138), (95, 168)], fill = rep_fill) # reps

        total_gap = 10
        border = int(total_gap/2)
        profile_size = lvl_circle_dia - total_gap
        raw_length = profile_size * multiplier
        # put in profile picture
        output = ImageOps.fit(profile_image, (raw_length, raw_length), centering=(0.5, 0.5))
        output = output.resize((profile_size, profile_size), Image.ANTIALIAS)
        mask = mask.resize((profile_size, profile_size), Image.ANTIALIAS)      
        profile_image = profile_image.resize((profile_size, profile_size), Image.ANTIALIAS)
        process.paste(profile_image, (circle_left + border, circle_top + border), mask)
        
        # write label text
        white_color = (240,240,240,255)
        light_color = (160,160,160,255)

        head_align = 105
        self._write_unicode(self._truncate_text(self._name(user, 24), 24), head_align, vert_pos + 3, level_label_fnt, header_u_fnt, (110,110,110,255), draw) # NAME
        self._write_unicode(userinfo["titre"], head_align, 136, level_label_fnt, header_u_fnt, white_color, draw)

        # draw level box
        level_right = 290
        level_left = level_right - 72
        draw.rectangle([(level_left, 0), (level_right, 21)], fill=(rep_fill[0],rep_fill[1],rep_fill[2],160)) # box
        lvl_text = "NIVEAU {}".format(userinfo["servers"][server.id]["level"])
        if badge_fill == (128,151,165,230):
            lvl_color = white_color
        else:
            lvl_color = self._contrast(rep_fill, badge_fill)   
        draw.text((self._center(level_left, level_right, lvl_text, level_label_fnt), 2), lvl_text,  font=level_label_fnt, fill=(lvl_color[0],lvl_color[1],lvl_color[2],255)) # Level #

        rep_text = "+{} rép.".format(userinfo["rep"])
        draw.text((self._center(5, 100, rep_text, rep_fnt), 141), rep_text, font=rep_fnt, fill=white_color)

        draw.text((self._center(5, 100, "Badges", sub_header_fnt), 173), "Badges", font=sub_header_fnt, fill=white_color) # Badges   

        # XP / Prochain niveau
        exp_text = "{}/{}".format(userinfo["current_xp"], int(self._get_next_level(userinfo["servers"][server.id]["level"]))) # Exp
        exp_color = self._contrast(badge_fill, exp_fill)
        draw.text((105, 99), exp_text,  font=exp_fnt, fill=(exp_color[0], exp_color[1], exp_color[2], 255)) # Exp Text
        
        lvl_left = 100
        label_align = 105
        self._write_unicode(u"Rang:", label_align, 165, general_info_fnt, general_info_u_fnt, light_color, draw)
        draw.text((label_align, 180), "Xp:",  font=general_info_fnt, fill=light_color) # Exp
        draw.text((label_align, 195), "Crédits:",  font=general_info_fnt, fill=light_color) # Credits

        # local stats
        num_local_align = 180
        local_symbol = u"\U0001F3E0 "
        if "linux" in platform.system().lower():
            local_symbol = u"\U0001F3E0 "
        else:
            local_symbol = "S "

        s_rank_txt = local_symbol + self._truncate_text("#{}".format(await self._find_server_rank(user, server)), 8)
        self._write_unicode(s_rank_txt, num_local_align - general_info_u_fnt.getsize(local_symbol)[0], 165, general_info_fnt, general_info_u_fnt, light_color, draw) # Rank 

        s_exp_txt = self._truncate_text("{}".format(self.users[user.id]["current_xp"]), 8)
        self._write_unicode(s_exp_txt, num_local_align, 180, general_info_fnt, general_info_u_fnt, light_color, draw)  # Exp
        try:
            credits = self._get_solde(user)
        except:
            credits = 0
        credit_txt = "{}".format(credits)
        draw.text((num_local_align, 195), self._truncate_text(credit_txt, 18),  font=general_info_fnt, fill=light_color) # Credits

        # global stats
        num_align = 230
        if "linux" in platform.system().lower():
            global_symbol = u"\U0001F30E "
            fine_adjust = 1
        else:
            global_symbol = "G "
            fine_adjust = 0

        rank_txt = global_symbol + self._truncate_text("#{}".format(await self._find_global_rank(user, server)), 8)
        exp_txt = self._truncate_text("{}".format(userinfo["global_xp"]), 8)
        self._write_unicode(rank_txt, num_align - general_info_u_fnt.getsize(global_symbol)[0] + fine_adjust, 165, general_info_fnt, general_info_u_fnt, light_color, draw) # Rank 
        self._write_unicode(exp_txt, num_align, 180, general_info_fnt, general_info_u_fnt, light_color, draw)  # Exp

        draw.text((105, 220), "Informations",  font=sub_header_fnt, fill=white_color) # Info Box 
        margin = 105
        offset = 238
        for line in textwrap.wrap(userinfo["info"], width=40):
            # draw.text((margin, offset), line, font=text_fnt, fill=(70,70,70,255))
            self._write_unicode(line, margin, offset, text_fnt, text_u_fnt, light_color, draw)            
            offset += text_fnt.getsize(line)[1] + 2

        # sort badges
        priority_badges = []
        for badge in userinfo["badges"]:
            priority_num = self.badges[badge]["priority_num"]
            priority_badges.append((badge, priority_num))
        sorted_badges = sorted(priority_badges, key=lambda us: us[1], reverse=True)

        # TODO: simplify this. it shouldn't be this complicated... sacrifice conciseness for customizability
        if self.settings["badge_type"] == "circles":
            # circles require antialiasing
            vert_pos = 187
            right_shift = 6
            left = 10 + right_shift
            right = 52 + right_shift
            coord = [(left, vert_pos), (right, vert_pos), (left, vert_pos + 33), (right, vert_pos + 33), (left, vert_pos + 66), (right, vert_pos + 66)]
            i = 0
            total_gap = 2 # /2
            border_width = int(total_gap/2)

            for pair in sorted_badges[:6]:
                badge = pair[0]
                bg_color = self.badges[badge]["bg_color"]
                text_color = self.badges[badge]["text_color"]
                border_color = self.badges[badge]["border_color"]
                text = badge.replace("_", " ")
                size = 32
                multiplier = 6 # for antialiasing
                raw_length = size * multiplier

                # draw mask circle
                mask = Image.new('L', (raw_length, raw_length), 0)
                draw_thumb = ImageDraw.Draw(mask)
                draw_thumb.ellipse((0, 0) + (raw_length, raw_length), fill = 255, outline = 0)

                # determine image or color for badge bg
                if await self._valid_image_url(bg_color):
                    # get image
                    async with aiohttp.get(bg_color) as r:
                        image = await r.content.read()
                    with open(GENPATH+'/temp_badge{}.png'.format(user.id),'wb') as f:
                        f.write(image)
                    badge_image = Image.open(GENPATH+'/temp_badge{}.png'.format(user.id)).convert('RGBA')
                    badge_image = badge_image.resize((raw_length, raw_length), Image.ANTIALIAS)

                    # structured like this because if border = 0, still leaves outline.
                    if border_color:
                        square = Image.new('RGBA', (raw_length, raw_length), border_color)
                        # put border on ellipse/circle
                        output = ImageOps.fit(square, (raw_length, raw_length), centering=(0.5, 0.5))
                        output = output.resize((size, size), Image.ANTIALIAS)
                        outer_mask = mask.resize((size, size), Image.ANTIALIAS)
                        process.paste(output, coord[i], outer_mask)

                        # put on ellipse/circle
                        output = ImageOps.fit(badge_image, (raw_length, raw_length), centering=(0.5, 0.5))
                        output = output.resize((size - total_gap, size - total_gap), Image.ANTIALIAS)
                        inner_mask = mask.resize((size - total_gap, size - total_gap), Image.ANTIALIAS)
                        process.paste(output, (coord[i][0] + border_width, coord[i][1] + border_width), inner_mask)
                    else:
                        # put on ellipse/circle
                        output = ImageOps.fit(badge_image, (raw_length, raw_length), centering=(0.5, 0.5))
                        output = output.resize((size, size), Image.ANTIALIAS)
                        outer_mask = mask.resize((size, size), Image.ANTIALIAS)
                        process.paste(output, coord[i], outer_mask)
                    os.remove(GENPATH+'/temp_badge{}.png'.format(user.id))
                else: # if it's just a color
                    if border_color:
                        # border
                        square = Image.new('RGBA', (raw_length, raw_length), border_color)
                        output = ImageOps.fit(square, (raw_length, raw_length), centering=(0.5, 0.5))
                        output = output.resize((size, size), Image.ANTIALIAS)
                        outer_mask = mask.resize((size, size), Image.ANTIALIAS)
                        process.paste(output, coord[i], outer_mask)

                        # put on ellipse/circle
                        square = Image.new('RGBA', (raw_length, raw_length), bg_color)
                        output = ImageOps.fit(square, (raw_length, raw_length), centering=(0.5, 0.5))
                        output = output.resize((size - total_gap, size - total_gap), Image.ANTIALIAS)
                        inner_mask = mask.resize((size - total_gap, size - total_gap), Image.ANTIALIAS)
                        process.paste(output, (coord[i][0] + border_width, coord[i][1] + border_width), inner_mask)
                        draw.text((self._center(coord[i][0], coord[i][0] + size, badge[:6], badge_fnt), coord[i][1] + 12), badge[:6],  font=badge_fnt, fill=text_color) # Text
                    else:
                        square = Image.new('RGBA', (raw_length, raw_length), bg_color)
                        output = ImageOps.fit(square, (raw_length, raw_length), centering=(0.5, 0.5))
                        output = output.resize((size, size), Image.ANTIALIAS)
                        outer_mask = mask.resize((size, size), Image.ANTIALIAS)
                        process.paste(output, coord[i], outer_mask)
                        draw.text((self._center(coord[i][0], coord[i][0] + size, badge[:6], badge_fnt), coord[i][1] + 12), badge[:6],  font=badge_fnt, fill=text_color) # Text
                i += 1
        elif self.settings["badge_type"] == "squares":
            # squares, cause eslyium.
            vert_pos = 188
            right_shift = 6
            left = 10 + right_shift
            right = 52 + right_shift
            coord = [(left, vert_pos), (right, vert_pos), (left, vert_pos + 33), (right, vert_pos + 33), (left, vert_pos + 66), (right, vert_pos + 66)]
            total_gap = 4
            border_width = int(total_gap/2)
            i = 0
            for pair in sorted_badges[:6]:
                badge = pair[0]
                bg_color = self.badges[badge]["bg_color"]
                text_color = self.badges[badge]["text_color"]
                border_color = self.badges[badge]["border_color"]
                text = badge.replace("_", " ")
                size = 32

                # determine image or color for badge bg, this is also pretty terrible tbh...
                if await self._valid_image_url(bg_color):
                    # get image
                    async with aiohttp.get(bg_color) as r:
                        image = await r.content.read()
                    with open(GENPATH+'/temp_badge{}.png'.format(user.id),'wb') as f:
                        f.write(image)

                    badge_image = Image.open(GENPATH+'/temp_badge{}.png'.format(user.id)).convert('RGBA')
                    if border_color != None:
                        draw.rectangle([coord[i], (coord[i][0] + size, coord[i][1] + size)], fill=border_color) # border
                        badge_image = badge_image.resize((size - total_gap + 1, size - total_gap + 1), Image.ANTIALIAS)
                        process.paste(badge_image, (coord[i][0] + border_width, coord[i][1] + border_width))
                    else:
                        badge_image = badge_image.resize((size, size), Image.ANTIALIAS)
                        process.paste(badge_image, coord[i])
                    os.remove(GENPATH+'/temp_badge{}.png'.format(user.id))
                else:
                    if border_color != None:
                        draw.rectangle([coord[i], (coord[i][0] + size, coord[i][1] + size)], fill=border_color) # border
                        draw.rectangle([(coord[i][0] + border_width, coord[i][1] + border_width), (coord[i][0] + size - border_width, coord[i][1] + size - border_width)], fill=bg_color) # bg               
                    else:
                        draw.rectangle([coord[i], (coord[i][0] + size, coord[i][1] + size)], fill = bg_color)
                    draw.text((self._center(coord[i][0], coord[i][0] + size, badge[:6], badge_fnt), coord[i][1] + 12), badge[:6],  font=badge_fnt, fill=text_color) # Text            
                i+=1
        elif self.settings["badge_type"] == "tags" or self.settings["badge_type"] == "bars":
            vert_pos = 190
            i = 0
            for pair in sorted_badges[:5]:
                badge = pair[0]
                bg_color = self.badges[badge]["bg_color"]
                text_color = self.badges[badge]["text_color"]
                border_color = self.badges[badge]["border_color"]
                left_pos = 10
                right_pos = 95
                text = badge.replace("_", " ")
                total_gap = 4
                border_width = int(total_gap/2)
                bar_size = (85, 15)

                # determine image or color for badge bg
                if await self._valid_image_url(bg_color):
                    async with aiohttp.get(bg_color) as r:
                        image = await r.content.read()
                    with open(GENPATH+'/temp_badge{}.png'.format(user.id),'wb') as f:
                        f.write(image)
                    badge_image = Image.open(GENPATH+'/temp_badge{}.png'.format(user.id)).convert('RGBA')

                    if border_color != None:
                        draw.rectangle([(left_pos, vert_pos + i*17), (right_pos, vert_pos + 15 + i*17)], fill = border_color, outline = border_color) # border
                        badge_image = badge_image.resize((bar_size[0] - total_gap + 1, bar_size[1] - total_gap + 1), Image.ANTIALIAS)
                        process.paste(badge_image, (left_pos + border_width, vert_pos + border_width + i*17))
                    else:
                        badge_image = badge_image.resize(bar_size, Image.ANTIALIAS)
                        process.paste(badge_image, (left_pos,vert_pos + i*17))                    
                    os.remove(GENPATH+'/temp_badge{}.png'.format(user.id))
                else:
                    if border_color != None:
                        draw.rectangle([(left_pos, vert_pos + i*17), (right_pos, vert_pos + 15 + i*17)], fill = border_color, outline = border_color) # border
                        draw.rectangle([(left_pos + border_width, vert_pos + border_width + i*17), (right_pos - border_width, vert_pos - border_width + 15 + i*17)], fill = bg_color) # bg                       
                    else:
                        draw.rectangle([(left_pos,vert_pos + i*17), (right_pos, vert_pos + 15 + i*17)], fill = bg_color, outline = border_color) # bg
                    bar_fnt = ImageFont.truetype(font_bold_file, 14) # a slightly bigger font was requested
                    draw.text((self._center(left_pos,right_pos, text, bar_fnt), vert_pos + 2 + i*17), text,  font=bar_fnt, fill = text_color) # Credits
                vert_pos += 2 # spacing
                i += 1

        result = Image.alpha_composite(result, process)
        result.save(GENPATH+'/profile{}.png'.format(user.id),'PNG', quality=100)

    # uses k-means algorithm to find color from bg, rank is abundance of color, descending
    async def _auto_color(self, url:str, ranks):
        phrases = ["Calculating colors..."] # in case I want more
        try:
            await self.bot.say("**{}**".format(random.choice(phrases)))   
            clusters = 10

            async with aiohttp.get(url) as r:
                image = await r.content.read()
            with open(GENPATH+'/temp_auto.png','wb') as f:
                f.write(image)

            im = Image.open(GENPATH+'/temp_auto.png').convert('RGBA')            
            im = im.resize((290, 290)) # resized to reduce time
            ar = scipy.misc.fromimage(im)
            shape = ar.shape
            ar = ar.reshape(scipy.product(shape[:2]), shape[2])

            codes, dist = scipy.cluster.vq.kmeans(ar.astype(float), clusters)
            vecs, dist = scipy.cluster.vq.vq(ar, codes)         # assign codes
            counts, bins = scipy.histogram(vecs, len(codes))    # count occurrences

            # sort counts
            freq_index = []
            index = 0
            for count in counts:
                freq_index.append((index, count))
                index += 1
            sorted_list = sorted(freq_index, key=lambda us: us[1], reverse=True)

            colors = []
            for rank in ranks:
                color_index = min(rank, len(codes))
                peak = codes[sorted_list[color_index][0]] # gets the original index
                peak = peak.astype(int)

                colors.append(''.join(format(c, '02x') for c in peak))
            return colors # returns array
        except:
            await self.bot.say("```Error or no scipy. \n"
                "Install scipy doing 'pip3 install numpy' and 'pip3 install scipy' \n"
                "or read here: https://github.com/AznStevy/Maybe-Useful-Cogs/blob/master/README.md```")           

    # returns new text color based on the bg. doesn't work great.
    def _contrast(self, bg_color, text_color):
        min_diff = .75 # percent difference
        dr = (bg_color[0] - text_color[0])
        dg = (bg_color[1] - text_color[1])
        db = (bg_color[2] - text_color[2])

        if bg_color[0] != 0:
            dr /= bg_color[0]
        if bg_color[1] != 0:
            dr /= bg_color[1]
        if bg_color[2] != 0:
            dr /= bg_color[2]

        if abs(dr) > min_diff or abs(dg) > min_diff or abs(dg) > min_diff:
            return text_color
        else:
            new_color = []
            if dr > 0 or dg > 0 or db > 0:
                for val in bg_color:
                    new_color.append(int(val*min_diff))
                return tuple(new_color)
            else:
                for val in bg_color:
                    val = val*(1+min_diff)
                    if val > 255:
                        val = 255
                    new_color.append(int(val))
                return tuple(new_color)

    # dampens the color given a parameter
    def _moderate_color(self, rgb, a, moderate_num):
        new_colors = []
        for color in rgb[:3]:
            if color > 128:
                color -= moderate_num
            else:
                color += moderate_num
            new_colors.append(color)
        new_colors.append(230)

        return tuple(new_colors)

    def _rgb_to_hex(self, rgb):
        rgb = tuple(rgb[:3])
        return '#%02x%02x%02x' % rgb

    def _is_hex(self, color:str):
        if color != None and len(color) != 4 and len(color) != 7:
            return False

        reg_ex = r'^#(?:[0-9a-fA-F]{3}){1,2}$'
        return re.search(reg_ex, str(color))

    def _luminance(self, color):
        luminance = (0.2126*color[0]) + (0.7152*color[1]) + (0.0722*color[2])
        return luminance

    # converts hex to rgb
    def _hex_to_rgb(self, hex_num: str, a:int):
        h = hex_num.lstrip('#')

        # if only 3 characters are given
        if len(str(h)) == 3:
            expand = ''.join([x*2 for x in str(h)])
            h = expand

        colors = [int(h[i:i+2], 16) for i in (0, 2 ,4)]
        colors.append(a)
        return tuple(colors)

    def _get_solde(self, user):  
        # print("\n ------------- \n")
        # pprint.pprint(self.bot.get_cog('Banque').bank.__dict__)
        # print("\n ------------- \n")
        bank = self.bot.get_cog('Banque').bank
        if bank.account_exists(user):
            credits = bank.get_balance(user)
        else:
            credits = 0
        return credits

    # returns a string with possibly a nickname
    def _name(self, user, max_length):
        if user.name == user.display_name:
            return user.name
        else:
            return "{} ({})".format(user.name, self._truncate_text(user.display_name, max_length - len(user.name) - 3), max_length)

    def _truncate_text(self, text, max_length):
        if len(text) > max_length:
            if text.strip('$').isdigit():
                text = int(text.strip('$'))
                return "${:.2E}".format(text)
            return text[:max_length-3] + "..."
        return text

    def _write_unicode(self, text, init_x, y, font, unicode_font, fill, draw):
            write_pos = init_x

            for char in text:
                if char.isalnum() or char in string.punctuation or char in string.whitespace:
                    draw.text((write_pos, y), char, font=font, fill=fill)
                    write_pos += font.getsize(char)[0] 
                else:
                    draw.text((write_pos, y), u"{}".format(char), font=unicode_font, fill=fill)
                    write_pos += unicode_font.getsize(char)[0]

    def _save_settings_bgs(self, ctx):
        try:
            serveur = ctx.message.server
        except:
            serveur = ctx.user.server

        self.servers[serveur.id] = {
                "nom": serveur.name,
                "settings" : self.settings,
                "bgs" : self.backgrounds  
            } 
        fileIO(SERVERS, "save", self.servers)

    # finds the pixel to center the text
    def _center(self, start, end, text, font):
        dist = end - start
        width = font.getsize(text)[0]
        start_pos = start + ((dist-width)/2)
        return int(start_pos)

    # doit on mentionner l'utilisateur ?
    def _is_mention(self, user):
        if self.settings["mention"]:
            return user.mention
        else:
            return user.name

    def _get_next_level(self, current_level):
        base_interval = int(self.settings["int_rank"])
        return (base_interval/20)*(current_level**2)+(base_interval/2)*current_level+base_interval 

    def _get_random_xp(self):
        minxp = int(self.settings["min_xp"])
        maxxp = int(self.settings["max_xp"])
        return random.randint(minxp, maxxp) 

    def _clear_folder(self):
        maxsize = 25000000 # 25mb max
        size = sum(os.path.getsize(GENPATH) for GENPATH in os.listdir('.') if os.path.isfile(GENPATH))
        if size > maxsize:
            fileList = os.listdir(GENPATH)
            for fileName in fileList:
                os.remove(GENPATH+"/"+fileName)

    def __init__(self, bot):
        self.threads = []
        self.bot = bot
        bot_settings = fileIO("data/red/settings.json", "load")
        self.owner = bot_settings["OWNER"]
        self.servers = fileIO(SERVERS, "load")
        self.badges = fileIO(BADGES, "load")
        default_settings = fileIO(DEFAULT_SETTINGS, "load")
        self.settings = default_settings["general"]
        self.backgrounds = default_settings["bgs"]
        self.users = fileIO(USERS, "load")
        self.block = fileIO(BLOCK, "load")
        locale.setlocale( locale.LC_ALL, '' )