import argparse
import asyncio
import json
import os
import random
import re
import traceback
from datetime import datetime
from os.path import isfile, join

import discord
from discord.ext import commands
from dotenv import load_dotenv

from cogs.canvas import Canvas
from cogs.piazza import Piazza
from util.badargs import BadArgs
from util.create_file import create_file_if_not_exists

CANVAS_COLOR = 0xe13f2b
CANVAS_THUMBNAIL_URL = "https://lh3.googleusercontent.com/2_M-EEPXb2xTMQSTZpSUefHR3TjgOCsawM3pjVG47jI-BrHoXGhKBpdEHeLElT95060B=s180"

load_dotenv()
CS221BOT_KEY = os.getenv("CS221BOT_KEY")

bot = commands.Bot(command_prefix="!", help_command=None, intents=discord.Intents.all())

parser = argparse.ArgumentParser(description="Run CS221Bot")
parser.add_argument("--cnu", dest="notify_unpublished", action="store_true",
                    help="Allow the bot to send notifications about unpublished Canvas modules (if you have access) as well as published ones.")
args = parser.parse_args()


def loadJSON(jsonfile):
    with open(jsonfile, "r") as f:
        return json.load(f)


def writeJSON(data, jsonfile):
    with open(jsonfile, "w") as f:
        json.dump(data, f)


async def status_task():
    await bot.wait_until_ready()

    while not bot.is_closed():
        online_members = {member for guild in bot.guilds for member in guild.members if not member.bot and member.status != discord.Status.offline}

        play = ["with the \"help\" command", " ", "with your mind", "ƃuᴉʎɐlԀ", "...something?",
                "a game? Or am I?", "¯\_(ツ)_/¯", f"with {len(online_members)} people", "with image manipulation"]
        listen = ["smart music", "... wait I can't hear anything",
                  "rush 🅱", "C++ short course"]
        watch = ["TV", "YouTube vids", "over you",
                 "how to make a bot", "C++ tutorials", "I, Robot"]

        rng = random.randrange(0, 3)

        if rng == 0:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=random.choice(play)))
        elif rng == 1:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=random.choice(listen)))
        else:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=random.choice(watch)))

        await asyncio.sleep(30)


def startup():
    files = ("data/poll.json", "data/canvas.json", "data/piazza.json")

    for f in files:
        if not isfile(f):
            create_file_if_not_exists(f)
            bot.writeJSON({}, f)

    bot.poll_dict = bot.loadJSON("data/poll.json")
    bot.canvas_dict = bot.loadJSON("data/canvas.json")
    bot.piazza_dict = bot.loadJSON("data/piazza.json")

    for channel in filter(lambda ch: not bot.get_channel(int(ch)), list(bot.poll_dict)):
        del bot.poll_dict[channel]

    for channel in (c for g in bot.guilds for c in g.text_channels if str(c.id) not in bot.poll_dict):
        bot.poll_dict.update({str(channel.id): ""})

    bot.writeJSON(bot.poll_dict, "data/poll.json")

    Canvas.canvas_init(bot.get_cog("Canvas"))
    Piazza.piazza_start(bot.get_cog("Piazza"))


async def wipe_dms():
    guild = bot.get_guild(745503628479037492)

    while True:
        await asyncio.sleep(300)
        now = datetime.utcnow()

        for channel in filter(lambda c: c.name.startswith("221dm-"), guild.channels):
            if msg := next(channel.history(limit=1), None):
                if (now - msg.created_at).total_seconds() >= 86400:
                    await channel.delete()
            else:
                await channel.delete()


@bot.event
async def on_ready():
    startup()
    print("Logged in successfully")
    bot.loop.create_task(status_task())
    bot.loop.create_task(wipe_dms())
    bot.loop.create_task(Piazza.track_inotes(bot.get_cog("Piazza")))
    bot.loop.create_task(Piazza.send_pupdate(bot.get_cog("Piazza")))
    bot.loop.create_task(Canvas.stream_tracking(bot.get_cog("Canvas")))
    bot.loop.create_task(Canvas.assignment_reminder(bot.get_cog("Canvas")))
    bot.loop.create_task(bot.get_cog("Canvas").update_modules_hourly())


@bot.event
async def on_guild_join(guild):
    for channel in guild.text_channels:
        bot.poll_dict.update({str(channel.id): ""})
        bot.writeJSON(bot.poll_dict, "data/poll.json")


@bot.event
async def on_guild_remove(guild):
    for channel in filter(lambda c: str(c.id) in bot.poll_dict, guild.channels):
        del bot.poll_dict[str(channel.id)]
        bot.writeJSON(bot.poll_dict, "data/poll.json")


@bot.event
async def on_channel_create(channel):
    if isinstance(channel, discord.TextChannel):
        bot.poll_dict.update({str(channel.id): ""})
        bot.writeJSON(bot.poll_dict, "data/poll.json")


@bot.event
async def on_channel_delete(channel):
    if str(channel.id) in bot.poll_dict:
        del bot.poll_dict[str(channel.id)]
        bot.writeJSON(bot.poll_dict, "data/poll.json")


@bot.event
async def on_message_edit(before, after):
    await bot.process_commands(after)


@bot.event
async def on_message(message):
    if isinstance(message.channel, discord.abc.PrivateChannel):
        return

    if not message.author.bot:
        # debugging
        # with open("messages.txt", "a") as f:
        # 	print(f"{message.guild.name}: {message.channel.name}: {message.author.name}: \"{message.content}\" @ {str(datetime.datetime.now())} \r\n", file = f)
        # print(message.content)

        # this is some weird bs happening only with android users in certain servers and idk why it happens
        # but basically the '@' is screwed up
        if re.findall(r"<<@&457618814058758146>&?\d{18}>", message.content):
            new = message.content.replace("<@&457618814058758146>", "@")
            await message.channel.send(new)

        await bot.process_commands(message)


if __name__ == "__main__":
    bot.loadJSON = loadJSON
    bot.writeJSON = writeJSON

    # True if the bot should send notifications about new *unpublished* modules on Canvas; False otherwise.
    # This only matters if the host of the bot has access to unpublished modules. If the host does
    # not have access, then the bot won't know about any unpublished modules and won't send any info
    # about them anyway.
    bot.notify_unpublished = args.notify_unpublished

    for extension in filter(lambda f: isfile(join("cogs", f)) and f != "__init__.py", os.listdir("cogs")):
        bot.load_extension(f"cogs.{extension[:-3]}")
        print(f"{extension} module loaded")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound) or isinstance(error, discord.HTTPException) or isinstance(error, discord.NotFound):
        pass
    elif isinstance(error, BadArgs) or str(type(error)) == "<class 'cogs.meta.BadArgs'>":
        await error.print(ctx)
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"Oops! That command is on cooldown right now. Please wait **{round(error.retry_after, 3)}** seconds before trying again.", delete_after=error.retry_after)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"The required argument(s) {error.param} is/are missing.", delete_after=5)
    elif isinstance(error, commands.DisabledCommand):
        await ctx.send("This command is disabled.", delete_after=5)
    elif isinstance(error, commands.MissingPermissions) or isinstance(error, commands.BotMissingPermissions):
        await ctx.send(error, delete_after=5)
    else:
        etype = type(error)
        trace = error.__traceback__

        try:
            await ctx.send(("```" + "".join(traceback.format_exception(etype, error, trace, 999)) + "```").replace("C:\\Users\\William\\anaconda3\\lib\\site-packages\\", "").replace("D:\\my file of stuff\\discordbot\\", ""))
        except Exception:
            print(("```" + "".join(traceback.format_exception(etype, error, trace, 999)) + "```").replace("C:\\Users\\William\\anaconda3\\lib\\site-packages\\", "").replace("D:\\my file of stuff\\discordbot\\", ""))

bot.run(CS221BOT_KEY)
