import asyncio
import copy
import operator
import os
import re
import shutil
import traceback
from datetime import datetime
from os.path import isfile
from typing import List, Optional, Union

import canvasapi
import discord
from canvasapi.module import Module, ModuleItem
from discord.ext import commands
from dotenv import load_dotenv

import util.canvas_handler
from util.badargs import BadArgs
from util.canvas_handler import CanvasHandler
from util.create_file import create_file_if_not_exists
from util.json import read_json, write_json

CANVAS_COLOR = 0xe13f2b
CANVAS_THUMBNAIL_URL = "https://lh3.googleusercontent.com/2_M-EEPXb2xTMQSTZpSUefHR3TjgOCsawM3pjVG47jI-BrHoXGhKBpdEHeLElT95060B=s180"

load_dotenv()
CANVAS_API_URL = "https://canvas.ubc.ca"
CANVAS_API_KEY = os.getenv("CANVAS_API_KEY")
CANVAS_INSTANCE = canvasapi.Canvas(CANVAS_API_URL, CANVAS_API_KEY)
CANVAS_FILE = "data/canvas.json"

# Used for updating Canvas modules
EMBED_CHAR_LIMIT = 6000
MAX_MODULE_IDENTIFIER_LENGTH = 120


class Canvas(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        if not isfile(CANVAS_FILE):
            create_file_if_not_exists(CANVAS_FILE)
            write_json({}, CANVAS_FILE)

        self.canvas_dict = read_json(CANVAS_FILE)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def track(self, ctx: commands.Context, *course_ids: str):
        """
        `!track <course IDs...>`

        Add the courses with given IDs to the list of courses being tracked. Note that you will
        only receive course updates in channels that you have typed `!live` in.
        """

        self._add_guild(ctx.message.guild)

        c_handler = self._get_canvas_handler(ctx.message.guild)

        if not isinstance(c_handler, CanvasHandler):
            raise BadArgs("Canvas Handler doesn't exist.")

        c_handler.track_course(course_ids, self.bot.notify_unpublished)

        await self.send_canvas_track_msg(c_handler, ctx)

    async def send_canvas_track_msg(self, c_handler: CanvasHandler, ctx: commands.Context) -> None:
        """
        Sends an embed to ctx that lists the Canvas courses being tracked by c_handler.
        """

        guild_dict = self.canvas_dict[str(ctx.message.guild.id)]
        guild_dict["courses"] = [str(c.id) for c in c_handler.courses]
        guild_dict["due_week"] = c_handler.due_week
        guild_dict["due_day"] = c_handler.due_day

        write_json(self.canvas_dict, "data/canvas.json")

        embed_var = self._get_tracking_courses(c_handler)
        embed_var.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=str(ctx.author.avatar_url))
        await ctx.send(embed=embed_var)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def untrack(self, ctx: commands.Context, *course_ids: str):
        """
        `!untrack <course IDs...>`

        Remove the courses with given IDs from the list of courses being tracked.
        """

        c_handler = self._get_canvas_handler(ctx.message.guild)

        if not isinstance(c_handler, CanvasHandler):
            raise BadArgs("Canvas Handler doesn't exist.")

        c_handler.untrack_course(course_ids)

        if not c_handler.courses:
            self.bot.d_handler.canvas_handlers.remove(c_handler)

        await self.send_canvas_track_msg(c_handler, ctx)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def asgn(self, ctx: commands.Context, *args: str):
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
            raise BadArgs("Canvas Handler doesn't exist.")

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
            pattern = r"\d{4}-\d{2}-\d{2}"
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
    async def live(self, ctx: commands.Context):
        """
        `!live`

        Enables course tracking for the channel the command is invoked in.
        """

        c_handler = self._get_canvas_handler(ctx.message.guild)

        if not isinstance(c_handler, CanvasHandler):
            raise BadArgs("Canvas Handler doesn't exist.")

        if ctx.message.channel not in c_handler.live_channels:
            c_handler.live_channels.append(ctx.message.channel)

            for course in c_handler.courses:
                modules_file = f"{util.canvas_handler.COURSES_DIRECTORY}/{course.id}/modules.txt"
                watchers_file = f"{util.canvas_handler.COURSES_DIRECTORY}/{course.id}/watchers.txt"
                c_handler.store_channels_in_file([ctx.message.channel], watchers_file)

                create_file_if_not_exists(modules_file)

                # Here, we will only download modules if modules_file is empty.
                if os.stat(modules_file).st_size == 0:
                    c_handler.download_modules(course, self.bot.notify_unpublished)

            self.canvas_dict[str(ctx.message.guild.id)]["live_channels"] = [channel.id for channel in c_handler.live_channels]
            write_json(self.canvas_dict, "data/canvas.json")

            await ctx.send("Added channel to live tracking.")
        else:
            await ctx.send("Channel already live tracking.")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def unlive(self, ctx: commands.Context):
        """
        `!unlive`

        Disables course tracking for the channel the command is invoked in.
        """

        c_handler = self._get_canvas_handler(ctx.message.guild)

        if not isinstance(c_handler, CanvasHandler):
            raise BadArgs("Canvas Handler doesn't exist.")

        if ctx.message.channel in c_handler.live_channels:
            c_handler.live_channels.remove(ctx.message.channel)

            self.canvas_dict[str(ctx.message.guild.id)]["live_channels"] = [channel.id for channel in c_handler.live_channels]
            write_json(self.canvas_dict, "data/canvas.json")

            for course in c_handler.courses:
                watchers_file = f"{util.canvas_handler.COURSES_DIRECTORY}/{course.id}/watchers.txt"
                c_handler.delete_channels_from_file([ctx.message.channel], watchers_file)

                # If there are no more channels watching the course, we should delete that course's directory.
                if os.stat(watchers_file).st_size == 0:
                    shutil.rmtree(f"{util.canvas_handler.COURSES_DIRECTORY}/{course.id}")

            await ctx.send("Removed channel from live tracking.")
        else:
            await ctx.send("Channel was not live tracking.")

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def annc(self, ctx: commands.Context, *args: str):
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
            raise BadArgs("Canvas Handler doesn't exist.")

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
    async def info(self, ctx: commands.Context):
        c_handler = self._get_canvas_handler(ctx.message.guild)
        await ctx.send("\n".join(str(i) for i in [c_handler.courses, c_handler.guild, c_handler.live_channels, c_handler.timings, c_handler.due_week, c_handler.due_day]))

    def _add_guild(self, guild: discord.Guild) -> None:
        if guild not in (ch.guild for ch in self.bot.d_handler.canvas_handlers):
            self.bot.d_handler.canvas_handlers.append(CanvasHandler(CANVAS_API_URL, CANVAS_API_KEY, guild))
            self.canvas_dict[str(guild.id)] = {
                "courses": [],
                "live_channels": [],
                "due_week": {},
                "due_day": {}
            }
            write_json(self.canvas_dict, "data/canvas.json")

    def _get_canvas_handler(self, guild: discord.Guild) -> Optional[CanvasHandler]:
        return next((ch for ch in self.bot.d_handler.canvas_handlers if ch.guild == guild), None)

    def _get_tracking_courses(self, c_handler: CanvasHandler) -> discord.Embed:
        course_names = c_handler.get_course_names(CANVAS_API_URL)
        embed_var = discord.Embed(title="Tracking Courses:", color=CANVAS_COLOR, timestamp=datetime.utcnow())
        embed_var.set_thumbnail(url=CANVAS_THUMBNAIL_URL)

        for c_name in course_names:
            embed_var.add_field(name=c_name[0], value=f"[Course Page]({c_name[1]})")

        return embed_var

    async def stream_tracking(self) -> None:
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
                        print(ch.timings)
                        ch.timings[str(c.id)] = data_list[0][5]

            await asyncio.sleep(30)

    async def assignment_reminder(self) -> None:
        while True:
            for ch in filter(operator.attrgetter("live_channels"), self.bot.d_handler.canvas_handlers):
                notify_role = next((r for r in ch.guild.roles if r.name.lower() == "notify"), None)

                for c in ch.courses:
                    for time in ("week", "day"):
                        data_list = ch.get_assignments(f"1-{time}", (str(c.id),), CANVAS_API_URL)

                        if time == "week":
                            recorded_ass_ids = ch.due_week[str(c.id)]
                        else:
                            recorded_ass_ids = ch.due_day[str(c.id)]

                        ass_ids = await self._assignment_sender(ch, data_list, recorded_ass_ids, notify_role, time)

                        if time == "week":
                            ch.due_week[str(c.id)] = ass_ids
                        else:
                            ch.due_day[str(c.id)] = ass_ids

                        self.canvas_dict[str(ch.guild.id)][f"due_{time}"][str(c.id)] = ass_ids

                    write_json(self.canvas_dict, "data/canvas.json")

            await asyncio.sleep(30)

    async def _assignment_sender(self, ch: CanvasHandler, data_list: List[List[str]], recorded_ass_ids: List[int], notify_role: discord.Role, time: str) -> List[str]:
        ass_ids = [data[-1] for data in data_list]
        not_recorded = tuple(data_list[i] for i, j in enumerate(ass_ids) if j not in recorded_ass_ids)

        if notify_role and not_recorded:
            for channel in ch.live_channels:
                await channel.send(notify_role.mention)

        for data in not_recorded:
            desc = data[4][:2045].rsplit(maxsplit=1)
            embed_var = discord.Embed(title=f"Due in one {time}: {data[2]}",
                                      url=data[3],
                                      description=desc[0] + "..." if desc else "[No description]",
                                      color=CANVAS_COLOR,
                                      timestamp=datetime.strptime(data[5], "%Y-%m-%d %H:%M:%S"))
            embed_var.set_author(name=data[0], url=data[1])
            embed_var.set_thumbnail(url=CANVAS_THUMBNAIL_URL)
            embed_var.add_field(name="Due at", value=data[6], inline=True)
            embed_var.set_footer(text="Created at", icon_url=CANVAS_THUMBNAIL_URL)

            for channel in ch.live_channels:
                await channel.send(embed=embed_var)

        return ass_ids

    async def update_modules(self) -> None:
        """
        Every x interval, we check Canvas modules for courses being tracked, and send information
        about new modules to Discord channels that are live tracking the courses.
        """

        await self.bot.wait_until_ready()

        while True:
            await self.check_modules()
            await asyncio.sleep(30)

    async def check_modules(self) -> None:
        """
        For every folder in handler.canvas_handler.COURSES_DIRECTORY (abbreviated as CDIR) we will:
        - get the modules for the Canvas course with ID that matches the folder name
        - compare the modules we retrieved with the modules found in CDIR/{course_id}/modules.txt
        - send the names of any new modules (i.e. modules that are not in modules.txt) to all channels
          in CDIR/{course_id}/watchers.txt
        - update CDIR/{course_id}/modules.txt with the modules we retrieved from Canvas

        NOTE: the Canvas API distinguishes between a Module and a ModuleItem. In our documentation, though,
        the word "module" can refer to both; we do not distinguish between the two types.
        """

        def get_field_value(module: Union[Module, ModuleItem]) -> str:
            """
            This function returns a string that can be added to a Discord embed as a field's value. The returned
            string contains the module's name/title attribute (depending on which one it has), as well
            as a hyperlink to the module (if the module has the html_url attribute). If the module's name/title exceeds
            MAX_MODULE_IDENTIFIER_LENGTH characters, we truncate it and append an ellipsis (...) so that the name/title
            has MAX_MODULE_IDENTIFIER_LENGTH characters.
            """

            if hasattr(module, "title"):
                field = module.title
            else:
                field = module.name

            if len(field) > MAX_MODULE_IDENTIFIER_LENGTH:
                field = f"{field[:MAX_MODULE_IDENTIFIER_LENGTH - 3]}..."

            if hasattr(module, "html_url"):
                field = f"[{field}]({module.html_url})"

            return field

        def update_embed(embed: discord.Embed, module: Union[Module, ModuleItem], embed_list: List[discord.Embed]) -> None:
            """
            Adds a field to embed containing information about given module. The field includes the module's name or
            title, as well as a hyperlink to the module if one exists.

            If the module's identifier (its name or title) has over MAX_IDENTIFIER_LENGTH characters, we truncate the
            identifier and append an ellipsis (...) so that the length does not exceed the maximum.

            The embed object that is passed in must have at most 24 fields.

            A deep copy of the embed object is appended to embed_list in two cases:
            - if adding the new field will cause the embed to exceed EMBED_CHAR_LIMIT characters in length
            - if the embed has 25 fields after adding the new field
            In both cases, we clear all of the original embed's fields after adding the embed copy to embed_list.

            NOTE: changes to embed and embed_list will persist outside this function.
            """

            field_value = get_field_value(module)

            # Note: 11 is the length of the string "Module Item"
            if 11 + len(field_value) + len(embed) > EMBED_CHAR_LIMIT:
                embed_list.append(copy.deepcopy(embed))
                embed.clear_fields()
                embed.title = f"New modules found for {course.name} (continued):"

            if isinstance(module, Module):
                embed.add_field(name="Module", value=field_value, inline=False)
            else:
                embed.add_field(name="Module Item", value=field_value, inline=False)

            if len(embed.fields) == 25:
                embed_list.append(copy.deepcopy(embed))
                embed.clear_fields()
                embed.title = f"New modules found for {course.name} (continued):"

        def write_modules(file_path: str, modules: List[Union[Module, ModuleItem]]) -> None:
            """
            Stores the ID of all modules in file with given path.
            """

            with open(file_path, "w") as f:
                for module in modules:
                    f.write(str(module.id) + "\n")

        def get_embeds(modules: List[Union[Module, ModuleItem]]) -> List[discord.Embed]:
            """
            Returns a list of Discord embeds to send to live channels.
            """

            embed = discord.Embed(title=f"New modules found for {course.name}:", color=CANVAS_COLOR)
            embed.set_thumbnail(url=CANVAS_THUMBNAIL_URL)

            embed_list = []

            for module in modules:
                update_embed(embed, module, embed_list)

            if len(embed.fields) != 0:
                embed_list.append(embed)

            return embed_list

        if os.path.exists(util.canvas_handler.COURSES_DIRECTORY):
            courses = [name for name in os.listdir(util.canvas_handler.COURSES_DIRECTORY)]

            # each folder in the courses directory is named with a course id (which is a positive integer)
            for course_id_str in courses:
                if course_id_str.isdigit():
                    course_id = int(course_id_str)

                    try:
                        course = CANVAS_INSTANCE.get_course(course_id)
                        modules_file = f"{util.canvas_handler.COURSES_DIRECTORY}/{course_id}/modules.txt"
                        watchers_file = f"{util.canvas_handler.COURSES_DIRECTORY}/{course_id}/watchers.txt"

                        create_file_if_not_exists(modules_file)
                        create_file_if_not_exists(watchers_file)

                        with open(modules_file, "r") as m:
                            existing_modules = set(m.read().splitlines())

                        all_modules = CanvasHandler.get_all_modules(course, self.bot.notify_unpublished)
                        write_modules(modules_file, all_modules)
                        differences = list(filter(lambda module: str(module.id) not in existing_modules, all_modules))

                        embeds_to_send = get_embeds(differences)

                        if embeds_to_send:
                            with open(watchers_file, "r") as w:
                                for channel_id in w:
                                    channel = self.bot.get_channel(int(channel_id.rstrip()))
                                    notify_role = next((r for r in channel.guild.roles if r.name.lower() == "notify"), None)
                                    await channel.send(notify_role.mention if notify_role else "")

                                    for element in embeds_to_send:
                                        await channel.send(embed=element)
                    except Exception:
                        print(traceback.format_exc(), flush=True)

    def canvas_init(self) -> None:
        for c_handler_guild_id in self.canvas_dict:
            guild = self.bot.guilds[[guild.id for guild in self.bot.guilds].index(int(c_handler_guild_id))]

            if guild not in (ch.guild for ch in self.bot.d_handler.canvas_handlers):
                self.bot.d_handler.canvas_handlers.append(CanvasHandler(CANVAS_API_URL, CANVAS_API_KEY, guild))

            c_handler = self._get_canvas_handler(guild)
            c_handler.track_course(tuple(self.canvas_dict[c_handler_guild_id]["courses"]), self.bot.notify_unpublished)
            live_channels_ids = self.canvas_dict[c_handler_guild_id]["live_channels"]
            live_channels = list(filter(lambda channel: channel.id in live_channels_ids, guild.text_channels))
            c_handler.live_channels = live_channels

            for due in ("due_week", "due_day"):
                for c in self.canvas_dict[c_handler_guild_id][due]:
                    if due == "due_week":
                        c_handler.due_week[c] = self.canvas_dict[c_handler_guild_id][due][c]
                    else:
                        c_handler.due_day[c] = self.canvas_dict[c_handler_guild_id][due][c]


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Canvas(bot))
