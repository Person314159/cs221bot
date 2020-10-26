import asyncio
import os
from datetime import datetime

import discord
from discord.ext import commands
from dotenv import load_dotenv

from cogs.meta import BadArgs
from handlers.piazza_handler import InvalidPostID, PiazzaHandler

PIAZZA_THUMBNAIL_URL = "https://store-images.s-microsoft.com/image/apps.25584.554ac7a6-231b-46e2-9960-a059f3147dbe.727eba5c-763a-473f-981d-ffba9c91adab.4e76ea6a-bd74-487f-bf57-3612e43ca795.png"

load_dotenv()
PIAZZA_EMAIL = os.getenv("PIAZZA_EMAIL")
PIAZZA_PASSWORD = os.getenv("PIAZZA_PASSWORD")


class Piazza(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # # start of Piazza functions # #
    # didn't want to support multiple PiazzaHandler instances because it's associated with
    # a single account (unsafe to send sensitive information through Discord, so there's
    # no way to login to another account without also having access to prod env variables)
    # and the API is also rate-limited, so it's probably not a good idea to spam Piazza's server
    # with an unlimited # of POST requests per instance everyday. One instance should be safe
    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def pinit(self, ctx, name, pid):
        """
        `!pinit` _ `course name` _ _ `piazza id` _

        **Usage:** !pinit <course name> <piazza id>

        **Examples:**
        `!pinit CPSC221 ke1ukp9g4xx6oi` creates a CPSC221 Piazza instance for the server

        *Only usable by TAs and Profs
        """

        self.bot.d_handler.piazza_handler = PiazzaHandler(name, pid, PIAZZA_EMAIL, PIAZZA_PASSWORD, ctx.guild)

        # dict.get defaults to None so KeyError is never thrown
        for channel in self.bot.piazza_dict.get("channels"):
            self.bot.d_handler.piazza_handler.add_channel(channel)

        self.bot.piazza_dict["course_name"] = name
        self.bot.piazza_dict["piazza_id"] = pid
        self.bot.piazza_dict["guild_id"] = ctx.guild.id
        self.bot.writeJSON(self.bot.piazza_dict, "data/piazza.json")
        response = f"Piazza instance created!\nName: {name}\nPiazza ID: {pid}\n"
        response += "If the above doesn't look right, please use `!pinit` again with the correct arguments"
        await ctx.send(response)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def ptrack(self, ctx, *cid):
        """
        `!ptrack` __`channel id`__

        **Usage:** !ptrack [channel id]

        **Examples:**
        `!ptrack 747259140908384386` adds CPSC221 server's #bot-commands channel id to the Piazza instance's list of tracked channels
        `!ptrack` adds the current channel's id to the Piazza instance's list of channels

        The channels added through `!ptrack` are where send_pupdate and track_inotes send their responses.

        *Only usable by TAs and Profs
        """

        if not cid:
            cid = ctx.message.channel.id
        else:
            cid = int(cid[0])

        self.bot.d_handler.piazza_handler.add_channel(cid)
        self.bot.piazza_dict["channels"] = list(self.bot.d_handler.piazza_handler.channels)
        self.bot.writeJSON(self.bot.piazza_dict, "data/piazza.json")
        await ctx.send("Channel added to tracking!")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def puntrack(self, ctx, *cid):
        """
        `!puntrack` __`channel id`__

        **Usage:** !puntrack [channel id]

        **Examples:**
        `!puntrack 747259140908384386` removes CPSC221 server's #bot-commands channel id to the Piazza instance's list of tracked channels
        `!puntrack` removes the current channel's id to the Piazza instance's list of channels

        The channels removed through `!puntrack` are where send_pupdate and track_inotes send their responses.

        *Only usable by TAs and Profs
        """

        if not cid:
            cid = ctx.message.channel.id
        else:
            cid = int(cid[0])

        self.bot.d_handler.piazza_handler.remove_channel(cid)
        self.bot.piazza_dict["channels"] = list(self.bot.d_handler.piazza_handler.channels)
        self.bot.writeJSON(self.bot.piazza_dict, "data/piazza.json")
        await ctx.send("Channel removed from tracking!")

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def ppinned(self, ctx):
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
    async def pread(self, ctx, postID):
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
            post = self.bot.d_handler.piazza_handler.get_post(postID)
        except InvalidPostID:
            raise BadArgs("Post not found.")

        if post:
            post_embed = self.create_post_embed(post)
            await ctx.send(embed=post_embed)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def ptest(self, ctx):
        """
        `!ptest`

        **Usage:** !ptest

        **Examples:**
        `!ptest` simulates a single call of `send_pupdate` to ensure the set-up was done correctly.
        """

        await self.send_piazza_posts(False)

    @staticmethod
    def create_post_embed(post):
        if post:
            post_embed = discord.Embed(title=post["subject"], url=post["url"], description=post["num"])
            post_embed.add_field(name=post["post_type"], value=post["post_body"], inline=False)

            if post["post_type"] != "Note":
                post_embed.add_field(name=post["ans_type"], value=post["ans_body"], inline=False)

            post_embed.set_thumbnail(url=PIAZZA_THUMBNAIL_URL)

            if post["more_answers"]:
                post_embed.add_field(name=f"{post['num_answers'] - 1} more contributions hidden", value="Click the title above to access the rest of the post.", inline=False)

            post_embed.set_footer(text=f"tags: {post['tags']}")
            return post_embed

    @staticmethod
    async def send_at_time():
        # default set to midnight PST (7/8am UTC)
        today = datetime.utcnow()
        hours = round((datetime.utcnow() - datetime.now()).seconds / 3600)
        post_time = datetime(today.year, today.month, today.day, hour=hours, minute=0, tzinfo=today.tzinfo)
        time_until_post = post_time - today

        if time_until_post.total_seconds():
            await asyncio.sleep(time_until_post.total_seconds())

    @staticmethod
    async def send_pupdate(self):
        while True:
            await self.send_piazza_posts(True)

            if not self.bot.d_handler.piazza_handler:
                await asyncio.sleep(60)
            else:
                await asyncio.sleep(60 * 60 * 24)

    async def send_piazza_posts(self, wait: bool):
        if not self.bot.d_handler.piazza_handler:
            return

        posts = await self.bot.d_handler.piazza_handler.get_posts_in_range()

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

        if wait:
            # Sends at midnight if it is not called by the test function
            await self.send_at_time()

        for ch in self.bot.d_handler.piazza_handler.channels:
            channel = self.bot.get_channel(ch)
            await channel.send(response)

    @staticmethod
    async def track_inotes(self):
        while True:
            if self.bot.d_handler.piazza_handler:
                posts = await self.bot.d_handler.piazza_handler.get_recent_notes()

                if len(posts) > 1:
                    response = "Instructor Update:\n"

                    for post in posts:
                        response += f"@{post['num']}: {post['subject']} <{post['url']}>\n"

                    for chnl in self.bot.d_handler.piazza_handler.channels:
                        channel = self.bot.get_channel(chnl)
                        await channel.send(response)

                await asyncio.sleep(60 * 60 * 5)
            else:
                await asyncio.sleep(60)

    @staticmethod
    def piazza_start(self):
        if all(field in self.bot.piazza_dict for field in ("course_name", "piazza_id", "guild_id")):
            self.bot.d_handler.piazza_handler = PiazzaHandler(self.bot.piazza_dict["course_name"], self.bot.piazza_dict["piazza_id"], PIAZZA_EMAIL, PIAZZA_PASSWORD, self.bot.piazza_dict["guild_id"])

        # dict.get defaults to None so a key error is never raised
        for ch in self.bot.piazza_dict.get("channels"):
            self.bot.d_handler.piazza_handler.add_channel(int(ch))


def setup(bot):
    bot.add_cog(Piazza(bot))
