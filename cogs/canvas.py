import asyncio
import operator
import os
import re
from datetime import datetime
from typing import Optional

import discord
from discord.ext import commands
from dotenv import load_dotenv

from handlers.canvas_handler import CanvasHandler
from cogs.meta import BadArgs

CANVAS_COLOR = 0xe13f2b
CANVAS_THUMBNAIL_URL = "https://lh3.googleusercontent.com/2_M-EEPXb2xTMQSTZpSUefHR3TjgOCsawM3pjVG47jI-BrHoXGhKBpdEHeLElT95060B=s180"

load_dotenv()
CANVAS_API_URL = "https://canvas.ubc.ca"
CANVAS_API_KEY = os.getenv("CANVAS_API_KEY")


class Canvas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def track(self, ctx: commands.Context, *course_ids: str):
        self._add_guild(ctx.message.guild)

        c_handler = self._get_canvas_handler(ctx.message.guild)

        if not isinstance(c_handler, CanvasHandler):
            raise BadArgs("Canvas Handler doesn't exist.", False, ctx.command)

        c_handler.track_course(course_ids)

        await self.send_canvas_track_msg(c_handler, ctx)

    async def send_canvas_track_msg(self, c_handler, ctx):
        self.bot.canvas_dict[str(ctx.message.guild.id)]["courses"] = [str(c.id) for c in c_handler.courses]
        self.bot.writeJSON(self.bot.canvas_dict, "data/canvas.json")

        embed_var = self._get_tracking_courses(c_handler, CANVAS_API_URL)
        embed_var.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=str(ctx.author.avatar_url))
        await ctx.send(embed=embed_var)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def untrack(self, ctx: commands.Context, *course_ids: str):
        c_handler = self._get_canvas_handler(ctx.message.guild)

        if not isinstance(c_handler, CanvasHandler):
            raise BadArgs("Canvas Handler doesn't exist.", False, ctx.command)

        c_handler.untrack_course(course_ids)

        if not c_handler.courses:
            self.bot.d_handler.canvas_handlers.remove(c_handler)

        await self.send_canvas_track_msg(c_handler, ctx)

    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def asgn(self, ctx: commands.Context, *args):
        """
        `!asgn ( | (-due (n-(hour|day|week|month|year)) | YYYY-MM-DD | YYYY-MM-DD-HH:MM:SS) | -all)`

        Argument can be left blank for sending assignments due 2 weeks from now.

        *Filter till due date:*

        `!asgn -due` can be in time from now e.g.: `-due 4-hour` or all assignments before a certain date e.g.: `-due 2020-10-21`

        *All assignments:*

        `!asgn -all` returns ALL assignments.
        """

        c_handler = self._get_canvas_handler(ctx.message.guild)

        if not isinstance(c_handler, CanvasHandler):
            raise BadArgs("Canvas Handler doesn't exist.", False, ctx.command)

        if args and args[0].startswith("-due"):
            due = args[1]
            course_ids = args[2:]
        elif args and args[0].startswith("-all"):
            due = None
            course_ids = args[1:]
        else:
            due = "2-week"
            course_ids = args

        assignments = c_handler.get_assignments(due, course_ids, CANVAS_API_URL)

        if not assignments:
            pattern = r'\d{4}-\d{2}-\d{2}'
            return await ctx.send(f"No assignments due by {due}{' (at 00:00)' if re.match(pattern, due) else ''}.")

        for data in assignments:
            embed_var = discord.Embed(title=data[2], url=data[3], description=data[4], color=CANVAS_COLOR, timestamp=datetime.strptime(data[5], "%Y-%m-%d %H:%M:%S"))
            embed_var.set_author(name=data[0], url=data[1])
            embed_var.set_thumbnail(url=CANVAS_THUMBNAIL_URL)
            embed_var.add_field(name="Due at", value=data[6], inline=True)
            embed_var.set_footer(text="Created at", icon_url=CANVAS_THUMBNAIL_URL)
            await ctx.send(embed=embed_var)

    @commands.command(hidden=True)
    @commands.is_owner()
    @commands.guild_only()
    async def live(self, ctx: commands.Context):
        c_handler = self._get_canvas_handler(ctx.message.guild)

        if not isinstance(c_handler, CanvasHandler):
            raise BadArgs("Canvas Handler doesn't exist.", False, ctx.command)

        if ctx.message.channel not in c_handler.live_channels:
            c_handler.live_channels.append(ctx.message.channel)

            self.bot.canvas_dict[str(ctx.message.guild.id)]["live_channels"] = [channel.id for channel in c_handler.live_channels]
            self.bot.writeJSON(self.bot.canvas_dict, "data/canvas.json")

            await ctx.send("Added channel to live tracking.")
        else:
            await ctx.send("Channel already live tracking.")

    @commands.command(hidden=True)
    @commands.is_owner()
    @commands.guild_only()
    async def unlive(self, ctx: commands.Context):
        c_handler = self._get_canvas_handler(ctx.message.guild)

        if not isinstance(c_handler, CanvasHandler):
            raise BadArgs("Canvas Handler doesn't exist.", False, ctx.command)

        if ctx.message.channel in c_handler.live_channels:
            c_handler.live_channels.remove(ctx.message.channel)

            self.bot.canvas_dict[str(ctx.message.guild.id)]["live_channels"] = [channel.id for channel in c_handler.live_channels]
            self.bot.writeJSON(self.bot.canvas_dict, "data/canvas.json")

            await ctx.send("Removed channel from live tracking.")
        else:
            await ctx.send("Channel was not live tracking.")

    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def annc(self, ctx: commands.Context, *args):
        """
        `!annc ( | (-since (n-(hour|day|week|month|year)) | YYYY-MM-DD | YYYY-MM-DD-HH:MM:SS) | -all)`

        Argument can be left blank for sending announcements from 2 weeks ago to now.

        *Filter since announcement date:*

        `!annc -since` can be in time from now e.g.: `-since 4-hour` or all announcements after a certain date e.g.: `-since 2020-10-21`

        *All announcements:*

        `!annc -all` returns ALL announcements.
        """

        c_handler = self._get_canvas_handler(ctx.message.guild)

        if not isinstance(c_handler, CanvasHandler):
            raise BadArgs("Canvas Handler doesn't exist.", False, ctx.command)

        if args and args[0].startswith("-since"):
            since = args[1]
            course_ids = args[2:]
        elif args and args[0].startswith("-all"):
            since = None
            course_ids = args[1:]
        else:
            since = "2-week"
            course_ids = args

        for data in c_handler.get_course_stream_ch(since, course_ids, CANVAS_API_URL, CANVAS_API_KEY):
            embed_var = discord.Embed(title=data[2], url=data[3], description=data[4], color=CANVAS_COLOR)
            embed_var.set_author(name=data[0], url=data[1])
            embed_var.set_thumbnail(url=CANVAS_THUMBNAIL_URL)
            embed_var.add_field(name="Created at", value=data[5], inline=True)
            await ctx.send(embed=embed_var)

    @commands.command(hidden=True)
    @commands.is_owner()
    @commands.guild_only()
    async def info(self, ctx):
        c_handler = self._get_canvas_handler(ctx.message.guild)
        await ctx.send("\n".join(str(i) for i in [c_handler.courses, c_handler.guild, c_handler.live_channels, c_handler.timings, c_handler.due_week, c_handler.due_day]))

    def _add_guild(self, guild: discord.Guild):
        if guild not in (ch.guild for ch in self.bot.d_handler.canvas_handlers):
            self.bot.d_handler.canvas_handlers.append(CanvasHandler(CANVAS_API_URL, "", guild))
            self.bot.canvas_dict[str(guild.id)] = {
                "courses"      : [],
                "live_channels": [],
                "due_week"     : {},
                "due_day"      : {}
            }
            self.bot.writeJSON(self.bot.canvas_dict, "data/canvas.json")

    def _get_canvas_handler(self, guild: discord.Guild) -> Optional[CanvasHandler]:
        return next((ch for ch in self.bot.d_handler.canvas_handlers if ch.guild == guild), None)

    @staticmethod
    def _get_tracking_courses(c_handler: CanvasHandler, CANVAS_API_URL) -> discord.Embed:
        course_names = c_handler.get_course_names(CANVAS_API_URL)
        embed_var = discord.Embed(title="Tracking Courses:", color=CANVAS_COLOR, timestamp=datetime.utcnow())
        embed_var.set_thumbnail(url=CANVAS_THUMBNAIL_URL)

        for c_name in course_names:
            embed_var.add_field(name=c_name[0], value=f"[Course Page]({c_name[1]})")

        return embed_var

    @staticmethod
    async def stream_tracking(self):
        while True:
            for ch in filter(operator.attrgetter("live_channels"), self.bot.d_handler.canvas_handlers):
                notify_role = next((r for r in ch.guild.roles if r.name.lower() == "notify"), None)

                for c in ch.courses:
                    since = ch.timings[str(c.id)]
                    since = re.sub(r"\s", "-", since)
                    data_list = ch.get_course_stream_ch(since, (str(c.id),), CANVAS_API_URL, CANVAS_API_KEY)

                    for data in data_list:
                        embed_var = discord.Embed(title=data[2], url=data[3], description=data[4], color=CANVAS_COLOR)
                        embed_var.set_author(name=data[0], url=data[1])
                        embed_var.set_thumbnail(url=CANVAS_THUMBNAIL_URL)
                        embed_var.add_field(name="Created at", value=data[5], inline=True)

                        for channel in ch.live_channels:
                            await channel.send(notify_role.mention if notify_role else "", embed=embed_var)

                    if data_list:
                        # latest announcement first
                        ch.timings[str(c.id)] = data_list[0][5]

            await asyncio.sleep(3600)

    @staticmethod
    async def assignment_reminder(self):
        while True:
            for ch in filter(operator.attrgetter("live_channels"), self.bot.d_handler.canvas_handlers):
                notify_role = next((r for r in ch.guild.roles if r.name.lower() == "notify"), None)

                for c in ch.courses:
                    for time in ("week", "day"):
                        data_list = ch.get_assignments(f"1-{time}", (str(c.id),), CANVAS_API_URL)
                        recorded_ass_ids = ch.due_week[str(c.id)]
                        ass_ids = await self._assignment_sender(ch, data_list, recorded_ass_ids, notify_role, time)
                        ch.due_week[str(c.id)] = ass_ids
                        self.bot.canvas_dict[str(ch.guild.id)][f"due_{time}"][str(c.id)] = ass_ids

                    self.bot.writeJSON(self.bot.canvas_dict, "data/canvas.json")

            await asyncio.sleep(3600)

    @staticmethod
    async def _assignment_sender(ch, data_list, recorded_ass_ids, notify_role, time):
        ass_ids = [data[-1] for data in data_list]
        not_recorded = tuple(data_list[i] for i, j in enumerate(ass_ids) if j not in recorded_ass_ids)

        if notify_role and not_recorded:
            for channel in ch.live_channels:
                await channel.send(notify_role.mention)

        for data in not_recorded:
            embed_var = discord.Embed(title=f"Due in one {time}: {data[2]}", url=data[3], description=data[4], color=CANVAS_COLOR, timestamp=datetime.strptime(data[5], "%Y-%m-%d %H:%M:%S"))
            embed_var.set_author(name=data[0], url=data[1])
            embed_var.set_thumbnail(url=CANVAS_THUMBNAIL_URL)
            embed_var.add_field(name="Due at", value=data[6], inline=True)
            embed_var.set_footer(text="Created at", icon_url=CANVAS_THUMBNAIL_URL)

            for channel in ch.live_channels:
                await channel.send(embed=embed_var)

        return ass_ids

    @staticmethod
    def canvas_init(self):
        for c_handler_guild_id in self.bot.canvas_dict:
            guild = self.bot.guilds[[guild.id for guild in self.bot.guilds].index(int(c_handler_guild_id))]

            if guild not in (ch.guild for ch in self.bot.d_handler.canvas_handlers):
                self.bot.d_handler.canvas_handlers.append(CanvasHandler(CANVAS_API_URL, "", guild))

            c_handler = self._get_canvas_handler(guild)
            c_handler.track_course(tuple(self.bot.canvas_dict[c_handler_guild_id]["courses"]))
            live_channels_ids = self.bot.canvas_dict[c_handler_guild_id]["live_channels"]
            live_channels = list(filter(live_channels_ids.__contains__, guild.text_channels))
            c_handler.live_channels = live_channels

            for due in ("due_week", "due_day"):
                for c in self.bot.canvas_dict[c_handler_guild_id][due]:
                    c_handler.due_week[c] = self.bot.canvas_dict[c_handler_guild_id][due][c]


def setup(bot):
    bot.add_cog(Canvas(bot))
