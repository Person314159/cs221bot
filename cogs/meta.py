import os
import random
from datetime import datetime
from os.path import isfile, join

import discord
from discord.ext import commands


class BadArgs(Exception):
    """
    Exception raised if the arguments to a command are in correct.

    Attributes:
        command -- The command that was run
        show_help -- Whether help should be shown
        msg -- Message to show (or none for no message)
    """
    def __init__(self, msg, command=None):
        self.command = command
        self.msg = msg

    def print(self, ctx):
        if self.msg:
            await ctx.send(self.msg, delete_after=5)
        if self.command:
            await ctx.send(self.command.help)


class Meta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.is_owner()
    async def die(self, ctx):
        await self.bot.logout()

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def help(self, ctx, *arg):
        """
        `!help` __`Returns list of commands or usage of command`__

        **Usage:** !help [optional cmd]

        **Examples:**
        `!help` [embed]
        """

        main = self.bot.get_cog("Main")
        canvas = self.bot.get_cog("Canvas")
        piazza = self.bot.get_cog("Piazza")
        meta = self.bot.get_cog("Meta")

        if not arg:
            embed = discord.Embed(title="CS221 Bot", description="Commands:", colour=random.randint(0, 0xFFFFFF), timestamp=datetime.utcnow())
            embed.add_field(name=f"❗ Current Prefix: `{self.bot.command_prefix}`", value="\u200b", inline=False)
            embed.add_field(name="Main", value=" ".join(f"`{i}`" for i in main.get_commands() if not i.hidden), inline=False)
            embed.add_field(name="Canvas", value=" ".join(f"`{i}`" for i in canvas.get_commands() if not i.hidden), inline=False)
            embed.add_field(name="Piazza", value=" ".join(f"`{i}`" for i in piazza.get_commands() if not i.hidden), inline=False)
            embed.add_field(name="Meta", value=" ".join(f"`{i}`" for i in meta.get_commands() if not i.hidden), inline=False)
            embed.set_thumbnail(url=self.bot.user.avatar_url)
            embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=str(ctx.author.avatar_url))
            await ctx.send(embed=embed)
        else:
            help_command = arg[0]

            comm = self.bot.get_command(help_command)

            if not comm or not comm.help or comm.hidden:
                raise BadArgs("That command doesn't exist.")

            await ctx.send(comm.help)

    @commands.command(hidden=True)
    @commands.is_owner()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def reload(self, ctx, *modules):
        if not isinstance(ctx.channel, discord.DMChannel):
            await ctx.message.delete()

        if not modules:
            modules = [f[:-3] for f in os.listdir("cogs") if isfile(join("cogs", f))]

        for extension in modules:
            Reload = await ctx.send(f"Reloading the {extension} module")
            try:
                self.bot.reload_extension(f"cogs.{extension}")
            except Exception as exc:
                return await ctx.send(exc)
            await Reload.edit(content=f"{extension} module reloaded.")

        self.bot.reload_extension("cogs.meta")

        await ctx.send("Done")


def setup(bot):
    bot.add_cog(Meta(bot))
