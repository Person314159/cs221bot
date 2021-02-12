import argparse
import asyncio
import json
import os
import random
import re
import traceback
from os.path import isfile, join

import discord
from discord.ext import commands
from dotenv import load_dotenv

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
        json.dump(data, f, indent=4)


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

    bot.get_cog("Canvas").canvas_init()
    bot.get_cog("Piazza").piazza_start()


@bot.event
async def on_ready():
    startup()
    print("Logged in successfully")
    bot.loop.create_task(status_task())
    bot.loop.create_task(bot.get_cog("Piazza").send_pupdate())
    bot.loop.create_task(bot.get_cog("Canvas").stream_tracking())
    bot.loop.create_task(bot.get_cog("Canvas").assignment_reminder())
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
async def on_guild_channel_create(channel):
    if isinstance(channel, discord.TextChannel):
        bot.poll_dict.update({str(channel.id): ""})
        bot.writeJSON(bot.poll_dict, "data/poll.json")


@bot.event
async def on_guild_channel_delete(channel):
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

        if message.channel.id == 796523380920680454 and (message.attachments or message.embeds):
            if (message.attachments[0].height, message.attachments[0].width) < (512, 512):
                await message.delete()
                await message.channel.send("Please submit an image with at least 512x512 dimensions!", delete_after=5)
            else:
                await message.add_reaction("⬆️")

        await bot.process_commands(message)


if __name__ == "__main__":
    bot.loadJSON = loadJSON
    bot.writeJSON = writeJSON

    # True if the bot should send notifications about new *unpublished* modules on Canvas; False otherwise.
    # This only matters if the host of the bot has access to unpublished modules. If the host does
    # not have access, then the bot won't know about any unpublished modules and won't send any info
    # about them anyway.
    bot.notify_unpublished = args.notify_unpublished

    if bot.notify_unpublished:
        print("Warning: bot will send notifications about unpublished modules (if you have access).")

    for extension in filter(lambda f: isfile(join("cogs", f)) and f != "__init__.py", os.listdir("cogs")):
        bot.load_extension(f"cogs.{extension[:-3]}")
        print(f"{extension} module loaded")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound) or isinstance(error, discord.HTTPException):
        pass
    elif isinstance(error, BadArgs):
        await error.print(ctx)
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(error, delete_after=error.retry_after)
    elif isinstance(error, commands.MissingPermissions) or isinstance(error, commands.BotMissingPermissions):
        await ctx.send(error, delete_after=5)
    else:
        etype = type(error)
        trace = error.__traceback__

        try:
            await ctx.send("```" + "".join(traceback.format_exception(etype, error, trace)) + "```")
        except Exception:
            print("".join(traceback.format_exception(etype, error, trace)))

bot.run(CS221BOT_KEY)
