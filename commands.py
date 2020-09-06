import datetime
import mimetypes
import random
from io import BytesIO

import discord
import requests
from discord.ext import commands

#################### COMMANDS ####################

class Main(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # example command
    @commands.command(hidden = True)
                    # number of calls   per this many seconds  by either user, channel, server or something else
    @commands.cooldown(      1,                     5,                    commands.BucketType.user)
    async def example(self, ctx, *args):
        await ctx.send("Hello World!")
        # args is a list of arguments
        # things put between quotes will be treated as one argument
        # so '?example "one two" three' will have ["one two", "three"] as arguments
        if not args:
            # do some stuff when no argument supplied (i.e. called with '?example')
            return
        else:
            # arguments supplied
            # do things with them
            return

    @commands.command(hidden = True)
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

        if not arg:
            embed = discord.Embed(title = "CS221 Bot", description = "Commands:", colour = random.randint(0, 0xFFFFFF), timestamp = datetime.datetime.utcnow())
            embed.add_field(name = f"❗ Current Prefix: `{self.bot.command_prefix}`", value = "\u200b", inline = False)
            embed.add_field(name = "Commands", value = " ".join(f"`{i}`" for i in main.get_commands() if not i.hidden), inline = False)
            embed.set_thumbnail(url = self.bot.user.avatar_url)
            embed.set_footer(text = f"Requested by {ctx.author.display_name}", icon_url = str(ctx.author.avatar_url))
            await ctx.send(embed = embed)
        else:
            help_command = arg[0]

            comm = self.bot.get_command(help_command)

            if not comm or not comm.help or comm.hidden:
                return await ctx.send("That command doesn't exist.", delete_after = 5)

            await ctx.send(comm.help)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def join(self, ctx, *arg):
        """
        `!join` __`Adds a role to yourself`__

        **Usage:** !join [role name]

        **Examples:**
        `!join L1A` adds the L1A role to yourself
        """

        # case where role name is space separated
        name = " ".join(arg).lower()
        # make sure that you can't add roles like "prof" or "ta"
        invalid_roles = ["Prof", "TA", "Fake TA", "CS221 bot"]
        aliases = {"he": 747925204864335935, "she": 747925268181811211, "ze": 747925349232279552, "they": 747925313748729976}

        for role in ctx.guild.roles:
            if name == role.name.lower() and role.name not in invalid_roles:
                if name.startswith("l1") and any(role.name.startswith("L1") for role in ctx.author.roles):
                    return await ctx.send("you already have a lab role!", delete_after = 5)
                elif role in ctx.author.roles:
                    return await ctx.send("you already have that role!", delete_after = 5)
                else:
                    await ctx.author.add_roles(role)
                    return await ctx.send("role added!", delete_after = 5)
            elif name in aliases:
                await ctx.author.add_roles(ctx.guild.get_role(aliases[name]))
                return await ctx.send("role added!", delete_after = 5)
        else:
            await ctx.send("you can't add that role!", delete_after = 5)
            return await ctx.send(ctx.command.help)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def leave(self, ctx, *arg):
        """
        `!leave` __`Removes an existing role from yourself`__

        **Usage:** !leave [role name]

        **Examples:**
        `!leave L1A` removes the L1A role from yourself
        """

        # case where role name is space separated
        name = " ".join(arg).lower()

        for role in ctx.guild.roles:
            if name == role.name.lower():
                if role in ctx.author.roles:
                    await ctx.author.remove_roles(role)
                    return await ctx.send("role removed!", delete_after = 5)
                else:
                    return await ctx.send("you don't have that role!", delete_after = 5)
        else:
            await ctx.send("that role doesn't exist!", delete_after = 5)
            return await ctx.send(ctx.command.help)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def poll(self, ctx):
        """
        `!poll` __`Poll generator`__

        **Usage:** !poll <question | check | end> | <option> | <option> | [option] | [...]

        **Examples:**
        `!poll poll | yee | nah` generates poll titled "poll" with options "yee" and "nah"
        `!poll check` returns content of last poll
        `!poll end` ends current poll in channel and returns results
        """

        poll_list = ctx.message.content[6:].split(" | ")
        question = poll_list[0]
        options = poll_list[1:]

        id_ = self.bot.poll_dict[str(ctx.channel.id)]

        if question == "check":
            if not id_:
                return await ctx.send("No active poll found.", delete_after = 5)

            try:
                poll_message = await ctx.channel.fetch_message(id_)
            except discord.NotFound:
                return await ctx.send("Looks like someone deleted the poll, or there is no active poll.", delete_after = 5)

            embed = poll_message.embeds[0]
            unformatted_options = [x.strip().split(": ") for x in embed.description.split("\n")]
            options_dict = {}

            for x in unformatted_options:
                options_dict[x[0]] = x[1]

            tally = {x: 0 for x in options_dict.keys()}

            for reaction in poll_message.reactions:
                if reaction.emoji in options_dict.keys():
                    async for reactor in reaction.users():
                        if reactor.id != self.bot.user.id:
                            tally[reaction.emoji] += 1

            output = f"Current results of the poll **\"{embed.title}\"**\nLink: {poll_message.jump_url}\n```"

            for key in tally.keys():
                output += f"{options_dict[key]}: {'▓' * tally[key] if tally[key] == max(tally.values()) else '░' * tally[key]} ({tally[key]} votes, {round(tally[key] / sum(tally.values()) * 100 if sum(tally.values()) else 0, 2)}%)\n\n"

            output += "```"

            files = []
            for url in options_dict.values():
                if mimetypes.guess_type(url)[0] and mimetypes.guess_type(url)[0].startswith("image"):
                    filex = BytesIO(requests.get(url).content)
                    filex.seek(0)
                    files.append(discord.File(filex, filename = url))

            return await ctx.send(output, files = files)
        elif question == "end":
            self.bot.poll_dict[str(ctx.channel.id)] = ""
            self.bot.writeJSON(self.bot.poll_dict, "poll.json")

            try:
                poll_message = await ctx.channel.fetch_message(id_)
            except discord.NotFound:
                return await ctx.send("Looks like someone deleted the poll, or there is no active poll.", delete_after = 5)

            embed = poll_message.embeds[0]
            unformatted_options = [x.strip().split(": ") for x in embed.description.split("\n")]
            options_dict = {}

            for x in unformatted_options:
                options_dict[x[0]] = x[1]

            tally = {x: 0 for x in options_dict.keys()}

            for reaction in poll_message.reactions:
                if reaction.emoji in options_dict.keys():
                    async for reactor in reaction.users():
                        if reactor.id != self.bot.user.id:
                            tally[reaction.emoji] += 1

            output = f"Final results of the poll **\"{embed.title}\"**\nLink: {poll_message.jump_url}\n```"

            for key in tally.keys():
                if tally[key]:
                    output += f"{options_dict[key]}: {'▓' * tally[key] if tally[key] == max(tally.values()) else '░' * tally[key]} ({tally[key]} votes, {round(tally[key] / sum(tally.values()) * 100, 2)}%)\n\n"
                else:
                    output += f"{options_dict[key]}: 0\n\n"

            output += "```"
    
            files = []
            for url in options_dict.values():
                if mimetypes.guess_type(url)[0] and mimetypes.guess_type(url)[0].startswith("image"):
                    filex = BytesIO(requests.get(url).content)
                    filex.seek(0)
                    files.append(discord.File(filex, filename = url))

            return await ctx.send(output, files = files)

        if id_:
            return await ctx.send("There's an active poll in this channel already.")

        if len(options) <= 1:
            await ctx.send("Please enter more than one option to poll.", delete_after = 5)
            return await ctx.send(ctx.command.help)
        elif len(options) > 20:
            return await ctx.send("Please limit to 10 options.", delete_after = 5)
        elif len(options) == 2 and options[0] == "yes" and options[1] == "no":
            reactions = ["✅", "❌"]
        else:
            reactions = [chr(127462 + i) for i in range(26)]

        description = []

        for x, option in enumerate(options):
            description += f"\n {reactions[x]}: {option}"

        embed = discord.Embed(title = question, description = "".join(description))
        files = []
        for url in options:
            if mimetypes.guess_type(url)[0] and mimetypes.guess_type(url)[0].startswith("image"):
                filex = BytesIO(requests.get(url).content)
                filex.seek(0)
                files.append(discord.File(filex, filename = url))
        react_message = await ctx.send(embed = embed, files = files)

        for reaction in reactions[:len(options)]:
            await react_message.add_reaction(reaction)

        self.bot.poll_dict[str(ctx.channel.id)] = react_message.id
        self.bot.writeJSON(self.bot.poll_dict, "poll.json")

    @commands.command(hidden = True)
    @commands.is_owner()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def reload(self, ctx, *modules):
        await ctx.message.delete()
        self.bot.reload_extension("commands")
        await ctx.send("Done")

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def votes(self, ctx):
        """
        `!votes` __`Top votes for server icon`__

        **Usage:** !votes

        **Examples:**
        `!votes` returns top 5 icons sorted by score (up - down)
        """

        images = []

        async for message in self.bot.get_channel(745517292892454963).history():
            if message.attachments or message.embeds:
                temp = []
                for reaction in message.reactions:
                    if reaction.emoji == "⬆️":
                        temp.append(reaction.count)
                        temp.append(await reaction.users().flatten())
                    elif reaction.emoji == "⬇️":
                        temp.append(reaction.count)
                        temp.append(await reaction.users().flatten())

                images.append([message.attachments[0].url, (temp[0] - 1 - (message.author in temp[1])) - (temp[2] - 1 - (message.author in temp[3]))])

        images.sort(key = lambda image: image[1], reverse = True)
        images = images[:5]

        for image in images:
            embed = discord.Embed(colour = random.randint(0, 0xFFFFFF))
            embed.add_field(name = "Score", value = image[1], inline = True)
            embed.set_thumbnail(url = image[0])
            await ctx.send(embed = embed)

    # add more commands here with the same syntax
    # also just look up the docs lol i can't do everything

#################### END COMMANDS ####################

def setup(bot):
    bot.add_cog(Main(bot))
