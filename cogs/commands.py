import mimetypes
import random
import re
import string
from datetime import datetime, timedelta, timezone
from io import BytesIO
from os.path import isfile
from urllib import parse

import discord
import pytz
import requests
import requests.models
from discord.ext import commands
from discord.ext.commands import BadArgument, MemberConverter

from util.badargs import BadArgs
from util.create_file import create_file_if_not_exists
from util.custom_role_converter import CustomRoleConverter
from util.discord_handler import DiscordHandler
from util.json import read_json, write_json

POLL_FILE = "data/poll.json"


# This is a huge hack but it technically works
def _urlencode(*args, **kwargs) -> str:
    kwargs.update(quote_via=parse.quote)
    return parse.urlencode(*args, **kwargs)


requests.models.urlencode = _urlencode


# ################### COMMANDS ################### #


class Commands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.add_instructor_role_counter = 0
        self.bot.d_handler = DiscordHandler()
        self.role_converter = CustomRoleConverter()

        if not isfile(POLL_FILE):
            create_file_if_not_exists(POLL_FILE)
            write_json({}, POLL_FILE)

        self.poll_dict = read_json(POLL_FILE)

        for channel in filter(lambda ch: not self.bot.get_channel(int(ch)), list(self.poll_dict)):
            del self.poll_dict[channel]

        for channel in (c for g in self.bot.guilds for c in g.text_channels if str(c.id) not in self.poll_dict):
            self.poll_dict.update({str(channel.id): ""})

        write_json(self.poll_dict, POLL_FILE)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def emojify(self, ctx: commands.Context):
        """
        `!emojify` __`Emoji text generator`__

        **Usage:** !emojify <text>

        **Examples:**
        `!emojify hello` prints "hello" with emoji
        `!emojify b` prints b with emoji"
        """

        mapping = {"A": "🇦", "B": "🅱", "C": "🇨", "D": "🇩", "E": "🇪", "F": "🇫", "G": "🇬", "H": "🇭", "I": "🇮", "J": "🇯", "K": "🇰", "L": "🇱", "M": "🇲", "N": "🇳", "O": "🇴", "P": "🇵", "Q": "🇶", "R": "🇷", "S": "🇸", "T": "🇹", "U": "🇺", "V": "🇻", "W": "🇼", "X": "🇽", "Y": "🇾", "Z": "🇿", "0": "0️⃣", "1": "1️⃣", "2": "2️⃣", "3": "3️⃣", "4": "4️⃣", "5": "5️⃣", "6": "6️⃣", "7": "7️⃣", "8": "8️⃣", "9": "9️⃣"}

        text = ctx.message.content[9:].upper()
        output = "".join(mapping[i] + (" " if i in string.ascii_uppercase else "") if i in mapping else i for i in text)

        await ctx.send(output)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def joinrole(self, ctx: commands.Context, *arg: str):
        """
        `!joinrole` __`Adds a role to yourself`__

        **Usage:** !joinrole [role name]

        **Examples:**
        `!joinrole Study Group` adds the Study Group role to yourself

        **Valid Roles:**
        Looking for Partners, Study Group, He/Him/His, She/Her/Hers, They/Them/Theirs, Ze/Zir/Zirs, notify
        """

        await ctx.message.delete()

        # case where role name is space separated
        name = " ".join(arg)

        # Display help if given no argument
        if not name:
            raise BadArgs("", show_help=True)

        # make sure that you can't add roles like "prof" or "ta"
        valid_roles = ["Looking for Partners", "Study Group", "He/Him/His", "She/Her/Hers", "They/Them/Theirs", "Ze/Zir/Zirs", "notify"]

        # Grab the role that the user selected
        # Converters! this also makes aliases unnecessary
        try:
            role = await self.role_converter.convert(ctx, name)
        except commands.RoleNotFound:
            raise BadArgs("You can't add that role!", show_help=True)

        # Ensure that the author does not already have the role
        if role in ctx.author.roles:
            raise BadArgs("you already have that role!")

        # Special handling for roles that exist but can not be selected by a student
        if role.name not in valid_roles:
            self.add_instructor_role_counter += 1

            if self.add_instructor_role_counter > 5:
                if self.add_instructor_role_counter == 42:
                    if random.random() > 0.999:
                        raise BadArgs("Congratulations, you found the secret message. IDEK how you did it, but good job. Still can't add the instructor role though. Bummer, I know.")
                elif self.add_instructor_role_counter == 69:
                    if random.random() > 0.9999:
                        raise BadArgs("nice.")
                raise BadArgs("You can't add that role, but if you try again, maybe something different will happen on the 42nd attempt")
            else:
                raise BadArgs("you cannot add an instructor/invalid role!", show_help=True)

        await ctx.author.add_roles(role)
        await ctx.send("role added!", delete_after=5)

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def latex(self, ctx: commands.Context, *args: str):
        """
        `!latex` __`LaTeX equation render`__

        **Usage:** !latex <equation>

        **Examples:**
        `!latex $\\frac{a}{b}$` [img]
        """

        formula = " ".join(args).strip("\n ")

        if sm := re.match(r"```(latex|tex)", formula):
            formula = formula[6 if sm.group(1) == "tex" else 8:].strip("`")

        data = requests.get(f"https://latex.codecogs.com/png.image?\dpi{{300}} \\bg_white {formula}")

        await ctx.send(file=discord.File(BytesIO(data.content), filename="latex.png"))

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def leaverole(self, ctx: commands.Context, *arg: str):
        """
        `!leaverole` __`Removes an existing role from yourself`__

        **Usage:** !leave [role name]

        **Examples:**
        `!leaverole Study Group` removes the Study Group role from yourself
        """

        await ctx.message.delete()

        # case where role name is space separated
        name = " ".join(arg).lower()

        if not name:
            raise BadArgs("", show_help=True)

        try:
            role = await self.role_converter.convert(ctx, name)
        except commands.RoleNotFound:
            raise BadArgs("That role doesn't exist!", show_help=True)

        if role not in ctx.author.roles:
            raise BadArgs("you don't have that role!")

        await ctx.author.remove_roles(role)
        await ctx.send("role removed!", delete_after=5)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def poll(self, ctx: commands.Context):
        """
        `!poll` __`Poll generator`__

        **Usage:** !poll <question | check | end> | <option> | <option> | [option] | [...]

        **Examples:**
        `!poll poll | yee | nah` generates poll titled "poll" with options "yee" and "nah"
        `!poll check` returns content of last poll
        `!poll end` ends current poll in channel and returns results
        """

        poll_list = tuple(map(str.strip, ctx.message.content[6:].split("|")))
        question = poll_list[0]
        options = poll_list[1:]

        id_ = self.poll_dict.get(str(ctx.channel.id), "")

        if question in ("check", "end"):
            if end := (question == "end"):
                del self.poll_dict[str(ctx.channel.id)]
                write_json(self.poll_dict, "data/poll.json")

            if not id_:
                raise BadArgs("No active poll found.")

            try:
                poll_message = await ctx.channel.fetch_message(id_)
            except discord.NotFound:
                raise BadArgs("Looks like someone deleted the poll, or there is no active poll.")

            embed = poll_message.embeds[0]
            unformatted_options = [x.strip().split(": ") for x in embed.description.split("\n")]
            options_dict = {}

            for x in unformatted_options:
                options_dict[x[0]] = x[1]

            tally = {x: 0 for x in options_dict}

            for reaction in poll_message.reactions:
                if reaction.emoji in options_dict:
                    async for reactor in reaction.users():
                        if reactor.id != self.bot.user.id:
                            tally[reaction.emoji] += 1

            output = f"{'Final' if end else 'Current'} results of the poll **\"{embed.title}\"**\nLink: {poll_message.jump_url}\n```"

            max_len = max(map(len, options_dict.values()))

            for key in tally:
                output += f"{options_dict[key].ljust(max_len)}: " + \
                          f"{('👑' * tally[key]).replace('👑', '▓', ((tally[key] - 1) or 1) - 1) if tally[key] == max(tally.values()) else '░' * tally[key]}".ljust(max(tally.values())).replace('👑👑', '👑') + \
                          f" ({tally[key]} votes, {round(tally[key] / sum(tally.values()) * 100, 2) if sum(tally.values()) else 0}%)\n\n"

            output += "```"

            files = []

            for url in options_dict.values():
                if mimetypes.guess_type(url)[0] and mimetypes.guess_type(url)[0].startswith("image"):
                    filex = BytesIO(requests.get(url).content)
                    filex.seek(0)
                    files.append(discord.File(filex, filename=url))

            return await ctx.send(output, files=files)

        if id_:
            return await ctx.send("There's an active poll in this channel already.")

        if len(options) <= 1:
            raise BadArgs("Please enter more than one option to poll.", show_help=True)
        elif len(options) > 20:
            raise BadArgs("Please limit to 10 options.")
        elif len(options) == 2 and options[0] == "yes" and options[1] == "no":
            reactions = ["✅", "❌"]
        else:
            reactions = tuple(chr(127462 + i) for i in range(26))

        description = []

        for x, option in enumerate(options):
            description += f"\n{reactions[x]}: {option}"

        embed = discord.Embed(title=question, description="".join(description))
        files = []

        for url in options:
            if mimetypes.guess_type(url)[0] and mimetypes.guess_type(url)[0].startswith("image"):
                filex = BytesIO(requests.get(url).content)
                filex.seek(0)
                files.append(discord.File(filex, filename=url))

        react_message = await ctx.send(embed=embed, files=files)

        for reaction in reactions[:len(options)]:
            await react_message.add_reaction(reaction)

        self.poll_dict[str(ctx.channel.id)] = react_message.id
        write_json(self.poll_dict, "data/poll.json")

    @commands.command()
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def purge(self, ctx: commands.Context, amount: int, *arg: str):
        """
        `!purge` __`purges all messages satisfying conditions from the last specified number of messages in channel.`__

        Usage: !purge <amount of messages to look through> [user | string <containing string> | reactions | type]

        **Options:**
        `user` - Only deletes messages sent by this user
        `string` - Will delete messages containing following string
        `reactions` - Will remove all reactions from messages
        `type` - One of valid types

        **Valid Types:**
        `text` - Is text only? (ignores image or embeds)
        `links` - Contains links?
        `bots` - Was send by bots?
        `images` - Contains images?
        `embeds` - Contains embeds?
        `mentions` - Contains user, role or everyone/here mentions?

        **Examples:**
        `!purge 100` deletes last 100 messages in channel
        `!purge 50 abc#1234` deletes all messages sent by abc#1234 in last 50 messages
        `!purge 30 string asdf ghjk` deletes all messages containing "asdf ghjk" in last 30 messages
        """

        await ctx.message.delete()

        if not ctx.author.guild_permissions.manage_messages:
            return await ctx.send("Oops! It looks like you don't have the permission to purge.", delete_after=5)

        if amount > 100:
            raise BadArgs("Please enter a smaller number to purge.")

        if not arg:
            total_messages = await ctx.channel.purge(limit=amount)
            return await ctx.send(f"**{len(total_messages)}** message{'s' if len(total_messages) > 1 else ''} purged.", delete_after=5)

        match arg[0]:
            case "reactions":
                messages = await ctx.channel.history(limit=amount).flatten()

                for i in messages:
                    if i.reactions:
                        await i.clear_reactions()

                await ctx.send(f"Reactions removed from the last {'' if amount == 1 else '**' + str(amount) + '**'} message{'s' if amount > 1 else ''}.", delete_after=5)
            case "text":
                total_messages = await ctx.channel.purge(limit=amount, check=lambda m: not m.embeds and not m.attachments)
                await ctx.send(f"**{len(total_messages)}** text message{'s' if len(total_messages) > 1 else ''} purged.")
            case "bots":
                total_messages = await ctx.channel.purge(limit=amount, check=lambda m: m.author.bot)
                await ctx.send(f"**{len(total_messages)}** bot message{'s' if len(total_messages) > 1 else ''} purged.", delete_after=5)
            case "images":
                total_messages = await ctx.channel.purge(limit=amount, check=lambda m: m.attachments)
                await ctx.send(f"**{len(total_messages)}** image message{'s' if len(total_messages) > 1 else ''} purged.", delete_after=5)
            case "embeds":
                total_messages = await ctx.channel.purge(limit=amount, check=lambda m: m.embeds)
                await ctx.send(f"**{len(total_messages)}** embed message{'s' if len(total_messages) > 1 else ''} purged.", delete_after=5)
            case "mentions":
                total_messages = await ctx.channel.purge(limit=amount, check=lambda m: m.mentions)
                await ctx.send(f"**{len(total_messages)}** mention message{'s' if len(total_messages) > 1 else ''} purged.", delete_after=5)
            case "links":
                total_messages = await ctx.channel.purge(limit=amount, check=lambda m: bool(re.search(r"https?://[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+", m.content)))
                await ctx.send(f"**{len(total_messages)}** link message{'s' if len(total_messages) > 1 else ''} purged.", delete_after=5)
            case "string":
                total_messages = await ctx.channel.purge(limit=amount, check=lambda m: " ".join(arg[1:]) in m.content)
                await ctx.send(f"**{len(total_messages)}** message{'s' if len(total_messages) > 1 else ''} containing \"{' '.join(arg[1:])}\" purged.")
            case _:
                try:
                    user = await MemberConverter().convert(ctx, " ".join(arg))
                except BadArgument:
                    return await ctx.send("That user doesn't exist.", delete_after=5)

                total_messages = await ctx.channel.purge(limit=amount, check=lambda m: m.author == user)
                await ctx.send(f"**{len(total_messages)}** message{'s' if len(total_messages) > 1 else ''} from {user.display_name} purged.", delete_after=5)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def shut(self, ctx: commands.Context):
        await ctx.message.delete()
        change = ""

        for role in ctx.guild.roles:
            if role.permissions.administrator:
                continue

            new_perms = role.permissions

            if not role.permissions.send_messages:
                change = "enabled messaging permissions"
                new_perms.update(send_messages=True)
            else:
                change = "disabled messaging permissions"
                new_perms.update(send_messages=False)

            await role.edit(permissions=new_perms)

        await ctx.send(change)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def userstats(self, ctx: commands.Context, *args: discord.Member):
        """
        `!userstats` __`Check user profile and stats`__

        **Usage:** !userstats [USER]

        **Examples:**
        `!userstats abc#1234` [embed]
        """

        # we use both user and member objects, since some stats can only be obtained
        # from either user or member object

        if not args:
            user = ctx.author
        else:
            user = args[0]

        async with ctx.channel.typing():
            most_active_channel = 0
            most_active_channel_name = None
            cum_message_count = 0
            yesterday = (datetime.now() - timedelta(days=1)).replace(tzinfo=pytz.timezone("US/Pacific")).astimezone(timezone.utc).replace(tzinfo=None)

            for channel in ctx.guild.text_channels:
                counter = 0

                async for message in channel.history(after=yesterday, limit=None):
                    if message.author == user:
                        counter += 1
                        cum_message_count += 1

                if counter > most_active_channel:
                    most_active_channel = counter
                    most_active_channel_name = "#" + channel.name

            embed = discord.Embed(title=f"Report for user `{user.name}#{user.discriminator}` (all times in UTC)")
            embed.add_field(name="Date Joined", value=user.joined_at.strftime("%A, %Y %B %d @ %H:%M:%S"))
            embed.add_field(name="Account Created", value=user.created_at.strftime("%A, %Y %B %d @ %H:%M:%S"))
            embed.add_field(name="Roles", value=", ".join([str(i) for i in sorted(user.roles[1:], key=lambda role: role.position, reverse=True)]))
            embed.add_field(name="Most active text channel in last 24 h", value=f"{most_active_channel_name} ({most_active_channel} messages)")
            embed.add_field(name="Total messages sent in last 24 h", value=str(cum_message_count))

            await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def votes(self, ctx: commands.Context):
        """
        `!votes` __`Top votes for server icon`__

        **Usage:** !votes

        **Examples:**
        `!votes` returns top 5 icons sorted by score
        """

        async with ctx.channel.typing():
            images = []

            for c in ctx.guild.text_channels:
                if c.name == "course-events":
                    channel = c
                    break
            else:
                raise BadArgs("votes channel doesn't exist.")

            async for message in channel.history():
                if message.attachments or message.embeds:
                    count = 0

                    for reaction in message.reactions:
                        if reaction.emoji == "⬆️":
                            count += reaction.count - (message.author in await reaction.users().flatten())

                    images.append([message.attachments[0].url, count])

            images = sorted(images, key=lambda image: image[1], reverse=True)[:5]

            for image in images:
                embed = discord.Embed(colour=random.randint(0, 0xFFFFFF))
                embed.add_field(name="Score", value=image[1])
                embed.set_thumbnail(url=image[0])
                await ctx.send(embed=embed)

    # add more commands here with the same syntax
    # also just look up the docs lol i can't do everything


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Commands(bot))
