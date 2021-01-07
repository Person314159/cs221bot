import random
from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands import ExtensionError

from util.badargs import BadArgs


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

        if not arg:
            embed = discord.Embed(title="CS221 Bot", description="Commands:", colour=random.randint(0, 0xFFFFFF), timestamp=datetime.utcnow())
            embed.add_field(name=f"❗ Current Prefix: `{self.bot.command_prefix}`", value="\u200b", inline=False)

            for k, v in self.bot.cogs.items():
                embed.add_field(name=k, value=" ".join(f"`{i}`" for i in v.get_commands() if not i.hidden), inline=False)

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
            modules = list(i.lower() for i in self.bot.cogs)

        for extension in modules:
            Reload = await ctx.send(f"Reloading the {extension} module")

            try:
                self.bot.reload_extension(f"cogs.{extension}")
            except ExtensionError as exc:
                return await ctx.send(exc)

            await Reload.edit(content=f"{extension} module reloaded.")

        self.bot.reload_extension("cogs.meta")

        await ctx.send("Done")


def setup(bot):
    bot.add_cog(Meta(bot))
