import discord.ext.commands as commands
from .utils import cases
from __main__ import send_cmd_help, settings


def setup(bot):
    bot.add_cog(Foo(bot))


class Foo:
    def __init__(self, bot):
        self.bot = bot
        self.cases = cases.Cases(self.bot)

    @commands.group(name='foo', invoke_without_command=True, pass_context=True)
    async def foo_group(self, ctx):
        #server = ctx.message.server

        await self.bot.say('foo')
        #await self.bot.say("type:{}\nsettings: {}".format(type(self.cases.owner_settings), self.cases.owner_settings))
        #Actions = self.cases.set_cases(server)
        #await self.bot.say(type(Actions))
        self.unStackSMS()



    @commands.command(pass_context=True, no_pm=True, name='cases')
    async def setCases(self, ctx, action: str = None, enabled: bool = None):
        """Active ou desactive la création de case

        Enabled peut être 'on' ou 'off'"""
        if action is None:
            await send_cmd_help(ctx)
        server = ctx.message.server
        self.cases.set_cases(server, action, enabled)
        await self.cases.unStackSMS(server)

    @commands.command(pass_context=True, no_pm=True, name='testcases')
    async def testCases(self, ctx):
        """Test la création de cases"""
        server  = ctx.message.server
        author  = ctx.message.author
        user    = ctx.message.author
        reason  = "ceci est un test"
        await self.cases.update_case(server, case = 92)
        # await self.cases.new_case(server    = ctx.message.server,
        #                           action    = "SOFTBAN",
        #                           mod       = author,
        #                           user      = user,
        #                           reason    = reason)

    @foo_group.group(name='bar', invoke_without_command=True,  pass_context=True)
    async def foo_bar_group(self, ctx, some_arg):
        await self.bot.say('foo bar with arg {}'.format(some_arg))

    @foo_bar_group.command(name='baz')
    async def foo_bar_baz(self):
        await self.bot.say('foo bar baz')

