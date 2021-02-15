from discord.ext import commands


class BadArgs(commands.CommandError):
    """
    Exception raised if the arguments to a command are in correct.

    Attributes:
        command -- The command that was run
        show_help -- Whether help should be shown
        msg -- Message to show (or none for no message)
    """

    def __init__(self, msg: str, show_help: bool = False):
        self.help = show_help
        self.msg = msg

    async def print(self, ctx: commands.Context):
        if self.msg:
            await ctx.send(self.msg, delete_after=5)

        if self.help:
            await ctx.send(ctx.command.help)
