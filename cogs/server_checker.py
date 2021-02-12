import asyncio
import json
from os.path import isfile
import subprocess
from typing import Dict, Optional

import discord
from discord.ext import commands

from util import create_file


SERVER_LIST = ("thetis", "valdes", "remote", "annacis", "anvil", "bowen", "lulu")
SERVER_TRACKERS_FILE = "data/server_trackers.json"


class ServerChecker(commands.Cog, name="server_checker"):
    def __init__(self, bot):
        def hook(dct):
            return {int(key): dct[key] for key in dct}

        self.bot = bot

        if not isfile(SERVER_TRACKERS_FILE):
            create_file.create_file_if_not_exists(SERVER_TRACKERS_FILE)
            self.bot.writeJSON({}, SERVER_TRACKERS_FILE)

        with open(SERVER_TRACKERS_FILE, "r") as f:
            # Maps channel ID to live message ID
            # All keys in the JSON are ints stored as strings. The hook function turns those keys into ints.
            self.server_trackers_dict: Dict[int, Optional[int]] = json.load(f, object_hook=hook)

    @commands.command(name="checkservers")
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def check_servers(self, ctx, *args):
        """
        `!checkservers` __`Check if the remote CS servers are online`__

        **Usage** `!checkservers [server names]`

        **Valid server names**
        thetis, remote, annacis, anvil, bowen, lulu, valdes

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

                if server_name in SERVER_LIST:
                    msgs.append(f"{server_name} is {await check_server(ip)}")
                else:
                    msgs.append(f"{server_name} is not a valid server name.")

        await ctx.send("\n".join(msgs))

    @commands.command(name="trackservers")
    @commands.is_owner()
    async def track_servers(self, ctx):
        """
        `!trackservers` __`Get CS server status updates live`__

        Causes the bot to periodically check the statuses of the remote CS servers,
        updating a live status message in the channel where this command is invoked.
        """

        if ctx.channel.id not in self.server_trackers_dict:
            self.server_trackers_dict[ctx.channel.id] = None
            self.bot.writeJSON(self.server_trackers_dict, SERVER_TRACKERS_FILE)
            await ctx.send("This channel will now receive live CS server status updates.",
                           delete_after=5)
        else:
            await ctx.send("This channel is already receiving live CS server status updates.",
                           delete_after=5)

    @commands.command(name="untrackservers")
    @commands.is_owner()
    async def untrack_servers(self, ctx):
        """
        `!untrackservers`

        Causes the bot to stop sending CS server updates to the channel where
        this command is invoked.
        """

        if ctx.channel.id in self.server_trackers_dict:
            live_msg_id = self.server_trackers_dict.pop(ctx.channel.id, None)
            self.bot.writeJSON(self.server_trackers_dict, SERVER_TRACKERS_FILE)

            if live_msg_id is not None:
                live_msg = ctx.channel.get_partial_message(live_msg_id)

                try:
                    await live_msg.delete()
                except discord.NotFound:
                    # The message was already deleted
                    pass

            await ctx.send("This channel will no longer receive live CS server status updates.",
                           delete_after=5)
        else:
            await ctx.send("This channel is not receiving live CS server status updates.",
                           delete_after=5)

    async def check_servers_periodically(self):
        """
        Periodically checks the statuses of the remote CS servers and sends status updates
        to all channels tracking the servers.
        """

        await self.bot.wait_until_ready()

        while True:
            await self.update_server_statuses()
            await asyncio.sleep(30)

    @staticmethod
    async def get_server_statuses() -> str:
        """
        Returns a Discord message that indicates the statuses of the remote CS servers.
        """

        msg_components = ["Server Statuses:"]

        for server_name in SERVER_LIST:
            ip = f"{server_name}.students.cs.ubc.ca"
            can_connect = await can_connect_ssh(ip)

            if can_connect:
                msg_components.append(f":white_check_mark: {ip}")
            else:
                msg_components.append(f":x: {ip}")

        return "\n".join(msg_components)

    async def update_server_statuses(self):
        """
        Gets the statuses of the CS servers and updates a live status message in each channel
        that is tracking the servers. We will call these channels "tracking channels".

        If there is no live status message in a tracking channel, the bot sends one. Otherwise,
        the bot simply edits the existing status message.

        If a tracking channel has been deleted, the bot will no longer attempt to send status
        updates to that channel.
        """

        message = await self.get_server_statuses()
        deleted_channel_ids = []

        for channel_id, msg_id in self.server_trackers_dict.items():
            channel = self.bot.get_channel(channel_id)

            if channel is not None:
                if msg_id is not None:
                    live_msg = channel.get_partial_message(msg_id)

                    try:
                        await live_msg.edit(content=message)
                    except discord.NotFound:
                        live_msg = await channel.send(message)
                        self.server_trackers_dict[channel_id] = live_msg.id
                else:
                    live_msg = await channel.send(message)
                    self.server_trackers_dict[channel_id] = live_msg.id
            else:
                deleted_channel_ids.append(channel_id)

        if deleted_channel_ids:
            for channel_id in deleted_channel_ids:
                del self.server_trackers_dict[channel_id]

        self.bot.writeJSON(self.server_trackers_dict, SERVER_TRACKERS_FILE)


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


def setup(bot):
    bot.add_cog(ServerChecker(bot))
