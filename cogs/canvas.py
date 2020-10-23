import asyncio
import operator
import os
import re
from datetime import datetime
from typing import Optional, Union, List, Tuple, TextIO
import traceback
import shutil

import discord
from discord.ext import commands
from dotenv import load_dotenv
import canvasapi
from canvasapi.module import Module
from canvasapi.module import ModuleItem

import handlers.canvas_handler
from cogs.meta import BadArgs
from handlers.canvas_handler import CanvasHandler
import util

CANVAS_COLOR = 0xe13f2b
CANVAS_THUMBNAIL_URL = "https://lh3.googleusercontent.com/2_M-EEPXb2xTMQSTZpSUefHR3TjgOCsawM3pjVG47jI-BrHoXGhKBpdEHeLElT95060B=s180"

load_dotenv()
CANVAS_API_URL = "https://canvas.ubc.ca"
CANVAS_API_KEY = os.getenv("CANVAS_API_KEY")

# Used for updating Canvas modules
CANVAS_INSTANCE = canvasapi.Canvas(CANVAS_API_URL, CANVAS_API_KEY)
EMBED_CHAR_LIMIT = 6000
MAX_MODULE_IDENTIFIER_LENGTH = 120

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
            raise BadArgs("Canvas Handler doesn't exist.")

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
            raise BadArgs("Canvas Handler doesn't exist.")

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
            raise BadArgs("Canvas Handler doesn't exist.")

        if ctx.message.channel not in c_handler.live_channels:
            c_handler.live_channels.append(ctx.message.channel)

            for course in c_handler.courses:
                watchers_file = f'{handlers.canvas_handler.COURSES_DIRECTORY}/{course.id}/watchers.txt'
                CanvasHandler.store_channels_in_file([ctx.message.channel], watchers_file)

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
            raise BadArgs("Canvas Handler doesn't exist.")

        if ctx.message.channel in c_handler.live_channels:
            c_handler.live_channels.remove(ctx.message.channel)

            self.bot.canvas_dict[str(ctx.message.guild.id)]["live_channels"] = [channel.id for channel in c_handler.live_channels]
            self.bot.writeJSON(self.bot.canvas_dict, "data/canvas.json")

            for course in c_handler.courses:
                watchers_file = f'{handlers.canvas_handler.COURSES_DIRECTORY}/{course.id}/watchers.txt'
                CanvasHandler.delete_channels_from_file([ctx.message.channel], watchers_file)

                # If there are no more channels watching the course, we should delete that course's directory.
                if os.stat(watchers_file).st_size == 0:
                    shutil.rmtree(f'{handlers.canvas_handler.COURSES_DIRECTORY}/{course.id}')

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

    async def update_modules_hourly(self):
        """
        Every hour, we check Canvas modules for courses being tracked, and send information
        about new modules to Discord channels that are live tracking the courses.
        """
        await self.bot.wait_until_ready()
        while True:
            await self.check_modules()
            await asyncio.sleep(3600)

    async def check_modules(self):
        """
        For every folder in handler.canvas_handler.COURSES_DIRECTORY (abbreviated as CDIR) we will:
        - get the modules for the Canvas course with ID that matches the folder name
        - compare the modules we retrieved with the modules found in CDIR/{course_id}/modules.txt
        - send the names of any modules not in the file to all channels in CDIR/{course_id}/watchers.txt
        - update CDIR/{course_id}/modules.txt with the modules we retrieved from Canvas
        """
        
        def get_field_value(module: Union[Module, ModuleItem]) -> str:
            """
            This function returns a string that can be added to a Discord embed as a field's value. The returned
            string contains the module's name/title attribute (depending on which one it has), as well
            as a hyperlink to the module (if the module has the html_url attribute). If the module's name/title exceeds 
            MAX_MODULE_IDENTIFIER_LENGTH characters, we truncate it and append an ellipsis (...) so that the name/title has 
            MAX_MODULE_IDENTIFIER_LENGTH characters.
            """
            if hasattr(module, 'title'):
                field = module.title
            else:
                field = module.name
            
            if len(field) > MAX_MODULE_IDENTIFIER_LENGTH:
                field = f'{field[:MAX_MODULE_IDENTIFIER_LENGTH - 3]}...'

            if hasattr(module, 'html_url'):
                field = f'[{field}]({module.html_url})'
            
            return field
        
        def update_embed(embed: discord.Embed, module: Union[Module, ModuleItem], 
                         num_fields: int, embed_list: List[discord.Embed]) -> Tuple[discord.Embed, int]:
            """
            Adds a field to embed containing information about given module. The field includes the module's name or title,
            as well as a hyperlink to the module if one exists.

            If the module's identifier (its name or title) has over MAX_MODULE_IDENTIFIER_LENGTH characters, we truncate the identifier
            and append an ellipsis (...) so that it has MAX_MODULE_IDENTIFIER_LENGTH characters.

            The embed object that is passed in must have at most 24 fields. Use the parameter `num_fields` to specify the number 
            of fields the embed object has.

            The embed object is appended to embed_list in two cases:
            - if adding the new field will cause the embed to exceed EMBED_CHAR_LIMIT characters in length, the embed is appended to embed_list first. 
                Then, we create a new embed and add the field to the new embed.
            - if the embed has 25 fields after adding the new field, we append embed to embed_list.

            Note that Python stores references in lists -- hence, modifying the content of the embed variable after calling
            this function will modify embed_list if embed was added to embed_list.

            This function returns a tuple (embed, num_fields) containing the updated values of embed and num_fields.
            
            NOTE: changes to embed_list will persist outside this function, but changes to embed and num_fields 
            may not be reflected outside this function. The caller should update (reassign) the values that were passed 
            in to embed and num_fields using the tuple returned by this function. A reassignment of embed will not
            change the contents of embed_list.
            """
            field_value = get_field_value(module)
            
            # Note: 11 is the length of the string "Module Item"
            if 11 + len(field_value) + len(embed) > EMBED_CHAR_LIMIT:
                embed_list.append(embed)
                embed = discord.Embed(title=f"New modules for {course.name} (continued):", color=CANVAS_COLOR)
                num_fields = 0
            
            if isinstance(module, canvasapi.module.Module):
                embed.add_field(name="Module", value=field_value, inline=False)
            else:
                embed.add_field(name="Module Item", value=field_value, inline=False)

            num_fields += 1

            if num_fields == 25:
                embed_list.append(embed)
                embed = discord.Embed(title=f"New modules for {course.name} (continued):", color=CANVAS_COLOR)
                num_fields = 0
            
            return (embed, num_fields)
        
        def handle_module(module: Union[Module, ModuleItem], modules_file: TextIO, existing_modules: List[str], 
                          curr_embed: discord.Embed, curr_embed_num_fields: int, 
                          embed_list: List[discord.Embed]) -> Tuple[discord.Embed, int]:
            """
            Writes given module or module item to modules_file. This function assumes that:
            - modules_file has already been opened in write/append mode.
            - module has the "name" attribute if it is an instance of canvasapi.module.Module.
            - module has the "html_url" attribute or the "title" attribute if it is an instance of canvasapi.module.ModuleItem.

            existing_modules contains contents of the pre-existing modules file (or is empty if the modules file has just been created)

            This function updates curr_embed, curr_embed_num_fields, and embed_list depending on whether existing_modules already
            knows about the given module item. 
            
            The function returns a tuple (curr_embed, curr_embed_num_fields) containing the updated values of curr_embed and curr_embed_num_fields.
            
            NOTE: changes to embed_list will persist outside this function, but changes to curr_embed and curr_embed_num_fields may not be 
            reflected outside this function. The caller should update the values that were passed in to curr_embed and curr_embed_num_fields 
            using the tuple returned by this function.
            """
            if isinstance(module, canvasapi.module.Module):
                to_write = module.name + '\n'
            else:
                if hasattr(module, 'html_url'):
                    to_write = module.html_url + '\n'
                else:
                    to_write = module.title + '\n'
                
            modules_file.write(to_write)

            if not to_write in existing_modules:
                embed_num_fields_tuple = update_embed(curr_embed, module, curr_embed_num_fields, embed_list)
                curr_embed = embed_num_fields_tuple[0]
                curr_embed_num_fields = embed_num_fields_tuple[1]
            
            return (curr_embed, curr_embed_num_fields)

        if (os.path.exists(handlers.canvas_handler.COURSES_DIRECTORY)):
            courses = [name for name in os.listdir(handlers.canvas_handler.COURSES_DIRECTORY)]

            # each folder in the courses directory is named with a course id (which is a positive integer)
            for course_id_str in courses:
                if course_id_str.isdigit():
                    course_id = int(course_id_str)
                    try:
                        course = CANVAS_INSTANCE.get_course(course_id)
                        modules_file = f'{handlers.canvas_handler.COURSES_DIRECTORY}/{course_id}/modules.txt'
                        watchers_file = f'{handlers.canvas_handler.COURSES_DIRECTORY}/{course_id}/watchers.txt'
                        
                        print(f'Downloading modules for {course.name}', flush=True)

                        util.create_file_if_not_exists(modules_file)
                        util.create_file_if_not_exists(watchers_file)

                        with open(modules_file, 'r') as m:
                            existing_modules = set(m.readlines())
                        
                        embeds_to_send = []

                        curr_embed = discord.Embed(title=f"New modules found for {course.name}:", color=CANVAS_COLOR)
                        curr_embed.set_thumbnail(url=CANVAS_THUMBNAIL_URL)
                        curr_num_fields = 0

                        with open(modules_file, 'w') as m:
                            for module in course.get_modules():
                                if hasattr(module, 'name'):
                                    embed_num_fields_tuple = handle_module(module, m, existing_modules, curr_embed, curr_num_fields, embeds_to_send)
                                    curr_embed = embed_num_fields_tuple[0]
                                    curr_num_fields = embed_num_fields_tuple[1]
                                    
                                    for item in module.get_module_items():
                                        if hasattr(item, 'title'):
                                            embed_num_fields_tuple = handle_module(item, m, existing_modules, curr_embed, curr_num_fields, embeds_to_send)
                                            curr_embed = embed_num_fields_tuple[0]
                                            curr_num_fields = embed_num_fields_tuple[1]
                        
                        if curr_num_fields:
                            embeds_to_send.append(curr_embed)
                        
                        if embeds_to_send:
                            with open(watchers_file, 'r') as w:
                                for channel_id in w:
                                    channel = self.bot.get_channel(int(channel_id.rstrip()))
                                    notify_role = next((r for r in channel.guild.roles if r.name.lower() == "notify"), None)
                                    for element in embeds_to_send:
                                        await channel.send(notify_role.mention if notify_role else "", embed=element)

                    except Exception:
                        print(traceback.format_exc(), flush=True)


    @staticmethod
    def canvas_init(self):
        for c_handler_guild_id in self.bot.canvas_dict:
            guild = self.bot.guilds[[guild.id for guild in self.bot.guilds].index(int(c_handler_guild_id))]

            if guild not in (ch.guild for ch in self.bot.d_handler.canvas_handlers):
                self.bot.d_handler.canvas_handlers.append(CanvasHandler(CANVAS_API_URL, "", guild))

            c_handler = self._get_canvas_handler(guild)
            c_handler.track_course(tuple(self.bot.canvas_dict[c_handler_guild_id]["courses"]))
            live_channels_ids = self.bot.canvas_dict[c_handler_guild_id]["live_channels"]
            live_channels = list(filter(lambda channel: channel.id in live_channels_ids, guild.text_channels))
            c_handler.live_channels = live_channels

            for due in ("due_week", "due_day"):
                for c in self.bot.canvas_dict[c_handler_guild_id][due]:
                    c_handler.due_week[c] = self.bot.canvas_dict[c_handler_guild_id][due][c]


def setup(bot):
    bot.add_cog(Canvas(bot))
