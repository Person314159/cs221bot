import asyncio
import os
import time
from datetime import datetime, timedelta, timezone
from os.path import isfile

import discord
from discord.ext import commands
from dotenv import load_dotenv

from util.badargs import BadArgs
from util.create_file import create_file_if_not_exists
from util.json import read_json, write_json
from util.piazza_handler import InvalidPostID, PiazzaHandler

PIAZZA_THUMBNAIL_URL = "https://store-images.s-microsoft.com/image/apps.25584.554ac7a6-231b-46e2-9960-a059f3147dbe.727eba5c-763a-473f-981d-ffba9c91adab.4e76ea6a-bd74-487f-bf57-3612e43ca795.png"
PIAZZA_FILE = "data/piazza.json"

load_dotenv()
PIAZZA_EMAIL = os.getenv("PIAZZA_EMAIL")
PIAZZA_PASSWORD = os.getenv("PIAZZA_PASSWORD")


class Piazza(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        if not isfile(PIAZZA_FILE):
            create_file_if_not_exists(PIAZZA_FILE)
            write_json({}, PIAZZA_FILE)

        self.piazza_dict = read_json(PIAZZA_FILE)

    # # start of Piazza functions # #
    # didn't want to support multiple PiazzaHandler instances because it's associated with
    # a single account (unsafe to send sensitive information through Discord, so there's
    # no way to login to another account without also having access to prod env variables)
    # and the API is also rate-limited, so it's probably not a good idea to spam Piazza's server
    # with an unlimited # of POST requests per instance everyday. One instance should be safe
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def pinit(self, ctx: commands.Context, name: str, pid: str):
        """
        `!pinit` _ `course name` _ _ `piazza id` _

        **Usage:** !pinit <course name> <piazza id>

        **Examples:**
        `!pinit CPSC221 abcdef1234` creates a CPSC221 Piazza instance for the server

        *Only usable by TAs and Profs
        """

        self.bot.d_handler.piazza_handler = PiazzaHandler(name, pid, PIAZZA_EMAIL, PIAZZA_PASSWORD, ctx.guild)

        # dict.get default to empty list so KeyError is never thrown
        for channel in self.piazza_dict.get("channels", []):
            self.bot.d_handler.piazza_handler.add_channel(channel)

        self.piazza_dict["channels"] = [ctx.channel.id]
        self.piazza_dict["course_name"] = name
        self.piazza_dict["piazza_id"] = pid
        self.piazza_dict["guild_id"] = ctx.guild.id
        write_json(self.piazza_dict, "data/piazza.json")
        response = f"Piazza instance created!\nName: {name}\nPiazza ID: {pid}\n"
        response += "If the above doesn't look right, please use `!pinit` again with the correct arguments"
        await ctx.send(response)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def ptrack(self, ctx: commands.Context):
        """
        `!ptrack` __`Tracks Piazza posts in channel`__

        **Usage:** !ptrack

        **Examples:**
        `!ptrack` adds the current channel's id to the Piazza instance's list of channels

        The channels added through `!ptrack` are where send_pupdate and track_inotes send their responses.

        *Only usable by TAs and Profs
        """

        cid = ctx.message.channel.id

        self.bot.d_handler.piazza_handler.add_channel(cid)
        self.piazza_dict["channels"] = self.bot.d_handler.piazza_handler.channels
        write_json(self.piazza_dict, "data/piazza.json")
        await ctx.send("Channel added to tracking!")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def puntrack(self, ctx: commands.Context):
        """
        `!puntrack` __`Untracks Piazza posts in channel`__

        **Usage:** !puntrack

        **Examples:**
        `!puntrack` removes the current channel's id to the Piazza instance's list of channels

        The channels removed through `!puntrack` are where send_pupdate and track_inotes send their responses.

        *Only usable by TAs and Profs
        """

        cid = ctx.message.channel.id

        self.bot.d_handler.piazza_handler.remove_channel(cid)
        self.piazza_dict["channels"] = self.bot.d_handler.piazza_handler.channels
        write_json(self.piazza_dict, "data/piazza.json")
        await ctx.send("Channel removed from tracking!")

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def ppinned(self, ctx: commands.Context):
        """
        `!ppinned`

        **Usage:** !ppinned

        **Examples:**
        `!ppinned` sends a list of the Piazza's pinned posts to the calling channel

        *to prevent hitting the rate-limit, only usable once every 5 secs channel-wide*
        """

        if self.bot.d_handler.piazza_handler:
            posts = self.bot.d_handler.piazza_handler.get_pinned()
            embed = discord.Embed(title=f"**Pinned posts for {self.bot.d_handler.piazza_handler.course_name}:**", colour=0x497aaa)

            for post in posts:
                embed.add_field(name=f"@{post['num']}", value=f"[{post['subject']}]({post['url']})", inline=False)

            embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=str(ctx.author.avatar_url))

            await ctx.send(embed=embed)
        else:
            raise BadArgs("Piazza hasn't been instantiated yet!")

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pread(self, ctx: commands.Context, post_id: int):
        """
        `!pread` __`post id`__

        **Usage:** !pread <post id>

        **Examples:**
        `!pread 828` returns an embed with the [post](https://piazza.com/class/ke1ukp9g4xx6oi?cid=828)'s
        info (question, answer, answer type, tags)
        """

        if not self.bot.d_handler.piazza_handler:
            raise BadArgs("Piazza hasn't been instantiated yet!")

        try:
            post = self.bot.d_handler.piazza_handler.get_post(post_id)
        except InvalidPostID:
            raise BadArgs("Post not found.")

        if post:
            post_embed = self.create_post_embed(post)
            await ctx.send(embed=post_embed)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def ptest(self, ctx: commands.Context):
        """
        `!ptest`

        **Usage:** !ptest

        **Examples:**
        `!ptest` simulates a single call of `send_pupdate` to ensure the set-up was done correctly.
        """

        await self.send_piazza_posts()

    def create_post_embed(self, post: dict) -> discord.Embed:
        if post:
            post_embed = discord.Embed(title=post["subject"], url=post["url"], description=post["num"])
            post_embed.add_field(name=post["post_type"], value=post["post_body"], inline=False)
            post_embed.add_field(name=f"{post['num_followups']} followup comments hidden", value="Click the title above to access the rest of the post.", inline=False)

            if post["post_type"] != "Note":
                post_embed.add_field(name="Instructor Answer", value=post["i_answer"], inline=False)
                post_embed.add_field(name="Student Answer", value=post["s_answer"], inline=False)

            if post["first_image"]:
                post_embed.set_image(url=post["first_image"])

            post_embed.set_thumbnail(url=PIAZZA_THUMBNAIL_URL)
            post_embed.set_footer(text=f"tags: {post['tags']}")
            return post_embed

    async def send_at_time(self) -> None:
        # default set to midnight UTC (4/5 PM PT)
        today = datetime.now(timezone.utc)
        hours = round(time.timezone / 3600) - time.daylight
        post_time = datetime(today.year, today.month, today.day, hour=hours) + timedelta(days=1)
        time_until_post = post_time - today

        if time_until_post.total_seconds():
            await asyncio.sleep(time_until_post.total_seconds())

    async def send_pupdate(self) -> None:
        while True:
            # Sends at midnight
            await self.send_at_time()
            await self.send_piazza_posts()

    async def send_piazza_posts(self) -> None:
        if not self.bot.d_handler.piazza_handler:
            return

        posts = await self.bot.d_handler.piazza_handler.get_posts_in_range()

        if posts:
            response = f"**{self.bot.d_handler.piazza_handler.course_name}'s posts for {datetime.today().strftime('%a. %B %d, %Y')}**\n"

            response += "Instructor's Notes:\n"

            if posts[0]:
                for ipost in posts[0]:
                    response += f"@{ipost['num']}: {ipost['subject']} <{ipost['url']}>\n"
            else:
                response += "None today!\n"

            response += "\nDiscussion posts: \n"

            if not posts[1]:
                response += "None today!"

            for post in posts[1]:
                response += f"@{post['num']}: {post['subject']} <{post['url']}>\n"

            for ch in self.bot.d_handler.piazza_handler.channels:
                channel = self.bot.get_channel(ch)
                await channel.send(response)

    def piazza_start(self) -> None:
        if all(field in self.piazza_dict for field in ("course_name", "piazza_id", "guild_id")):
            self.bot.d_handler.piazza_handler = PiazzaHandler(self.piazza_dict["course_name"], self.piazza_dict["piazza_id"], PIAZZA_EMAIL, PIAZZA_PASSWORD, self.piazza_dict["guild_id"])

        # dict.get will default to an empty tuple so a key error is never raised
        # We need to have the empty tuple because if the default value is None, an error is raised (NoneType object
        # is not iterable).
        for ch in self.piazza_dict.get("channels", tuple()):
            self.bot.d_handler.piazza_handler.add_channel(int(ch))


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Piazza(bot))