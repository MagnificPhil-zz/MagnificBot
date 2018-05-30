from discord.ext import commands
import discord.utils
from __main__ import settings

#
# Ceci est une version modifiée de checks.py, à l'origine faite par Rapptz
#
#                 https://github.com/Rapptz
#          https://github.com/Rapptz/RoboDanny/tree/async
#

def is_owner_check(ctx):
    _id = ctx.message.author.id
    return _id == settings.owner or _id in ctx.bot.settings.co_owners

def is_owner():
    return commands.check(is_owner_check)


# Le système d'autorisation du bot est basé sur une base "juste fonctionne"
# Vous avez des permissions et le bot a des permissions. Si vous répondez aux autorisations
# nécessaires pour exécuter la commande (et le bot aussi), alors cela passe
# et vous pouvez exécuter la commande.
# Si ces vérifications échouent, il y a deux solutions de repli.
# Un rôle avec le nom de Bot Mod et un rôle avec le nom de Bot Admin.
# Avoir ces rôles vous donne accès à certaines commandes sans avoir réellement
# les autorisations requises pour elles.
# Bien sûr, le propriétaire sera toujours capable d'exécuter les commandes.

def check_permissions(ctx, perms):
    if is_owner_check(ctx):
        return True
    elif not perms:
        return False

    ch = ctx.message.channel
    author = ctx.message.author
    resolved = ch.permissions_for(author)
    return all(getattr(resolved, name, None) == value for name, value in perms.items())

def role_or_permissions(ctx, check, **perms):
    if check_permissions(ctx, perms):
        return True

    ch = ctx.message.channel
    author = ctx.message.author
    if ch.is_private:
        return False # ne peut pas avoir de rôles en MP
    role = discord.utils.find(check, author.roles)

    return role is not None


def sel_or_permissions(**perms):
    def predicate(ctx):
        server = ctx.message.server
        sel_role = settings.get_server_sel(server).lower()
        mod_role = settings.get_server_mod(server).lower()
        admin_role = settings.get_server_admin(server).lower()
        cocap_role = settings.get_server_cocap(server).lower()
        return role_or_permissions(ctx, lambda r: r.name.lower() in (sel_role, mod_role, admin_role, cocap_role), **perms)

    return commands.check(predicate)

def mod_or_permissions(**perms):
    def predicate(ctx):
        server = ctx.message.server
        mod_role = settings.get_server_mod(server).lower()
        admin_role = settings.get_server_admin(server).lower()
        cocap_role = settings.get_server_cocap(server).lower()
        return role_or_permissions(ctx, lambda r: r.name.lower() in (mod_role, admin_role, cocap_role), **perms)

    return commands.check(predicate)

def admin_or_permissions(**perms):
    def predicate(ctx):
        server = ctx.message.server
        admin_role = settings.get_server_admin(server).lower()
        cocap_role = settings.get_server_cocap(server).lower()
        return role_or_permissions(ctx, lambda r: r.name.lower() in (admin_role, cocap_role), **perms)

    return commands.check(predicate)


def cocap_or_permissions(**perms):
    def predicate(ctx):
        server = ctx.message.server
        cocap_role = settings.get_server_cocap(server)
        return role_or_permissions(ctx, lambda r: r.name.lower() == cocap_role.lower(), **perms)

    return commands.check(predicate)

def serverowner_or_permissions(**perms):
    def predicate(ctx):
        if ctx.message.server is None:
            return False
        server = ctx.message.server
        owner = server.owner

        if ctx.message.author.id == owner.id:
            return True

        return check_permissions(ctx,perms)
    return commands.check(predicate)

def serverowner():
    return serverowner_or_permissions()

def cocap():
    return cocap_or_permissions()

def admin():
    return admin_or_permissions()

def mod():
    return mod_or_permissions()

def sel():
    return sel_or_permissions()
