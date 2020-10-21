import ast
import asyncio
import mimetypes
import operator
import os
import random
import re
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from io import BytesIO
from typing import Optional

import discord
import pytz
import requests
import webcolors
from discord.ext import commands
from dotenv import load_dotenv
from googletrans import Translator, constants

from canvas_handler import CanvasHandler
from discord_handler import DiscordHandler
from piazza_handler import PiazzaHandler, InvalidPostID

CANVAS_COLOR = 0xe13f2b
CANVAS_THUMBNAIL_URL = "https://lh3.googleusercontent.com/2_M-EEPXb2xTMQSTZpSUefHR3TjgOCsawM3pjVG47jI-BrHoXGhKBpdEHeLElT95060B=s180"
PIAZZA_THUMBNAIL_URL = "https://store-images.s-microsoft.com/image/apps.25584.554ac7a6-231b-46e2-9960-a059f3147dbe.727eba5c-763a-473f-981d-ffba9c91adab.4e76ea6a-bd74-487f-bf57-3612e43ca795.png"

load_dotenv()
CANVAS_API_URL = "https://canvas.ubc.ca"
CANVAS_API_KEY = os.getenv("CANVAS_API_KEY")
PIAZZA_EMAIL = os.getenv("PIAZZA_EMAIL")
PIAZZA_PASSWORD = os.getenv("PIAZZA_PASSWORD")

#################### COMMANDS ####################


class Main(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.add_instructor_role_counter = 0
        self.d_handler = DiscordHandler()

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def colour(self, ctx):
        """
        `!colour` __`Colour info`__

        **Usage:** !colour [colour]

        **Examples:**
        `!colour` returns info of random colour
        `!colour #ffffff` returns info of colour white
        `!colour rgb(0, 0, 0)` returns info of colour black
        `!colour hsl(0, 100%, 50%)` returns info of colour red
        `!colour cmyk(100%, 0%, 0%, 0%)` returns info of colour cyan
        `!colour blue` returns info of colour blue

        percent signs are optional
        """

        def RGB_to_HSL(r, g, b):
            r /= 255
            g /= 255
            b /= 255
            c_max = max(r, g, b)
            c_min = min(r, g, b)
            delta = c_max - c_min
            l = (c_max + c_min) / 2

            if not delta:
                h = 0
                s = 0
            else:
                s = delta / (1 - abs(2 * l - 1))
                if c_max == r:
                    h = 60 * (((g - b) / delta) % 6)
                elif c_max == g:
                    h = 60 * ((b - r) / delta + 2)
                else:
                    h = 60 * ((r - g) / delta + 4)

            s *= 100
            l *= 100
            return h, s, l

        def HSL_to_RGB(h, s, l):
            h %= 360
            s /= 100
            l /= 100
            c = (1 - abs(2 * l - 1)) * s
            x = c * (1 - abs((h / 60) % 2 - 1))
            m = l - c / 2

            if 0 <= h < 60:
                temp = [c, x, 0]
            elif 60 <= h < 120:
                temp = [x, c, 0]
            elif 120 <= h < 180:
                temp = [0, c, x]
            elif 180 <= h < 240:
                temp = [0, x, c]
            elif 240 <= h < 300:
                temp = [x, 0, c]
            else:
                temp = [c, 0, x]

            return (temp[0] + m) * 255, (temp[1] + m) * 255, (temp[2] + m) * 255

        def RGB_to_CMYK(r, g, b):
            if (r, g, b) == (0, 0, 0):
                return 0, 0, 0, 100

            r /= 255
            g /= 255
            b /= 255
            k = 1 - max(r, g, b)
            c = (1 - r - k) / (1 - k)
            m = (1 - g - k) / (1 - k)
            y = (1 - b - k) / (1 - k)
            c *= 100
            m *= 100
            y *= 100
            k *= 100
            return c, m, y, k

        def CMYK_to_RGB(c, m, y, k):
            c /= 100
            m /= 100
            y /= 100
            k /= 100
            r = 255 * (1 - c) * (1 - k)
            g = 255 * (1 - m) * (1 - k)
            b = 255 * (1 - y) * (1 - k)
            return r, g, b

        def RGB_to_HEX(r, g, b):
            return hex(r * 16 ** 4 + g * 16 ** 2 + b)[2:].zfill(6)

        def closest_colour(requested_colour):
            min_colours = {}

            for key, name in webcolors.CSS3_HEX_TO_NAMES.items():
                r_c, g_c, b_c = webcolors.hex_to_rgb(key)
                rd = (r_c - requested_colour[0]) ** 2
                gd = (g_c - requested_colour[1]) ** 2
                bd = (b_c - requested_colour[2]) ** 2
                min_colours[(rd + gd + bd)] = name

            return min_colours[min(min_colours.keys())]

        def get_colour_name(requested_colour):
            try:
                closest_name = actual_name = webcolors.rgb_to_name(requested_colour)
            except ValueError:
                closest_name = closest_colour(requested_colour)
                actual_name = None

            return actual_name, closest_name

        css = {"lightsalmon": "0xFFA07A", "salmon": "0xFA8072", "darksalmon": "0xE9967A", "lightcoral": "0xF08080", "indianred": "0xCD5C5C", "crimson": "0xDC143C", "firebrick": "0xB22222", "red": "0xFF0000", "darkred": "0x8B0000", "coral": "0xFF7F50", "tomato": "0xFF6347", "orangered": "0xFF4500", "gold": "0xFFD700", "orange": "0xFFA500", "darkorange": "0xFF8C00", "lightyellow": "0xFFFFE0", "lemonchiffon": "0xFFFACD", "lightgoldenrodyellow": "0xFAFAD2", "papayawhip": "0xFFEFD5", "moccasin": "0xFFE4B5", "peachpuff": "0xFFDAB9", "palegoldenrod": "0xEEE8AA", "khaki": "0xF0E68C", "darkkhaki": "0xBDB76B", "yellow": "0xFFFF00", "lawngreen": "0x7CFC00", "chartreuse": "0x7FFF00", "limegreen": "0x32CD32", "lime": "0x00FF00", "forestgreen": "0x228B22", "green": "0x008000", "darkgreen": "0x006400", "greenyellow": "0xADFF2F", "yellowgreen": "0x9ACD32", "springgreen": "0x00FF7F", "mediumspringgreen": "0x00FA9A", "lightgreen": "0x90EE90", "palegreen": "0x98FB98", "darkseagreen": "0x8FBC8F", "mediumseagreen": "0x3CB371", "seagreen": "0x2E8B57", "olive": "0x808000", "darkolivegreen": "0x556B2F", "olivedrab": "0x6B8E23", "lightcyan": "0xE0FFFF", "cyan": "0x00FFFF", "aqua": "0x00FFFF", "aquamarine": "0x7FFFD4", "mediumaquamarine": "0x66CDAA", "paleturquoise": "0xAFEEEE", "turquoise": "0x40E0D0", "mediumturquoise": "0x48D1CC", "darkturquoise": "0x00CED1", "lightseagreen": "0x20B2AA", "cadetblue": "0x5F9EA0", "darkcyan": "0x008B8B", "teal": "0x008080", "powderblue": "0xB0E0E6", "lightblue": "0xADD8E6", "lightskyblue": "0x87CEFA", "skyblue": "0x87CEEB", "deepskyblue": "0x00BFFF", "lightsteelblue": "0xB0C4DE", "dodgerblue": "0x1E90FF", "cornflowerblue": "0x6495ED", "steelblue": "0x4682B4", "royalblue": "0x4169E1", "blue": "0x0000FF", "mediumblue": "0x0000CD", "darkblue": "0x00008B", "navy": "0x000080", "midnightblue": "0x191970", "mediumslateblue": "0x7B68EE", "slateblue": "0x6A5ACD", "darkslateblue": "0x483D8B", "lavender": "0xE6E6FA", "thistle": "0xD8BFD8", "plum": "0xDDA0DD", "violet": "0xEE82EE", "orchid": "0xDA70D6", "fuchsia": "0xFF00FF", "magenta": "0xFF00FF", "mediumorchid": "0xBA55D3", "mediumpurple": "0x9370DB", "blueviolet": "0x8A2BE2", "darkviolet": "0x9400D3", "darkorchid": "0x9932CC", "darkmagenta": "0x8B008B", "purple": "0x800080", "indigo": "0x4B0082", "pink": "0xFFC0CB", "lightpink": "0xFFB6C1", "hotpink": "0xFF69B4", "deeppink": "0xFF1493", "palevioletred": "0xDB7093", "mediumvioletred": "0xC71585", "white": "0xFFFFFF", "snow": "0xFFFAFA", "honeydew": "0xF0FFF0", "mintcream": "0xF5FFFA", "azure": "0xF0FFFF", "aliceblue": "0xF0F8FF", "ghostwhite": "0xF8F8FF", "whitesmoke": "0xF5F5F5", "seashell": "0xFFF5EE", "beige": "0xF5F5DC", "oldlace": "0xFDF5E6", "floralwhite": "0xFFFAF0", "ivory": "0xFFFFF0", "antiquewhite": "0xFAEBD7", "linen": "0xFAF0E6", "lavenderblush": "0xFFF0F5", "mistyrose": "0xFFE4E1", "gainsboro": "0xDCDCDC", "lightgray": "0xD3D3D3", "silver": "0xC0C0C0", "darkgray": "0xA9A9A9", "gray": "0x808080", "dimgray": "0x696969", "lightslategray": "0x778899", "slategray": "0x708090", "darkslategray": "0x2F4F4F", "black": "0x000000", "cornsilk": "0xFFF8DC", "blanchedalmond": "0xFFEBCD", "bisque": "0xFFE4C4", "navajowhite": "0xFFDEAD", "wheat": "0xF5DEB3", "burlywood": "0xDEB887", "tan": "0xD2B48C", "rosybrown": "0xBC8F8F", "sandybrown": "0xF4A460", "goldenrod": "0xDAA520", "peru": "0xCD853F", "chocolate": "0xD2691E", "saddlebrown": "0x8B4513", "sienna": "0xA0522D", "brown": "0xA52A2A", "maroon": "0x800000"}

        def color_embed(colour, r, g, b, c, m, y, k, h, s, l):
            Hex = f"#{RGB_to_HEX(r, g, b)}"
            rgb = f"rgb({r},{g},{b})"
            hsl = f"hsl({round(float(h), 2)},{round(float(s), 2)}%,{round(float(l), 2)}%)"
            cmyk = f"cmyk({round(float(c), 2)}%,{round(float(m), 2)}%,{round(float(y), 2)}%,{round(float(k), 2)}%)"
            css_code = get_colour_name((r, g, b))[1]
            embed = discord.Embed(title=colour, description="", colour=int(Hex[1:], 16))
            embed.add_field(name="Hex", value=Hex, inline=True)
            embed.add_field(name="RGB", value=rgb, inline=True)
            embed.add_field(name="HSL", value=hsl, inline=True)
            embed.add_field(name="CMYK", value=cmyk, inline=True)
            embed.add_field(name="CSS", value=css_code, inline=True)
            embed.set_thumbnail(url=f"https://serux.pro/rendercolour/?rgb={r},{g},{b}")
            return embed

        def RGB(r, g, b, colour):
            h, s, l = RGB_to_HSL(r, g, b)
            c, m, y, k = RGB_to_CMYK(r, g, b)
            return color_embed(colour, r, g, b, c, m, y, k, h, s, l)

        def hslRGB(h, s, l, colour):
            h -= (h // 360) * 360
            r, g, b = HSL_to_RGB(h, s, l)
            c, m, y, k = RGB_to_CMYK(r, g, b)
            r = round(r)
            g = round(g)
            b = round(b)
            return color_embed(colour, 
                               , c, m, y, k, h, s, l)

        def cmykRGB(c, m, y, k, colour):
            r, g, b = CMYK_to_RGB(c, m, y, k)
            h, s, l = RGB_to_HSL(r, g, b)
            r = round(r)
            g = round(g)
            b = round(b)
            return color_embed(colour, r, g, b, c, m, y, k, h, s, l)

        def cssRGB(colour):
            r = int(css[colour][2:4], 16)
            g = int(css[colour][4:6], 16)
            b = int(css[colour][6:], 16)
            h, s, l = RGB_to_HSL(r, g, b)
            c, m, y, k = RGB_to_CMYK(r, g, b)
            return color_embed(colour, r, g, b, c, m, y, k, h, s, l)

        colour = ctx.message.content[len(self.bot.command_prefix) + 7:]

        if not colour:
            await ctx.send(embed=RGB(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), "Random Colour"))
        elif c_str := re.search(r"#([0-9A-Fa-f]{3}){1,2}", colour):
            c_str = c_str.group()
            if len(c_str) == 7:
                await ctx.send(embed=RGB(int(c_str[1:3], 16), int(c_str[3:5], 16), int(c_str[5:], 16), c_str))
            elif len(c_str) == 4:
                await ctx.send(embed=RGB(int(c_str[1] * 2, 16), int(c_str[2] * 2, 16), int(c_str[3] * 2, 16), c_str))
        elif c_str := re.search(r"([0-9A-Fa-f]{3}){1,2}", colour):
            c_str = c_str.group()
            if len(c_str) == 6:
                await ctx.send(embed=RGB(int(c_str[:2], 16), int(c_str[2:4], 16), int(c_str[4:], 16), c_str))
            elif len(c_str) == 3:
                await ctx.send(embed=RGB(int(c_str[0] * 2, 16), int(c_str[1] * 2, 16), int(c_str[2] * 2, 16), c_str))
        elif c_str := re.search(r"rgb\((\d{1,3}), *(\d{1,3}), *(\d{1,3})\)", colour):
            r, g, b = map(int, c_str.group(1, 2, 3))
            if max(r, g, b) > 255 or min(r, g, b) < 0:
                return await ctx.send("You inputted an invalid colour. Please try again.", delete_after=5)
            await ctx.send(embed=RGB(r, g, b, c_str))
        elif c_str := re.search(r"hsl\((\d{1,3}(?:\.\d*)?), *(\d{1,3}(?:\.\d*)?)%?, *(\d{1,3}(?:\.\d*)?)%?\)", colour):
            h, s, l = map(Fraction, c_str.group(1, 2, 3))
            if h > 360 or max(s, l) > 100 or min(h, s, l) < 0:
                return await ctx.send("You inputted an invalid colour. Please try again.", delete_after=5)
            await ctx.send(embed=hslRGB(h, s, l, c_str))
        elif c_str := re.search(r"cmyk\((\d{1,3}(\.\d*)?)%?, *(\d{1,3}(\.\d*)?)%?, *(\d{1,3}(\.\d*)?)%?, *(\d{1,3}(\.\d*)?)%?\)", colour):
            c, m, y, k = map(Fraction, c_str.group(1, 2, 3, 4))
            if max(c, m, y, k) > 100 or min(c, m, y, k) < 0:
                return await ctx.send("You inputted an invalid colour. Please try again.", delete_after=5)
            await ctx.send(embed=cmykRGB(c, m, y, k, c_str))
        elif colour.lower() in css:
            await ctx.send(embed=cssRGB(colour.lower()))
        else:
            await ctx.send("You inputted an invalid colour. Please try again.", delete_after=5)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def die(self, ctx):
        await self.bot.logout()

    @commands.command()
    async def dm(self, ctx):
        """
        `!dm` __`221DM Generator`__

        **Usage:** !dm <user | close> [user] [...]

        **Examples:**
        `!dm @blankuser#1234` creates 221DM with TAs and blankuser
        `!dm @blankuser#1234 @otheruser#5678` creates 221DM with TAs, blankuser and otheruser
        `!dm close` closes 221DM

        *Only usable by TAs and Profs
        """

        # meant for 221 server
        guild = self.bot.get_guild(745503628479037492)

        if "close" in ctx.message.content.lower():
            if not ctx.channel.name.startswith("221dm-"):
                return await ctx.send("This is not a 221DM.")

            await ctx.send("Closing 221DM.")
            await next(i for i in guild.roles if i.name == ctx.channel.name).delete()
            return await ctx.channel.delete()

        if all(i.name not in ("TA", "Prof") for i in ctx.author.roles):
            # only TAs and Prof can use this command
            return await ctx.send("You do not have permission to use this command.")

        if not ctx.message.mentions:
            return await ctx.send("You need to specify a user or users to add!")

        # generate customized channel name to allow customized role
        nam = int(str((datetime.now() - datetime(1970, 1, 1)).total_seconds()).replace(".", "")) + ctx.author.id
        nam = f"221dm-{nam}"
        # create custom role
        role = await guild.create_role(name=nam, colour=discord.Colour(0x2f3136))

        for user in ctx.message.mentions:
            try:
                await user.add_roles(role)
            except (discord.Forbidden, discord.HTTPException):
                pass  # if for whatever reason one of the people doesn't exist, just ignore and keep going

        access = discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True)
        noaccess = discord.PermissionOverwrite(read_messages=False, read_message_history=False, send_messages=False)
        overwrites = {
            # allow Computers and the new role, deny everyone else including Fake TA
            guild.default_role: noaccess,
            guild.get_role(748035942945914920): access,
            role: access
        }
        # this id is id of group dm category
        channel = await guild.create_text_channel(nam, overwrites=overwrites, category=guild.get_channel(764672304793255986))
        await ctx.send("Opened channel.")
        users = (f"<@{usr.id}>" for usr in ctx.message.mentions)
        await channel.send(f"<@{ctx.author.id}> {' '.join(users)}\n" +
                           f"Welcome to 221 private DM. Type `!close` to exit when you are finished.")

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def gtcycle(self, ctx, limit, *, txt):
        """
        `!gtcycle` __`Google Translate Cycler`__

        **Usage:** !gtcycle <number of languages | all> <text>

        **Examples:**
        `!gtcycle all hello!` cycles through all languages with input text "hello!"
        `!gtcycle 12 hello!` cycles through 12 languages with input text "hello!"
        """

        lang_list = list(constants.LANGUAGES)
        random.shuffle(lang_list)

        if limit == "all":
            limit = len(lang_list)
        elif not (limit.isdecimal() and 1 < (limit := int(limit)) < len(constants.LANGUAGES)):
            return await ctx.send(
                f"Please send a positive integer number of languages less than {len(constants.LANGUAGES)} to cycle.",
                delete_after=5)

        lang_list = ["en"] + lang_list[:limit] + ["en"]
        translator = Translator()

        for i, j in zip(lang_list[:-1], lang_list[1:]):
            translation = translator.translate(txt, src=i, dest=j)
            txt = translation.text
            await asyncio.sleep(0)

        if len(txt) > 2000:
            if len(txt) > 10000:
                await ctx.send("Result too large.")
            else:
                while len(txt) > 2000:
                    await ctx.send(txt[:2000])
                    txt = txt[2000:]

                await ctx.send(txt)
        else:
            await ctx.send(txt)

        return

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def help(self, ctx, *arg):
        """
        `!help` __`Returns list of commands or usage of command`__

        **Usage:** !help [optional cmd]

        **Examples:**
        `!help` [embed]
        """

        main = self.bot.get_cog("Main")

        if not arg:
            embed = discord.Embed(title="CS221 Bot", description="Commands:", colour=random.randint(0, 0xFFFFFF), timestamp=datetime.utcnow())
            embed.add_field(name=f"❗ Current Prefix: `{self.bot.command_prefix}`", value="\u200b", inline=False)
            embed.add_field(name="Commands", value=" ".join(f"`{i}`" for i in main.get_commands() if not i.hidden), inline=False)
            embed.set_thumbnail(url=self.bot.user.avatar_url)
            embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=str(ctx.author.avatar_url))
            await ctx.send(embed=embed)
        else:
            help_command = arg[0]

            comm = self.bot.get_command(help_command)

            if not comm or not comm.help or comm.hidden:
                return await ctx.send("That command doesn't exist.", delete_after=5)

            await ctx.send(comm.help)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def join(self, ctx, *arg):
        """
        `!join` __`Adds a role to yourself`__

        **Usage:** !join [role name]

        **Examples:**
        `!join L1A` adds the L1A role to yourself

        **Valid Roles:**
        Looking for Partners, Study Group, L1A, L1B, L1C, L1D, L1E, L1F, L1G, L1H, L1J, L1K, L1N, L1P, L1R, L1S, L1T, He/Him/His, She/Her/Hers, They/Them/Theirs, Ze/Zir/Zirs, notify
        """

        # case where role name is space separated
        name = " ".join(arg).lower()
        # Display help if given no argument
        if not name:
            return await ctx.send(ctx.command.help)
        # make sure that you can't add roles like "prof" or "ta"
        valid_roles = ["Looking for Partners", "Study Group", "L1A", "L1B", "L1C", "L1D", "L1E", "L1F", "L1G", "L1H", "L1J", "L1K", "L1N", "L1P", "L1R", "L1S", "L1T", "He/Him/His", "She/Her/Hers", "They/Them/Theirs", "Ze/Zir/Zirs", "notify"]
        aliases = {"he": "He/Him/His", "she": "She/Her/Hers", "ze": "Ze/Zir/Zirs", "they": "They/Them/Theirs"}

        # Convert alias to proper name
        if name in aliases:
            name = aliases[name].lower()

        # Ensure that people only add one lab role
        if name.startswith("l1") and any(role.name.startswith("L1") for role in ctx.author.roles):
            return await ctx.send("You already have a lab role!", delete_after=5)

        # Grab the role that the user selected
        role = next((r for r in ctx.guild.roles if name == r.name.lower()), None)

        # Check that the role actually exists
        if not role:
            await ctx.send("You can't add that role!", delete_after=5)
            return await ctx.send(ctx.command.help)

        # Ensure that the author does not already have the role
        if role in ctx.author.roles:
            return await ctx.send("you already have that role!", delete_after=5)

        # Special handling for roles that exist but can not be selected by a student
        if role.name not in valid_roles:
            self.add_instructor_role_counter += 1
            if self.add_instructor_role_counter > 5:
                if self.add_instructor_role_counter == 42:
                    if random.random() > 0.999:
                        return await ctx.send("Congratulations, you found the secret message. IDEK how you did it, but good job. Still can't add the instructor role though. Bummer, I know.", delete_after=5)
                elif self.add_instructor_role_counter == 69:
                    if random.random() > 0.9999:
                        return await ctx.send("nice.", delete_after=5)
                return await ctx.send("You can't add that role, but if you try again, maybe something different will happen on the 42nd attempt", delete_after=5)
            else:
                return await ctx.send("you cannot add an instructor/invalid role!", delete_after=5)

        await ctx.author.add_roles(role)
        return await ctx.send("role added!", delete_after=5)

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def latex(self, ctx, *args):
        """
        `!latex` __`LaTeX equation render`__

        **Usage:** !latex <equation>

        **Examples:**
        `!latex \\frac{a}{b}` [img]
        """

        formula = " ".join(args).strip("`")
        if (sm := formula.splitlines()[0].lower) in ("latex", "tex"):
            formula = formula[3 if sm == "tex" else 5:]

        body = {
            "formula": formula,
            "fsize": r"30px",
            "fcolor": r"FFFFFF",
            "mode": r"0",
            "out": r"1",
            "remhost": r"quicklatex.com",
            "preamble": r"\usepackage{amsmath}\usepackage{amsfonts}\usepackage{amssymb}",
            "rnd": str(random.random() * 100)
        }

        try:
            img = requests.post("https://www.quicklatex.com/latex3.f", data=body, timeout=10)
        except (requests.ConnectionError, requests.HTTPError, requests.TooManyRedirects, requests.Timeout):
            return await ctx.send("Render timed out.", delete_after=5)

        if img.status_code == 200:
            if img.text.startswith("0"):
                await ctx.send(file=discord.File(BytesIO(requests.get(img.text.split()[1]).content), "latex.png"))
            else:
                await ctx.send(" ".join(img.text.split()[5:]), delete_after=5)
        else:
            await ctx.send("Something done goofed. Maybe check your syntax?", delete_after=5)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def leave(self, ctx, *arg):
        """
        `!leave` __`Removes an existing role from yourself`__

        **Usage:** !leave [role name]

        **Examples:**
        `!leave L1A` removes the L1A role from yourself
        """

        # case where role name is space separated
        name = " ".join(arg).lower()
        if not name:
            return await ctx.send(ctx.command.help)

        for role in ctx.guild.roles:
            if name == role.name.lower():
                if role in ctx.author.roles:
                    await ctx.author.remove_roles(role)
                    return await ctx.send("role removed!", delete_after=5)
                else:
                    return await ctx.send("you don't have that role!", delete_after=5)
        else:
            await ctx.send("that role doesn't exist!", delete_after=5)
            return await ctx.send(ctx.command.help)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def poll(self, ctx):
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

        id_ = self.bot.poll_dict[str(ctx.channel.id)]

        if question in ("check", "end"):
            if end := (question == "end"):
                self.bot.poll_dict[str(ctx.channel.id)] = ""
                self.bot.writeJSON(self.bot.poll_dict, "data/poll.json")

            if not id_:
                return await ctx.send("No active poll found.", delete_after=5)

            try:
                poll_message = await ctx.channel.fetch_message(id_)
            except discord.NotFound:
                return await ctx.send("Looks like someone deleted the poll, or there is no active poll.", delete_after=5)

            embed = poll_message.embeds[0]
            unformatted_options = [x.strip().split(": ")
                                   for x in embed.description.split("\n")]
            options_dict = {}

            for x in unformatted_options:
                options_dict[x[0]] = x[1]

            tally = {x: 0 for x in options_dict.keys()}

            for reaction in poll_message.reactions:
                if reaction.emoji in options_dict.keys():
                    async for reactor in reaction.users():
                        if reactor.id != self.bot.user.id:
                            tally[reaction.emoji] += 1

            output = f"{'Final' if end else 'Current'} results of the poll **\"{embed.title}\"**\nLink: {poll_message.jump_url}\n```"

            max_len = max(map(len, tally.values()))
            # Dicts act like sets of their keys without .values() or something similar. So .keys() is rarely needed.
            for key in tally:
                if tally[key]:
                    output += f"{options_dict[key].ljust(max_len)}: " +\
                              f"{('👑' * tally[key]).replace('👑', '▓', tally[key] - 2) if tally[key] == max(tally.values()) else '░' * tally[key]}".rjust(max(tally.values())).replace('👑👑', '👑') +\
                              f" ({tally[key]} votes, {round(tally[key] / sum(tally.values()) * 100 if sum(tally.values()) else 0, 2)}%)\n\n"
                else:
                    output += f"{options_dict[key].ljust(max_len)}: 0\n\n"

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
            await ctx.send("Please enter more than one option to poll.", delete_after=5)
            return await ctx.send(ctx.command.help)
        elif len(options) > 20:
            return await ctx.send("Please limit to 10 options.", delete_after=5)
        elif len(options) == 2 and options[0] == "yes" and options[1] == "no":
            reactions = ["✅", "❌"]
        else:
            reactions = tuple(chr(127462 + i) for i in range(26))

        description = []

        for x, option in enumerate(options):
            description += f"\n {reactions[x]}: {option}"

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

        self.bot.poll_dict[str(ctx.channel.id)] = react_message.id
        self.bot.writeJSON(self.bot.poll_dict, "data/poll.json")

    @commands.command(hidden=True)
    @commands.is_owner()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def reload(self, ctx, *modules):
        if not isinstance(ctx.channel, discord.DMChannel):
            await ctx.message.delete()

        self.bot.reload_extension("commands")
        self.canvas_init(self.bot.get_cog("Main"))
        self.piazza_start(self.bot.get_cog("Main"))
        await ctx.send("Done")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def shut(self, ctx):
        change = ""

        for role in self.bot.get_guild(745503628479037492).roles[:-6]:
            if role.permissions.value == 104187456:
                change = "enabled messaging permissions"
                await role.edit(permissions=discord.Permissions(permissions=104189504))
            elif role.permissions.value == 104189504:
                change = "disabled messaging permissions"
                await role.edit(permissions=discord.Permissions(permissions=104187456))

        await ctx.send(change)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def userstats(self, ctx, *userid):
        """
        `!userstats` __`Check user profile and stats`__

        **Usage:** !userstats <USER ID>

        **Examples:** `!userstats 226878658013298690` [embed]
        """

        if not userid:
            user = ctx.author
        else:
            try:
                userid = int(userid[0])
            except ValueError:
                return await ctx.send("Please enter a user id", delete_after=5)

            user = ctx.guild.get_member(userid)

        if not user:
            return await ctx.send("That user does not exist", delete_after=5)

        # we use both user and member objects, since some stats can only be obtained
        # from either user or member object

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
            embed.add_field(name="Date Joined", value=user.joined_at.strftime("%A, %Y %B %d @ %H:%M:%S"), inline=True)
            embed.add_field(name="Account Created", value=user.created_at.strftime("%A, %Y %B %d @ %H:%M:%S"), inline=True)
            embed.add_field(name="Roles", value=", ".join([str(i) for i in sorted(user.roles[1:], key=lambda role: role.position, reverse=True)]), inline=True)
            embed.add_field(name="Most active text channel in last 24 h", value=f"{most_active_channel_name} ({most_active_channel} messages)", inline=True)
            embed.add_field(name="Total messages sent in last 24 h", value=str(cum_message_count), inline=True)

            await ctx.send(embed=embed)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def track(self, ctx: commands.Context, *course_ids: str):
        self._add_guild(ctx.message.guild)

        c_handler = self._get_canvas_handler(ctx.message.guild)

        if not isinstance(c_handler, CanvasHandler):
            return await ctx.send("Canvas Handler doesn't exist.", delete_after=5)

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
            return await ctx.send("Canvas Handler doesn't exist.", delete_after=5)

        c_handler.untrack_course(course_ids)

        if not c_handler.courses:
            self.d_handler.canvas_handlers.remove(c_handler)

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
            return await ctx.send("Canvas Handler doesn't exist.", delete_after=5)

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
            return await ctx.send("Canvas Handler doesn't exist.", delete_after=5)

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
            return await ctx.send("Canvas Handler doesn't exist.", delete_after=5)

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
    async def stream(self, ctx: commands.Context, *args):
        """
        `!stream ( | (-since (n-(hour|day|week|month|year)) | YYYY-MM-DD | YYYY-MM-DD-HH:MM:SS) | -all)`

        Argument can be left blank for sending announcements from 2 weeks ago to now.

        *Filter since announcement date:*

        `!stream -since` can be in time from now e.g.: `-since 4-hour` or all announcements after a certain date e.g.: `-since 2020-10-21`

        *All announcements:*

        `!stream -all` returns ALL announcements.
        """

        c_handler = self._get_canvas_handler(ctx.message.guild)

        if not isinstance(c_handler, CanvasHandler):
            return await ctx.send("Canvas Handler doesn't exist.", delete_after=5)

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
        if guild not in (ch.guild for ch in self.d_handler.canvas_handlers):
            self.d_handler.canvas_handlers.append(CanvasHandler(CANVAS_API_URL, "", guild))
            self.bot.canvas_dict[str(guild.id)] = {
                "courses": [],
                "live_channels": [],
                "due_week": {},
                "due_day": {}
            }
            self.bot.writeJSON(self.bot.canvas_dict, "data/canvas.json")

    def _get_canvas_handler(self, guild: discord.Guild) -> Optional[CanvasHandler]:
        return next((ch for ch in self.d_handler.canvas_handlers if ch.guild == guild), None)

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
            for ch in filter(operator.attrgetter("live_channels"), self.d_handler.canvas_handlers):
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
            for ch in filter(operator.attrgetter("live_channels"), self.d_handler.canvas_handlers):
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

            if guild not in (ch.guild for ch in self.d_handler.canvas_handlers):
                self.d_handler.canvas_handlers.append(CanvasHandler(CANVAS_API_URL, "", guild))

            c_handler = self._get_canvas_handler(guild)
            c_handler.track_course(tuple(self.bot.canvas_dict[c_handler_guild_id]["courses"]))
            live_channels_ids = self.bot.canvas_dict[c_handler_guild_id]["live_channels"]
            live_channels = list(filter(live_channels_ids.__contains__, guild.text_channels))
            c_handler.live_channels = live_channels

            for due in ("due_week", "due_day"):
                for c in self.bot.canvas_dict[c_handler_guild_id][due]:
                    c_handler.due_week[c] = self.bot.canvas_dict[c_handler_guild_id][due][c]

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

        self.d_handler.piazza_handler = PiazzaHandler(name, pid, PIAZZA_EMAIL, PIAZZA_PASSWORD, ctx.guild)

        # dict.get defaults to None so KeyError is never thrown
        for channel in self.bot.piazza_dict.get("channels"):
            self.d_handler.piazza_handler.add_channel(channel)

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

        self.d_handler.piazza_handler.add_channel(cid)
        self.bot.piazza_dict["channels"] = list(self.d_handler.piazza_handler.channels)
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

        self.d_handler.piazza_handler.remove_channel(cid)
        self.bot.piazza_dict["channels"] = list(self.d_handler.piazza_handler.channels)
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

        if self.d_handler.piazza_handler:
            posts = self.d_handler.piazza_handler.get_pinned()
            embed = discord.Embed(title=f"**Pinned posts for {self.d_handler.piazza_handler.course_name}:**", colour=0x497aaa)

            for post in posts:
                embed.add_field(name=f"@{post['num']}", value=f"[{post['subject']}]({post['url']})", inline=False)

            embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=str(ctx.author.avatar_url))

            await ctx.send(embed=embed)
        else:
            await ctx.send("Piazza hasn't been instantiated yet!")

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

        if not self.d_handler.piazza_handler:
            return await ctx.send("Piazza hasn't been instantiated yet!")

        try:
            post = self.d_handler.piazza_handler.get_post(postID)
        except InvalidPostID:
            return await ctx.send("Post not found.")

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
                post_embed.add_field(name=f"{post['num_answers']-1} more contributions hidden", value="Click the title above to access the rest of the post.", inline=False)

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
            self.send_piazza_posts(True)
            await asyncio.sleep(60*60*24)

    async def send_piazza_posts(self, wait: bool):
        if not self.d_handler.piazza_handler:
            return

        posts = self.d_handler.piazza_handler.get_posts_in_range()

        response = f"**{self.d_handler.piazza_handler.course_name}'s posts for {datetime.today().strftime('%a. %B %d, %Y')}**\n"

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

        for ch in self.d_handler.piazza_handler.channels:
            channel = self.bot.get_channel(ch)
            await channel.send(response)

    @staticmethod
    async def track_inotes(self):
        while True:
            if self.d_handler.piazza_handler:
                posts = self.d_handler.piazza_handler.get_recent_notes()

                if len(posts) > 1:
                    response = "Instructor Update:\n"

                    for post in posts:
                        response += f"@{post['num']}: {post['subject']} <{post['url']}>\n"

                    for chnl in self.d_handler.piazza_handler.channels:
                        channel = self.bot.get_channel(chnl)
                        await channel.send(response)

            await asyncio.sleep(60*60*5)

    @staticmethod
    def piazza_start(self):
        if all(field in self.bot.piazza_dict for field in ("course_name", "piazza_id", "guild_id")):
            self.d_handler.piazza_handler = PiazzaHandler(self.bot.piazza_dict["course_name"], self.bot.piazza_dict["piazza_id"], PIAZZA_EMAIL, PIAZZA_PASSWORD, self.bot.piazza_dict["guild_id"])

        # dict.get defaults to None so a key error is never raised
        for ch in self.bot.piazza_dict.get("channels"):
            self.d_handler.piazza_handler.add_channel(int(ch))

    # add more commands here with the same syntax
    # also just look up the docs lol i can't do everything

# ################### END COMMANDS ################### #


def setup(bot):
    bot.add_cog(Main(bot))
