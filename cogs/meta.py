import random
from datetime import datetime

import discord
from discord import ExtensionError
from discord.ext import commands

from util.badargs import BadArgs


class Meta(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.is_owner()
    async def die(self, ctx: commands.Context):
        await self.bot.logout()

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def help(self, ctx: commands.Context, *arg: str):
        """
        `!help` __`Returns list of commands or usage of command`__

        **Usage:** !help [optional cmd]

        **Examples:**
        `!help` [embed]
        """

        if not arg:
            embed = discord.Embed(title="CS221 Bot", description="Commands:", colour=random.randint(0, 0xFFFFFF), timestamp=datetime.utcnow())
            embed.add_field(name=f"❗ Current Prefix: `{self.bot.command_prefix}`", value="\u200b", inline=False)

            for k, v in sorted(self.bot.cogs.items(), key=lambda kv: kv[0]):
                embed.add_field(name=k, value=" ".join(f"`{i}`" for i in v.get_commands() if not i.hidden), inline=False)

            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=str(ctx.author.display_avatar.url))
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
    async def reload(self, ctx: commands.Context, *modules: str):
        if not isinstance(ctx.channel, discord.DMChannel):
            await ctx.message.delete()

        if not modules:
            modules = list(i.lower() for i in self.bot.cogs)

        for extension in modules:
            reload_msg = await ctx.send(f"Reloading the {extension} module")

            try:
                self.bot.reload_extension(f"cogs.{extension}")
            except ExtensionError as exc:
                return await ctx.send(str(exc))

            await reload_msg.edit(content=f"{extension} module reloaded.")

        await ctx.send("Done")


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Meta(bot))
