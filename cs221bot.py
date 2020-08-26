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

bot = commands.Bot(command_prefix = "!", help_command = None)

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
        num_guilds = len(bot.guilds)
        online_members = []

        for guild in bot.guilds:
            for member in guild.members:
                if not member.bot and member.status != discord.Status.offline:
                    if member not in online_members:
                        online_members.append(member)

        play = ["with the \"help\" command", " ", "with your mind", "ƃuᴉʎɐlԀ", "...something?", "a game? Or am I?", "¯\_(ツ)_/¯", f"with {len(online_members)} people", "with image manipulation"]
        listen = ["smart music", "... wait I can't hear anything", "rush 🅱", "C++ short course"]
        watch = ["TV", "YouTube vids", "over you", "how to make a bot", "C++ tutorials"]

        rng = random.randrange(0, 3)

        if rng == 0:
            await bot.change_presence(activity = discord.Activity(type = discord.ActivityType.playing, name = random.choice(play)))
        elif rng == 1:
            await bot.change_presence(activity = discord.Activity(type = discord.ActivityType.listening, name = random.choice(listen)))
        else:
            await bot.change_presence(activity = discord.Activity(type = discord.ActivityType.watching, name = random.choice(watch)))

        await asyncio.sleep(30)

def startup():
    bot.poll_dict = bot.loadJSON("poll.json")

    for channel in list(bot.poll_dict):
        if not bot.get_channel(int(channel)):
            del bot.poll_dict[channel]
    bot.writeJSON(bot.poll_dict, "poll.json")

    for guild in bot.guilds:
        for channel in guild.text_channels:
            if str(channel.id) not in bot.poll_dict:
                bot.poll_dict.update({str(channel.id): ""})
                bot.writeJSON(bot.poll_dict, "poll.json")
    return

@bot.event
async def on_ready():
    startup()
    print("Logged in successfully")
    bot.loop.create_task(status_task())

@bot.event
async def on_guild_join(guild):
	for channel in guild.text_channels:
		bot.poll_dict.update({str(channel.id) : ""})
		bot.writeJSON(bot.poll_dict, "poll.json")

@bot.event
async def on_guild_remove(guild):
	for channel in guild.channels:
		if str(channel.id) in bot.poll_dict:
			del bot.poll_dict[str(channel.id)]
			bot.writeJSON(bot.poll_dict, "poll.json")

@bot.event
async def on_channel_create(channel):
	if isinstance(channel, discord.TextChannel):
		bot.poll_dict.update({str(channel.id) : ""})
		bot.writeJSON(bot.poll_dict, "poll.json")

@bot.event
async def on_channel_delete(channel):
	if str(channel.id) in bot.poll_dict:
		del bot.poll_dict[str(channel.id)]
		bot.writeJSON(bot.poll_dict, "poll.json")

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

        if message.channel.id == 745517292892454963 and (message.attachments or message.embeds):
            if (message.attachments[0].height, message.attachments[0].width) < (512, 512):
                await message.delete()
                await message.channel.send("Please submit an image with at least 512x512 dimensions!", delete_after = 5)
            else: 
                await message.add_reaction("⬆️")
                await message.add_reaction("⬇️")

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
        await ctx.send(f"Oops! That command is on cooldown right now. Please wait **{round(error.retry_after, 3)}** seconds before trying again.", delete_after = error.retry_after)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"The required argument(s) {error.param} is/are missing.", delete_after = 5)
    elif isinstance(error, commands.DisabledCommand):
        await ctx.send("This command is disabled.", delete_after = 5)
    elif isinstance(error, commands.MissingPermissions) or isinstance(error, commands.BotMissingPermissions):
        await ctx.send(error, delete_after = 5)
    else:
        etype = type(error)
        trace = error.__traceback__

        # prints full traceback
        try:
            await ctx.send("```" + "".join(traceback.format_exception(etype, error, trace, 999)) + "```".replace("C:\\Users\\William\\anaconda3\\lib\\site-packages\\", "").replace("D:\\my file of stuff\\cs221bot\\", ""))
        except Exception:
            print("```" + "".join(traceback.format_exception(etype, error, trace, 999)) + "```".replace("C:\\Users\\William\\anaconda3\\lib\\site-packages\\", "").replace("D:\\my file of stuff\\cs221bot\\", ""))

bot.run(os.getenv("CS221BOT_KEY"))
