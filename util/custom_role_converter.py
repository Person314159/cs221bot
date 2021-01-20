from discord.ext import commands


class CustomRoleConverter(commands.IDConverter):
    async def convert(self, ctx, argument):
        for role in ctx.guild.roles:
            if argument.lower() in role.name.lower():
                return role
        else:
            raise commands.RoleNotFound
