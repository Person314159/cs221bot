import subprocess

from discord.ext import commands

SERVER_LIST = ("thetis", "remote", "annacis", "bowen", "lulu", "gambier", "anvil")
OTHER_SERVER_NAMES = ("valdes",)


class ServerStats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="checkservers")
    @commands.cooldown(1, 60)
    async def check_servers(self, ctx: commands.Context, *args: str):
        """
        `!checkservers` __`Check if the remote CS servers are online`__

        **Usage** `!checkservers [server names]`

        **Valid server names**
        thetis, remote, annacis, bowen, lulu, valdes, gambier, anvil

        **Examples:**
        `!checkservers` checks all server statuses
        `!checkservers thetis` checks status of thetis server
        `!checkservers thetis remote` checks status of thetis and remote servers
        """

        async def check_server(server_ip: str) -> str:
            """
            Checks if the server with given IP can be connected to with SSH.

            Parameters
            ----------
            server_ip: `str`
                The IP of the server to check

            Returns
            -------
            `str`
                "online" if we can connect to the server using SSH; "offline" otherwise
            """

            can_connect = await can_connect_ssh(server_ip)
            return "online" if can_connect else "offline"

        msgs = []

        if not args:
            for server_name in SERVER_LIST:
                ip = f"{server_name}.students.cs.ubc.ca"
                msgs.append(f"{server_name} is {await check_server(ip)}")
        else:
            for server_name in set(map(lambda arg: arg.lower(), args)):
                ip = f"{server_name}.students.cs.ubc.ca"

                if server_name in SERVER_LIST or server_name in OTHER_SERVER_NAMES:
                    msgs.append(f"{server_name} is {await check_server(ip)}")
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
        output = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "PubkeyAuthentication=no", "-o",
                                 "PasswordAuthentication=no", "-o", "KbdInteractiveAuthentication=no",
                                 "-o", "ChallengeResponseAuthentication=no", server_ip,
                                 "2>&1"], capture_output=True, timeout=5).stderr.decode("utf-8")

        return "Permission denied" in output or "verification failed" in output
    except subprocess.TimeoutExpired:
        return False


def setup(bot: commands.Bot) -> None:
    bot.add_cog(ServerStats(bot))
