import asyncio
import json
import os
import random
import re
import time
import traceback
from datetime import datetime
from os.path import isfile, join

import discord
from discord.ext import commands
from dotenv import load_dotenv

from commands import Main

CANVAS_COLOR = 0xe13f2b
CANVAS_THUMBNAIL_URL = "https://lh3.googleusercontent.com/2_M-EEPXb2xTMQSTZpSUefHR3TjgOCsawM3pjVG47jI-BrHoXGhKBpdEHeLElT95060B=s180"

load_dotenv()
CS221BOT_KEY = os.getenv("CS221BOT_KEY")

bot = commands.Bot(command_prefix="!", help_command=None, intents=discord.Intents.all())


def loadJSON(jsonfile):
    with open(jsonfile, "r") as f:
        b = json.load(f)
        return json.loads(b)


def writeJSON(data, jsonfile):
    b = json.dumps(data)
    with open(jsonfile, "w") as f:
        json.dump(b, f)


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
    try:
        bot.poll_dict = bot.loadJSON("data/poll.json")
        bot.canvas_dict = bot.loadJSON("data/canvas.json")
        bot.piazza_dict = bot.loadJSON("data/piazza.json")
    except FileNotFoundError:
        bot.writeJSON({}, "data/poll.json")
        bot.poll_dict = bot.loadJSON("data/poll.json")
        bot.writeJSON({}, "data/canvas.json")
        bot.canvas_dict = bot.loadJSON("data/canvas.json")
        bot.writeJSON({}, "data/piazza.json")
        bot.piazza_dict = bot.loadJSON("data/piazza.json")

    for channel in list(bot.poll_dict):
        if not bot.get_channel(int(channel)):
            del bot.poll_dict[channel]

    for guild in bot.guilds:
        for channel in guild.text_channels:
            if str(channel.id) not in bot.poll_dict:
                bot.poll_dict.update({str(channel.id): ""})

    bot.writeJSON(bot.poll_dict, "data/poll.json")

    Main.canvas_init(bot.get_cog("Main"))
    Main.piazza_start(bot.get_cog("Main"))


async def wipe_dms():
    guild = bot.get_guild(745503628479037492)

    while True:
        await asyncio.sleep(300)

        for channel in guild.channels:
            if channel.name.startswith("221dm-"):
                async for msg in channel.history(limit=1):
                    if (datetime.utcnow() - msg.created_at).total_seconds() >= 86400:
                        await channel.delete()
                        break
                else:
                    await channel.delete()


@bot.event
async def on_ready():
    startup()
    print("Logged in successfully")
    bot.loop.create_task(status_task())
    bot.loop.create_task(wipe_dms())


@bot.event
async def on_guild_join(guild):
    for channel in guild.text_channels:
        bot.poll_dict.update({str(channel.id): ""})
        bot.writeJSON(bot.poll_dict, "data/poll.json")


@bot.event
async def on_guild_remove(guild):
    for channel in guild.channels:
        if str(channel.id) in bot.poll_dict:
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
    if message.author.bot:
        return
    else:
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
    bot.load_extension("commands")
    print("commands module loaded")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound) or isinstance(error, discord.HTTPException) or isinstance(error, discord.NotFound):
        pass
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

        # prints full traceback
        try:
            await ctx.send("```" + "".join(traceback.format_exception(etype, error, trace, 999)) + "```".replace("C:\\Users\\William\\anaconda3\\lib\\site-packages\\", "").replace("D:\\my file of stuff\\cs221bot\\", ""))
        except:
            print("```" + "".join(traceback.format_exception(etype, error, trace, 999)) + "```".replace("C:\\Users\\William\\anaconda3\\lib\\site-packages\\", "").replace("D:\\my file of stuff\\cs221bot\\", ""))

bot.loop.create_task(Main.track_inotes(bot.get_cog("Main")))
bot.loop.create_task(Main.send_pupdate(bot.get_cog("Main")))
bot.loop.create_task(Main.stream_tracking(bot.get_cog("Main")))
bot.loop.create_task(Main.assignment_reminder(bot.get_cog("Main")))
bot.run(CS221BOT_KEY)
