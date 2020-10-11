import ast
import asyncio
import datetime
import mimetypes
import os
import random
import pytz
import re
from datetime import timedelta
from fractions import Fraction
from io import BytesIO
from typing import List, Optional

import dateutil.parser.isoparser
import discord
import requests
import webcolors
from bs4 import BeautifulSoup
from canvasapi import Canvas
from discord.ext import commands
from dotenv import load_dotenv
from googletrans import Translator, constants

from canvas_handler import CanvasHandler
from discord_handler import DiscordHandler

CANVAS_COLOR = 0xe13f2b
CANVAS_THUMBNAIL_URL = "https://lh3.googleusercontent.com/2_M-EEPXb2xTMQSTZpSUefHR3TjgOCsawM3pjVG47jI-BrHoXGhKBpdEHeLElT95060B=s180"

load_dotenv()
CANVAS_API_URL = "https://canvas.ubc.ca"
CANVAS_API_KEY = os.getenv("CANVAS_API_KEY")

#################### COMMANDS ####################


class Main(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.add_instructor_role_counter = 0
        self.d_handler = DiscordHandler()

    @commands.command(hidden=True)
    async def close(self, ctx):
        if not ctx.channel.name.startswith("221dm-"): return
        await ctx.send("Closing DM.")
        for role in ctx.guild.roles:
          if role.name == ctx.channel.name:
            await role.delete()
            break
        await ctx.channel.delete()
        
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
                closest_name = actual_name = webcolors.rgb_to_name(
                    requested_colour)
            except ValueError:
                closest_name = closest_colour(requested_colour)
                actual_name = None

            return actual_name, closest_name

        css = {"lightsalmon": "0xFFA07A", "salmon": "0xFA8072", "darksalmon": "0xE9967A", "lightcoral": "0xF08080", "indianred": "0xCD5C5C", "crimson": "0xDC143C", "firebrick": "0xB22222", "red": "0xFF0000", "darkred": "0x8B0000", "coral": "0xFF7F50", "tomato": "0xFF6347", "orangered": "0xFF4500", "gold": "0xFFD700", "orange": "0xFFA500", "darkorange": "0xFF8C00", "lightyellow": "0xFFFFE0", "lemonchiffon": "0xFFFACD", "lightgoldenrodyellow": "0xFAFAD2", "papayawhip": "0xFFEFD5", "moccasin": "0xFFE4B5", "peachpuff": "0xFFDAB9", "palegoldenrod": "0xEEE8AA", "khaki": "0xF0E68C", "darkkhaki": "0xBDB76B", "yellow": "0xFFFF00", "lawngreen": "0x7CFC00", "chartreuse": "0x7FFF00", "limegreen": "0x32CD32", "lime": "0x00FF00", "forestgreen": "0x228B22", "green": "0x008000", "darkgreen": "0x006400", "greenyellow": "0xADFF2F", "yellowgreen": "0x9ACD32", "springgreen": "0x00FF7F", "mediumspringgreen": "0x00FA9A", "lightgreen": "0x90EE90", "palegreen": "0x98FB98", "darkseagreen": "0x8FBC8F", "mediumseagreen": "0x3CB371", "seagreen": "0x2E8B57", "olive": "0x808000", "darkolivegreen": "0x556B2F", "olivedrab": "0x6B8E23", "lightcyan": "0xE0FFFF", "cyan": "0x00FFFF", "aqua": "0x00FFFF", "aquamarine": "0x7FFFD4", "mediumaquamarine": "0x66CDAA", "paleturquoise": "0xAFEEEE", "turquoise": "0x40E0D0", "mediumturquoise": "0x48D1CC", "darkturquoise": "0x00CED1", "lightseagreen": "0x20B2AA", "cadetblue": "0x5F9EA0", "darkcyan": "0x008B8B", "teal": "0x008080", "powderblue": "0xB0E0E6", "lightblue": "0xADD8E6", "lightskyblue": "0x87CEFA", "skyblue": "0x87CEEB", "deepskyblue": "0x00BFFF", "lightsteelblue": "0xB0C4DE", "dodgerblue": "0x1E90FF", "cornflowerblue": "0x6495ED", "steelblue": "0x4682B4", "royalblue": "0x4169E1", "blue": "0x0000FF",
               "mediumblue": "0x0000CD", "darkblue": "0x00008B", "navy": "0x000080", "midnightblue": "0x191970", "mediumslateblue": "0x7B68EE", "slateblue": "0x6A5ACD", "darkslateblue": "0x483D8B", "lavender": "0xE6E6FA", "thistle": "0xD8BFD8", "plum": "0xDDA0DD", "violet": "0xEE82EE", "orchid": "0xDA70D6", "fuchsia": "0xFF00FF", "magenta": "0xFF00FF", "mediumorchid": "0xBA55D3", "mediumpurple": "0x9370DB", "blueviolet": "0x8A2BE2", "darkviolet": "0x9400D3", "darkorchid": "0x9932CC", "darkmagenta": "0x8B008B", "purple": "0x800080", "indigo": "0x4B0082", "pink": "0xFFC0CB", "lightpink": "0xFFB6C1", "hotpink": "0xFF69B4", "deeppink": "0xFF1493", "palevioletred": "0xDB7093", "mediumvioletred": "0xC71585", "white": "0xFFFFFF", "snow": "0xFFFAFA", "honeydew": "0xF0FFF0", "mintcream": "0xF5FFFA", "azure": "0xF0FFFF", "aliceblue": "0xF0F8FF", "ghostwhite": "0xF8F8FF", "whitesmoke": "0xF5F5F5", "seashell": "0xFFF5EE", "beige": "0xF5F5DC", "oldlace": "0xFDF5E6", "floralwhite": "0xFFFAF0", "ivory": "0xFFFFF0", "antiquewhite": "0xFAEBD7", "linen": "0xFAF0E6", "lavenderblush": "0xFFF0F5", "mistyrose": "0xFFE4E1", "gainsboro": "0xDCDCDC", "lightgray": "0xD3D3D3", "silver": "0xC0C0C0", "darkgray": "0xA9A9A9", "gray": "0x808080", "dimgray": "0x696969", "lightslategray": "0x778899", "slategray": "0x708090", "darkslategray": "0x2F4F4F", "black": "0x000000", "cornsilk": "0xFFF8DC", "blanchedalmond": "0xFFEBCD", "bisque": "0xFFE4C4", "navajowhite": "0xFFDEAD", "wheat": "0xF5DEB3", "burlywood": "0xDEB887", "tan": "0xD2B48C", "rosybrown": "0xBC8F8F", "sandybrown": "0xF4A460", "goldenrod": "0xDAA520", "peru": "0xCD853F", "chocolate": "0xD2691E", "saddlebrown": "0x8B4513", "sienna": "0xA0522D", "brown": "0xA52A2A", "maroon": "0x800000"}

        def RGB(r, g, b, colour):
            h, s, l = RGB_to_HSL(r, g, b)
            c, m, y, k = RGB_to_CMYK(r, g, b)
            Hex = f"#{RGB_to_HEX(r, g, b)}"
            rgb = f"rgb({r},{g},{b})"
            hsl = f"hsl({round(float(h), 2)},{round(float(s), 2)}%,{round(float(l), 2)}%)"
            cmyk = f"cmyk({round(float(c), 2)}%,{round(float(m), 2)}%,{round(float(y), 2)}%,{round(float(k), 2)}%)"
            css_code = get_colour_name((r, g, b))[1]
            embed = discord.Embed(
                title=colour, description="", colour=int(Hex[1:], 16))
            embed.add_field(name="Hex", value=Hex, inline=True)
            embed.add_field(name="RGB", value=rgb, inline=True)
            embed.add_field(name="HSL", value=hsl, inline=True)
            embed.add_field(name="CMYK", value=cmyk, inline=True)
            embed.add_field(name="CSS", value=css_code, inline=True)
            embed.set_thumbnail(
                url=f"https://serux.pro/rendercolour/?rgb={r},{g},{b}")
            return embed

        def hslRGB(h, s, l, colour):
            h -= (h // 360) * 360
            r, g, b = HSL_to_RGB(h, s, l)
            c, m, y, k = RGB_to_CMYK(r, g, b)
            r = round(r)
            g = round(g)
            b = round(b)
            Hex = f"#{RGB_to_HEX(r, g, b)}"
            rgb = f"rgb({r},{g},{b})"
            hsl = f"hsl({round(float(h), 2)},{round(float(s), 2)}%,{round(float(l), 2)}%)"
            cmyk = f"cmyk({round(float(c), 2)}%,{round(float(m), 2)}%,{round(float(y), 2)}%,{round(float(k), 2)}%)"
            css_code = get_colour_name((r, g, b))[1]
            embed = discord.Embed(
                title=colour, description="", colour=int(Hex[1:], 16))
            embed.add_field(name="Hex", value=Hex, inline=True)
            embed.add_field(name="RGB", value=rgb, inline=True)
            embed.add_field(name="HSL", value=hsl, inline=True)
            embed.add_field(name="CMYK", value=cmyk, inline=True)
            embed.add_field(name="CSS", value=css_code, inline=True)
            embed.set_thumbnail(
                url=f"https://serux.pro/rendercolour/?rgb={r},{g},{b}")
            return embed

        def cmykRGB(c, m, y, k, colour):
            r, g, b = CMYK_to_RGB(c, m, y, k)
            h, s, l = RGB_to_HSL(r, g, b)
            r = round(r)
            g = round(g)
            b = round(b)
            Hex = f"#{RGB_to_HEX(r, g, b)}"
            rgb = f"rgb({r},{g},{b})"
            hsl = f"hsl({round(float(h), 2)},{round(float(s), 2)}%,{round(float(l), 2)}%)"
            cmyk = f"cmyk({round(float(c), 2)}%,{round(float(m), 2)}%,{round(float(y), 2)}%,{round(float(k), 2)}%)"
            css_code = get_colour_name((r, g, b))[1]
            embed = discord.Embed(
                title=colour, description="", colour=int(Hex[1:], 16))
            embed.add_field(name="Hex", value=Hex, inline=True)
            embed.add_field(name="RGB", value=rgb, inline=True)
            embed.add_field(name="HSL", value=hsl, inline=True)
            embed.add_field(name="CMYK", value=cmyk, inline=True)
            embed.add_field(name="CSS", value=css_code, inline=True)
            embed.set_thumbnail(
                url=f"https://serux.pro/rendercolour/?rgb={r},{g},{b}")
            return embed

        def cssRGB(colour):
            r = int(css[colour][2:4], 16)
            g = int(css[colour][4:6], 16)
            b = int(css[colour][6:], 16)
            h, s, l = RGB_to_HSL(r, g, b)
            c, m, y, k = RGB_to_CMYK(r, g, b)
            Hex = f"#{RGB_to_HEX(r, g, b)}"
            rgb = f"rgb({r},{g},{b})"
            hsl = f"hsl({round(float(h), 2)},{round(float(s), 2)}%,{round(float(l), 2)}%)"
            cmyk = f"cmyk({round(float(c), 2)}%,{round(float(m), 2)}%,{round(float(y), 2)}%,{round(float(k), 2)}%)"
            css_code = get_colour_name((r, g, b))[1]
            embed = discord.Embed(
                title=colour, description="", colour=int(Hex[1:], 16))
            embed.add_field(name="Hex", value=Hex, inline=True)
            embed.add_field(name="RGB", value=rgb, inline=True)
            embed.add_field(name="HSL", value=hsl, inline=True)
            embed.add_field(name="CMYK", value=cmyk, inline=True)
            embed.add_field(name="CSS", value=css_code, inline=True)
            embed.set_thumbnail(
                url=f"https://serux.pro/rendercolour/?rgb={r},{g},{b}")
            return embed

        colour = ctx.message.content[len(self.bot.command_prefix) + 7:]

        if not colour:
            await ctx.send(embed=RGB(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), "Random Colour"))
        elif re.fullmatch(r"#([0-9A-Fa-f]{3}){1,2}", colour):
            if len(colour) == 7:
                await ctx.send(embed=RGB(int(colour[1:3], 16), int(colour[3:5], 16), int(colour[5:], 16), colour))
            elif len(colour) == 4:
                await ctx.send(embed=RGB(int(colour[1] * 2, 16), int(colour[2] * 2, 16), int(colour[3] * 2, 16), colour))
        elif re.fullmatch(r"([0-9A-Fa-f]{3}){1,2}", colour):
            if len(colour) == 6:
                await ctx.send(embed=RGB(int(colour[:2], 16), int(colour[2:4], 16), int(colour[4:], 16), colour))
            elif len(colour) == 3:
                await ctx.send(embed=RGB(int(colour[0] * 2, 16), int(colour[1] * 2, 16), int(colour[2] * 2, 16), colour))
        elif re.fullmatch(r"rgb\((\d{1,3}, *){2}\d{1,3}\)", colour):
            content = ast.literal_eval(colour[3:])
            await ctx.send(embed=RGB(content[0], content[1], content[2], colour))
        elif re.fullmatch(r"hsl\(\d{1,3}(\.\d*)?, *\d{1,3}(\.\d*)?%, *\d{1,3}(\.\d*)?%\)", colour):
            content = colour
            colour = colour[4:].split(")")[0].split(",")
            h = Fraction(colour[0])
            s = Fraction(colour[1][:-1])
            l = Fraction(colour[2][:-1])

            if h > 360 or s > 100 or l > 100:
                raise ValueError

            await ctx.send(embed=hslRGB(h, s, l, content))
        elif re.fullmatch(r"cmyk\((\d{1,3}(\.\d*)?%, *){3}\d{1,3}(\.\d*)?%\)", colour):
            content = colour
            colour = colour[5:].split(")")[0].split(",")
            c = Fraction(colour[0].split("%")[0])
            m = Fraction(colour[1].split("%")[0])
            y = Fraction(colour[2].split("%")[0])
            k = Fraction(colour[3].split("%")[0])

            if c > 100 or m > 100 or y > 100 or k > 100:
                raise ValueError

            await ctx.send(embed=cmykRGB(c, m, y, k, content))
        elif colour.lower() in css.keys():
            await ctx.send(embed=cssRGB(colour.lower()))
        else:
            return await ctx.send("You inputted an invalid colour. Please try again.", delete_after=5)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def die(self, ctx):
        await self.bot.logout()

    @commands.command(hidden=True)
    async def dm(self, ctx):
        # only works in 221 server, replace id with your own server's if using elsewhere
        if ctx.guild.id != 745503628479037492: return
        for role in ctx.author.roles:
            if role.name in ["TA", "Prof"]: break
        else: return # only TAs and Prof can use this command
        if len(ctx.message.mentions) == 0: return await ctx.send("You need to specify a user to add!")
        # generate customized channel name to allow customized role
        nam = int(str((datetime.datetime.now()- datetime.datetime(1970,1,1)).total_seconds()).replace(".", ""))+ctx.author.id
        nam = f"221dm-{nam}"
        role = await ctx.guild.create_role(name=nam, colour = discord.Colour(0x2f3136)) # create custom role
        for user in ctx.message.mentions:
          try: await user.add_roles(role)
          except: pass # if for whatever reason one of the people doesn't exist, just ignore and keep going
        access = discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True)
        noaccess = discord.PermissionOverwrite(read_messages=False, read_message_history=False, send_messages=False)
        overwrites = {
            # allow Computers and the new role, deny everyone else including Fake TA
            ctx.guild.default_role: noaccess,
            ctx.guild.get_role(748035942945914920): access,
            role: access
        }
        channel = await ctx.guild.create_text_channel(nam, overwrites=overwrites, category = ctx.guild.get_channel(764654262138437652)) # this id is id of group dm category
        await ctx.send("Opened channel.")
        await channel.send("Welcome to 221 private DM. Type `!close` to exit when you are finished.")
        
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

        if limit != "all":
            try:
                limit = int(limit)

                if limit < 1 or limit > len(constants.LANGUAGES):
                    raise ValueError
            except ValueError:
                return await ctx.send(f"Please send a positive integer number of languages less than {len(constants.LANGUAGES)} to cycle.", delete_after=5)
        else:
            limit = len(lang_list)

        lang_list = ["en"] + lang_list[:limit] + ["en"]
        translator = Translator()

        for i in range(len(lang_list) - 1):
            translation = translator.translate(
                txt, src=lang_list[i], dest=lang_list[i + 1])
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
            embed = discord.Embed(title="CS221 Bot", description="Commands:", colour=random.randint(
                0, 0xFFFFFF), timestamp=datetime.datetime.utcnow())
            embed.add_field(
                name=f"❗ Current Prefix: `{self.bot.command_prefix}`", value="\u200b", inline=False)
            embed.add_field(name="Commands", value=" ".join(
                f"`{i}`" for i in main.get_commands() if not i.hidden), inline=False)
            embed.set_thumbnail(url=self.bot.user.avatar_url)
            embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=str(
                ctx.author.avatar_url))
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
        # make sure that you can't add roles like "prof" or "ta"
        invalid_roles = ["Prof", "TA", "Fake TA",
                         "Computers", "Server Booster", "C++Bot", "CS221 bot"]
        aliases = {"he": 747925204864335935, "she": 747925268181811211,
                   "ze": 747925349232279552, "they": 747925313748729976}

        for role in ctx.guild.roles:
            if name == role.name.lower() and role.name not in invalid_roles and not role.name.startswith("221dm-"):
                if role.name in invalid_roles:
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
                        return await ctx.send("you cannot add an instructor role!", delete_after=5)
                elif name.startswith("l1") and any(role.name.startswith("L1") for role in ctx.author.roles):
                    return await ctx.send("you already have a lab role!", delete_after=5)
                elif role in ctx.author.roles:
                    return await ctx.send("you already have that role!", delete_after=5)
                else:
                    await ctx.author.add_roles(role)
                    return await ctx.send("role added!", delete_after=5)
            elif name in aliases:
                await ctx.author.add_roles(ctx.guild.get_role(aliases[name]))
                return await ctx.send("role added!", delete_after=5)
        else:
            await ctx.send("you can't add that role!", delete_after=5)
            return await ctx.send(ctx.command.help)

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def latex(self, ctx):
        """
        `!latex` __`LaTeX equation render`__

        **Usage:** !latex <equation>

        **Examples:**
        `!latex \\frac{a}{b}` [img]
        """

        formula = ctx.message.content[len(self.bot.command_prefix) + 6:]
        formula = formula.replace("%", "%25").replace("&", "%26")
        body = "formula=" + formula + \
            "&fsize=30px&fcolor=FFFFFF&mode=0&out=1&remhost=quicklatex.com&preamble=\\usepackage{amsmath}\\usepackage{amsfonts}\\usepackage{amssymb}&rnd=" + str(
                random.random() * 100)

        try:
            img = requests.post(
                "https://www.quicklatex.com/latex3.f", data=body.encode("utf-8"), timeout=10)
        except Exception:
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

        poll_list = ctx.message.content[6:].split(" | ")
        question = poll_list[0]
        options = poll_list[1:]

        id_ = self.bot.poll_dict[str(ctx.channel.id)]

        if question == "check":
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

            output = f"Current results of the poll **\"{embed.title}\"**\nLink: {poll_message.jump_url}\n```"

            for key in tally.keys():
                output += f"{options_dict[key]}: {'▓' * tally[key] if tally[key] == max(tally.values()) else '░' * tally[key]} ({tally[key]} votes, {round(tally[key] / sum(tally.values()) * 100 if sum(tally.values()) else 0, 2)}%)\n\n"

            output += "```"

            files = []
            for url in options_dict.values():
                if mimetypes.guess_type(url)[0] and mimetypes.guess_type(url)[0].startswith("image"):
                    filex = BytesIO(requests.get(url).content)
                    filex.seek(0)
                    files.append(discord.File(filex, filename=url))

            return await ctx.send(output, files=files)
        elif question == "end":
            self.bot.poll_dict[str(ctx.channel.id)] = ""
            self.bot.writeJSON(self.bot.poll_dict, "data/poll.json")

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

            output = f"Final results of the poll **\"{embed.title}\"**\nLink: {poll_message.jump_url}\n```"

            for key in tally.keys():
                if tally[key]:
                    output += f"{options_dict[key]}: {'▓' * tally[key] if tally[key] == max(tally.values()) else '░' * tally[key]} ({tally[key]} votes, {round(tally[key] / sum(tally.values()) * 100, 2)}%)\n\n"
                else:
                    output += f"{options_dict[key]}: 0\n\n"

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
            reactions = [chr(127462 + i) for i in range(26)]

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
        await ctx.send("Done")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def shut(self, ctx):
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
            yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).replace(
                tzinfo=pytz.timezone("US/Pacific")).astimezone(datetime.timezone.utc).replace(tzinfo=None)

            for channel in ctx.guild.text_channels:
                counter = 0

                async for message in channel.history(after=yesterday, limit=None):
                    if message.author == user:
                        counter += 1
                        cum_message_count += 1

                if counter > most_active_channel:
                    most_active_channel = counter
                    most_active_channel_name = "#" + channel.name

            embed = discord.Embed(
                title=f"Report for user `{user.name}#{user.discriminator}` (all times in UTC)")
            embed.add_field(name="Date Joined", value=user.joined_at.strftime(
                "%A, %Y %B %d @ %H:%M:%S"), inline=True)
            embed.add_field(name="Account Created", value=user.created_at.strftime(
                "%A, %Y %B %d @ %H:%M:%S"), inline=True)
            embed.add_field(name="Roles", value=", ".join([str(i) for i in sorted(
                user.roles[1:], key=lambda role: role.position, reverse=True)]), inline=True)
            embed.add_field(name="Most active text channel in last 24 h",
                            value=f"{most_active_channel_name} ({most_active_channel} messages)", inline=True)
            embed.add_field(name="Total messages sent in last 24 h",
                            value=cum_message_count, inline=True)

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

        self.bot.canvas_dict[str(ctx.message.guild.id)]["courses"] = [
            str(c.id) for c in c_handler.courses]
        self.bot.writeJSON(self.bot.canvas_dict, "data/canvas.json")

        embed_var = self._get_tracking_courses(
            c_handler, CANVAS_API_URL)
        embed_var.set_footer(
            text=f"Requested by {ctx.author.display_name}", icon_url=str(ctx.author.avatar_url))
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

        self.bot.canvas_dict[str(ctx.message.guild.id)]["courses"] = [
            str(c.id) for c in c_handler.courses]
        self.bot.writeJSON(self.bot.canvas_dict, "data/canvas.json")

        embed_var = self._get_tracking_courses(
            c_handler, CANVAS_API_URL)
        embed_var.set_footer(
            text=f"Requested by {ctx.author.display_name}", icon_url=str(ctx.author.avatar_url))
        await ctx.send(embed=embed_var)

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

        assignments = c_handler.get_assignments(
            due, course_ids, CANVAS_API_URL)

        if not assignments:
            pattern = r'\d{4}-\d{2}-\d{2}'
            return await ctx.send(f"No assignments due by {due}{' (at 00:00)' if re.match(pattern, due) else ''}.")

        for data in assignments:
            embed_var = discord.Embed(title=data[2], url=data[3], description=data[4], color=CANVAS_COLOR,
                                      timestamp=datetime.datetime.strptime(data[5], "%Y-%m-%d %H:%M:%S"))
            embed_var.set_author(name=data[0], url=data[1])
            embed_var.set_thumbnail(url=CANVAS_THUMBNAIL_URL)
            embed_var.add_field(name="Due at", value=data[6], inline=True)
            embed_var.set_footer(
                text="Created at", icon_url=CANVAS_THUMBNAIL_URL)
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

            self.bot.canvas_dict[str(ctx.message.guild.id)]["live_channels"] = [
                channel.id for channel in c_handler.live_channels]
            self.bot.writeJSON(self.bot.canvas_dict, "data/canvas.json")

            await ctx.send("Added channel to live tracking.")

    @commands.command(hidden=True)
    @commands.is_owner()
    @commands.guild_only()
    async def unlive(self, ctx: commands.Context):
        c_handler = self._get_canvas_handler(ctx.message.guild)
        if not isinstance(c_handler, CanvasHandler):
            return await ctx.send("Canvas Handler doesn't exist.", delete_after=5)
        if ctx.message.channel in c_handler.live_channels:
            c_handler.live_channels.remove(ctx.message.channel)

            self.bot.canvas_dict[str(ctx.message.guild.id)]["live_channels"] = [
                channel.id for channel in c_handler.live_channels]
            self.bot.writeJSON(self.bot.canvas_dict, "data/canvas.json")

            await ctx.send("Removed channel from live tracking.")

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
            embed_var = discord.Embed(
                title=data[2], url=data[3], description=data[4], color=CANVAS_COLOR)
            embed_var.set_author(name=data[0], url=data[1])
            embed_var.set_thumbnail(url=CANVAS_THUMBNAIL_URL)
            embed_var.add_field(name="Created at", value=data[5], inline=True)
            await ctx.send(embed=embed_var)

    @commands.command(hidden=True)
    @commands.is_owner()
    @commands.guild_only()
    async def info(self, ctx):
        c_handler = self._get_canvas_handler(ctx.message.guild)
        await ctx.send(str(c_handler.courses) + "\n" +
                       str(c_handler.guild) + "\n" +
                       str(c_handler.live_channels) + "\n" +
                       str(c_handler.timings) + "\n" +
                       str(c_handler.due_week) + "\n" +
                       str(c_handler.due_day))

    def _add_guild(self, guild: discord.Guild):
        if guild not in [ch.guild for ch in self.d_handler.canvas_handlers]:
            self.d_handler.canvas_handlers.append(
                CanvasHandler(CANVAS_API_URL, "", guild))
            self.bot.canvas_dict[str(guild.id)] = {
                "courses": [], "live_channels": [], "due_week": {}, "due_day": {}}
            self.bot.writeJSON(self.bot.canvas_dict, "data/canvas.json")

    def _get_canvas_handler(self, guild: discord.Guild) -> Optional[CanvasHandler]:
        for ch in self.d_handler.canvas_handlers:
            if ch.guild == guild:
                return ch

    def _get_tracking_courses(self, c_handler: CanvasHandler, CANVAS_API_URL) -> discord.Embed:
        course_names = c_handler.get_course_names(CANVAS_API_URL)
        embed_var = discord.Embed(
            title="Tracking Courses:", color=CANVAS_COLOR, timestamp=datetime.datetime.utcnow())
        embed_var.set_thumbnail(url=CANVAS_THUMBNAIL_URL)
        for c_name in course_names:
            embed_var.add_field(
                name=c_name[0], value=f"[Course Page]({c_name[1]})")
        return embed_var

    @staticmethod
    async def stream_tracking(self):
        while True:
            for ch in self.d_handler.canvas_handlers:
                if len(ch.live_channels) > 0:
                    notify_role = None
                    for role in ch.guild.roles:
                        if role.name.lower() == "notify":
                            notify_role = role
                            break
                    for c in ch.courses:
                        since = ch.timings[str(c.id)]
                        since = re.sub(r"\s", "-", since)
                        data_list = ch.get_course_stream_ch(
                            since, (str(c.id),), CANVAS_API_URL, CANVAS_API_KEY)
                        for data in data_list:
                            embed_var = discord.Embed(
                                title=data[2], url=data[3], description=data[4], color=CANVAS_COLOR)
                            embed_var.set_author(name=data[0], url=data[1])
                            embed_var.set_thumbnail(
                                url=CANVAS_THUMBNAIL_URL)
                            embed_var.add_field(
                                name="Created at", value=data[5], inline=True)
                            for channel in ch.live_channels:
                                await channel.send(notify_role.mention if notify_role else "", embed=embed_var)
                        if data_list:
                            # latest announcement first
                            ch.timings[str(c.id)] = data_list[0][5]

            await asyncio.sleep(3600)

    @staticmethod
    async def assignment_reminder(self):
        while True:
            for ch in self.d_handler.canvas_handlers:
                if ch.live_channels:
                    notify_role = None
                    for role in ch.guild.roles:
                        if role.name == "notify":
                            notify_role = role
                            break
                    for c in ch.courses:
                        data_list = ch.get_assignments(
                            "1-week", (str(c.id),), CANVAS_API_URL)
                        recorded_ass_ids = ch.due_week[str(c.id)]
                        ass_ids = await self._assignment_sender(self, ch, data_list, recorded_ass_ids, notify_role)
                        ch.due_week[str(c.id)] = ass_ids
                        self.bot.canvas_dict[str(
                            ch.guild.id)]["due_week"][str(c.id)] = ass_ids

                        data_list = ch.get_assignments(
                            "1-day", (str(c.id),), CANVAS_API_URL)
                        recorded_ass_ids = ch.due_day[str(c.id)]
                        ass_ids = await self._assignment_sender(self, ch, data_list, recorded_ass_ids, notify_role)
                        ch.due_day[str(c.id)] = ass_ids
                        self.bot.canvas_dict[str(
                            ch.guild.id)]["due_day"][str(c.id)] = ass_ids

                        self.bot.writeJSON(
                            self.bot.canvas_dict, "data/canvas.json")

            await asyncio.sleep(3600)

    @staticmethod
    async def _assignment_sender(self, ch, data_list, recorded_ass_ids, notify_role):
        ass_ids = [data[-1] for data in data_list]
        not_recorded = [data_list[ass_ids.index(
            i)] for i in ass_ids if i not in recorded_ass_ids]
        if notify_role and not_recorded:
            for channel in ch.live_channels:
                await channel.send(notify_role.mention)
        for data in not_recorded:
            embed_var = discord.Embed(
                title=data[2], url=data[3], description=data[4], color=CANVAS_COLOR, timestamp=datetime.datetime.strptime(data[5], "%Y-%m-%d %H:%M:%S"))
            embed_var.set_author(name=data[0], url=data[1])
            embed_var.set_thumbnail(url=CANVAS_THUMBNAIL_URL)
            embed_var.add_field(name="Due at", value=data[6], inline=True)
            embed_var.set_footer()
            embed_var.set_footer(
                text="Created at", icon_url=CANVAS_THUMBNAIL_URL)
            for channel in ch.live_channels:
                await channel.send(embed=embed_var)
        return ass_ids

    @staticmethod
    def canvas_init(self):
        for c_handler_guild_id in self.bot.canvas_dict:
            guild = self.bot.guilds[[guild.id for guild in self.bot.guilds].index(
                int(c_handler_guild_id))]
            if guild not in [ch.guild for ch in self.d_handler.canvas_handlers]:
                self.d_handler.canvas_handlers.append(
                    CanvasHandler(CANVAS_API_URL, "", guild))
            c_handler = self._get_canvas_handler(guild)
            c_handler.track_course(
                tuple(self.bot.canvas_dict[c_handler_guild_id]["courses"]))
            live_channels_ids = self.bot.canvas_dict[c_handler_guild_id]["live_channels"]
            live_channels = [
                channel for channel in guild.text_channels if channel.id in live_channels_ids]
            c_handler.live_channels = live_channels
            for c in self.bot.canvas_dict[c_handler_guild_id]["due_week"]:
                c_handler.due_week[c] = self.bot.canvas_dict[c_handler_guild_id]["due_week"][c]
            for c in self.bot.canvas_dict[c_handler_guild_id]["due_day"]:
                c_handler.due_day[c] = self.bot.canvas_dict[c_handler_guild_id]["due_day"][c]

    # add more commands here with the same syntax
    # also just look up the docs lol i can't do everything

#################### END COMMANDS ####################


def setup(bot):
    bot.add_cog(Main(bot))
