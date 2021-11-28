import subprocess

from discord.ext import commands

SERVER_LIST = ("valdes", "remote", "anvil", "gambier", "pender", "thetis")


class ServerStats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="checkservers")
    @commands.cooldown(1, 600)
    async def check_servers(self, ctx: commands.Context, *args: str):
        """
        `!checkservers` __`Check if the remote CS servers are online`__

        **Usage** `!checkservers [server names]`

        **Valid server names**
        thetis, remote, valdes, anvil, gambier, pender

        **Examples:**
        `!checkservers` checks all server statuses
        `!checkservers thetis` checks status of thetis server
        `!checkservers thetis gambier` checks status of thetis and gambier servers
        """

        msgs = []

        if not args:
            for server_name in SERVER_LIST:
                ip = f"{server_name}.students.cs.ubc.ca"
                status = await can_connect_ssh(ip)
                msgs.append(f"{'✅' if status else '❌'} {server_name} is {'online' if status else 'offline'}")
        else:
            for server_name in set(map(lambda arg: arg.lower(), args)):
                ip = f"{server_name}.students.cs.ubc.ca"
                status = await can_connect_ssh(ip)

                if server_name in SERVER_LIST:
                    msgs.append(f"{'✅' if status else '❌'} {server_name} is {'online' if status else 'offline'}")
                else:
                    msgs.append(f"{server_name} is not a valid server name.")

        await ctx.send("\n".join(msgs))


async def can_connect_ssh(server_ip: str) -> bool:
    """
    Check if we can establish an SSH connection to the server with the given IP.

    Parameters
    ----------
    server_ip: `str`
        The IP of the server

    Returns
    -------
    `bool`
        True if the given IP is valid and if an SSH connection can be established; False otherwise
    """

    try:
        # Command from https://stackoverflow.com/a/47166507
        output = subprocess.run(["ssh", "-o", "BatchMode=yes", server_ip, "2>&1"], capture_output=True, timeout=3)
        return output.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def setup(bot: commands.Bot) -> None:
    bot.add_cog(ServerStats(bot))
