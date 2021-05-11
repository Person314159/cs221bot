import discord
from discord.ext import commands


class CustomMemberConverter(commands.IDConverter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Member:
        try:
            return await commands.MemberConverter().convert(ctx, argument)
        except commands.BadArgument:
            for member in ctx.bot.get_guild(ctx.bot.guild_id).members:
                if argument.lower() in member.name.lower() or argument.lower() in member.display_name.lower():
                    return member
            else:
                raise commands.MemberNotFound(argument)
