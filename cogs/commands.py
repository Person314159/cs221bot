import asyncio
import mimetypes
import random
import re
import urllib.parse
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from io import BytesIO
from operator import methodcaller

import discord
import pytz
import requests
import requests.models
import webcolors
from discord.ext import commands
from googletrans import constants, Translator

from cogs.meta import BadArgs
from handlers.discord_handler import DiscordHandler


# This is a huge hack but it technically works
def _urlencode(*args, **kwargs):
    kwargs.update(quote_via=urllib.parse.quote)
    return urllib.parse.urlencode(*args, **kwargs)


requests.models.urlencode = _urlencode


# ################### COMMANDS ################### #


class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.add_instructor_role_counter = 0
        self.bot.d_handler = DiscordHandler()

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
            return color_embed(colour, r, g, b, c, m, y, k, h, s, l)

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
        elif c_str := re.search(r"\brgb\((\d{1,3}), *(\d{1,3}), *(\d{1,3})\)", colour):
            r, g, b = map(int, c_str.group(1, 2, 3))

            if max(r, g, b) > 255 or min(r, g, b) < 0:
                raise BadArgs("You inputted an invalid colour. Please try again.", show_help=True)

            await ctx.send(embed=RGB(r, g, b, c_str.group()))
        elif c_str := re.search(r"\bhsl\((\d{1,3}(?:\.\d*)?), *(\d{1,3}(?:\.\d*)?)%?, *(\d{1,3}(?:\.\d*)?)%?\)", colour):
            h, s, l = map(Fraction, c_str.group(1, 2, 3))

            if h > 360 or max(s, l) > 100 or min(h, s, l) < 0:
                raise BadArgs("You inputted an invalid colour. Please try again.", show_help=True)

            await ctx.send(embed=hslRGB(h, s, l, c_str.group()))
        elif c_str := re.search(r"\bcmyk\((\d{1,3}(?:\.\d*)?)%?, *(\d{1,3}(?:\.\d*)?)%?, *(\d{1,3}(?:\.\d*)?)%?, *(\d{1,3}(?:\.\d*)?)%?\)", colour):
            c, m, y, k = map(Fraction, c_str.group(1, 2, 3, 4))

            if max(c, m, y, k) > 100 or min(c, m, y, k) < 0:
                raise BadArgs("You inputted an invalid colour. Please try again.", show_help=True)

            await ctx.send(embed=cmykRGB(c, m, y, k, c_str.group()))
        elif colour.lower() in css:
            await ctx.send(embed=cssRGB(colour.lower()))
        elif c_str := re.search(r"\b#?([\dA-F]([\dA-F](?=[\dA-F]{4}))?)([\dA-F](?:(?<=[\dA-F]{3})[\dA-F](?=[\dA-F]{2}))?)([\dA-F](?:(?<=[\dA-F]{5})[\dA-F])?)\b", colour, re.I):
            mul = methodcaller("__mul__", 1 + (not c_str.group(2)))
            r, g, b = map(mul, c_str.group(1, 3, 4))

            await ctx.send(embed=RGB(int(r, 16), int(g, 16), int(b, 16), c_str.group()))
        else:
            raise BadArgs("You inputted an invalid colour. Please try again.", show_help=True)

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
                raise BadArgs("This is not a 221DM.")

            await ctx.send("Closing 221DM.")
            await next(i for i in guild.roles if i.name == ctx.channel.name).delete()
            return await ctx.channel.delete()

        if all(i.name not in ("TA", "Prof") for i in ctx.author.roles):
            # only TAs and Prof can use this command
            raise BadArgs("You do not have permission to use this command.")

        if not ctx.message.mentions:
            raise BadArgs("You need to specify a user or users to add!", show_help=True)

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
            guild.default_role                : noaccess,
            guild.get_role(748035942945914920): access,
            role                              : access
        }
        # this id is id of group dm category
        channel = await guild.create_text_channel(nam, overwrites=overwrites, category=guild.get_channel(764672304793255986))
        await ctx.send("Opened channel.")
        users = (f"<@{usr.id}>" for usr in ctx.message.mentions)
        await channel.send(f"<@{ctx.author.id}> {' '.join(users)}\n" +
                           f"Welcome to 221 private DM. Type `!dm close` to exit when you are finished.")

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

        if len(txt) > 10000:
            BadArgs("Result too large.", False)

        while len(txt) > 2000:
            await ctx.send(txt[:2000])
            txt = txt[2000:]

        await ctx.send(txt)

        return

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
            raise BadArgs("", show_help=True)

        # make sure that you can't add roles like "prof" or "ta"
        valid_roles = ["Looking for Partners", "Study Group", "L1A", "L1B", "L1C", "L1D", "L1E", "L1F", "L1G", "L1H", "L1J", "L1K", "L1N", "L1P", "L1R", "L1S", "L1T", "He/Him/His", "She/Her/Hers", "They/Them/Theirs", "Ze/Zir/Zirs", "notify"]
        aliases = {"he": "He/Him/His", "she": "She/Her/Hers", "ze": "Ze/Zir/Zirs", "they": "They/Them/Theirs"}

        # Convert alias to proper name
        if name.lower() in aliases:
            name = aliases[name].lower()

        # Ensure that people only add one lab role
        if name.startswith("l1") and any(role.name.startswith("L1") for role in ctx.author.roles):
            raise BadArgs("You already have a lab role!")

        # Grab the role that the user selected
        role = next((r for r in ctx.guild.roles if name == r.name.lower()), None)

        # Check that the role actually exists
        if not role:
            raise BadArgs("You can't add that role!", show_help=True)

        # Ensure that the author does not already have the role
        if role in ctx.author.roles:
            raise BadArgs("you already have that role!")

        # Special handling for roles that exist but can not be selected by a student
        if role.name not in valid_roles:
            self.add_instructor_role_counter += 1

            if self.add_instructor_role_counter > 5:
                if self.add_instructor_role_counter == 42:
                    if random.random() > 0.999:
                        raise BadArgs("Congratulations, you found the secret message. IDEK how you did it, but good job. Still can't add the instructor role though. Bummer, I know.")
                elif self.add_instructor_role_counter == 69:
                    if random.random() > 0.9999:
                        raise BadArgs("nice.")
                raise BadArgs( "You can't add that role, but if you try again, maybe something different will happen on the 42nd attempt")
            else:
                raise BadArgs("you cannot add an instructor/invalid role!", show_help=True)

        await ctx.author.add_roles(role)
        await ctx.send("role added!", delte_after=5)

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def latex(self, ctx, *args):
        """
        `!latex` __`LaTeX equation render`__

        **Usage:** !latex <equation>

        **Examples:**
        `!latex \\frac{a}{b}` [img]
        """

        formula = " ".join(args).strip("\n ")

        if sm := re.match(r"```(latex|tex)", formula):
            formula = formula[6 if sm.group(1) == "tex" else 8:]

        formula = formula.strip("`")

        body = {
            "formula" : formula,
            "fsize"   : r"30px",
            "fcolor"  : r"FFFFFF",
            "mode"    : r"0",
            "out"     : r"1",
            "remhost" : r"quicklatex.com",
            "preamble": r"\usepackage{amsmath}\usepackage{amsfonts}\usepackage{amssymb}",
            "rnd"     : str(random.random() * 100)
        }

        try:
            img = requests.post("https://www.quicklatex.com/latex3.f", data=body, timeout=10)
        except (requests.ConnectionError, requests.HTTPError, requests.TooManyRedirects, requests.Timeout):
            raise BadArgs("Render timed out.")

        if img.status_code != 200:
            raise BadArgs("Something done goofed. Maybe check your syntax?")

        if img.text.startswith("0"):
            await ctx.send(file=discord.File(BytesIO(requests.get(img.text.split()[1]).content), "latex.png"))
        else:
            await ctx.send(" ".join(img.text.split()[5:]), delete_after=5)

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
            raise BadArgs("", show_help=True)

        aliases = {"he": "he/him/his", "she": "she/her/hers", "ze": "ze/zir/zirs", "they": "they/them/theirs"}

        # Convert alias to proper name
        if name.lower() in aliases:
            name = aliases[name]

        role = next((r for r in ctx.guild.roles if name == r.name.lower()), None)

        if not role:
            raise BadArgs("that role doesn't exist!")

        if role not in ctx.author.roles:
            raise BadArgs("you don't have that role!")

        await ctx.author.remove_roles(role)
        await ctx.send("role removed!", delete_after=5)

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
                raise BadArgs("No active poll found.")

            try:
                poll_message = await ctx.channel.fetch_message(id_)
            except discord.NotFound:
                raise BadArgs("Looks like someone deleted the poll, or there is no active poll.")

            embed = poll_message.embeds[0]
            unformatted_options = [x.strip().split(": ") for x in embed.description.split("\n")]
            options_dict = {}

            for x in unformatted_options:
                options_dict[x[0]] = x[1]

            tally = {x: 0 for x in options_dict}

            for reaction in poll_message.reactions:
                if reaction.emoji in options_dict:
                    async for reactor in reaction.users():
                        if reactor.id != self.bot.user.id:
                            tally[reaction.emoji] += 1

            output = f"{'Final' if end else 'Current'} results of the poll **\"{embed.title}\"**\nLink: {poll_message.jump_url}\n```"

            max_len = max(map(len, options_dict.values()))

            for key in tally:
                output += f"{options_dict[key].ljust(max_len)}: " + \
                          f"{('👑' * tally[key]).replace('👑', '▓', ((tally[key] - 1) or 1) - 1) if tally[key] == max(tally.values()) else '░' * tally[key]}".ljust(max(tally.values())).replace('👑👑', '👑') + \
                          f" ({tally[key]} votes, {round(tally[key] / sum(tally.values()) * 100, 2) if sum(tally.values()) else 0}%)\n\n"

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
            raise BadArgs("Please enter more than one option to poll.", show_help=True)
        elif len(options) > 20:
            raise BadArgs("Please limit to 10 options.")
        elif len(options) == 2 and options[0] == "yes" and options[1] == "no":
            reactions = ["✅", "❌"]
        else:
            reactions = tuple(chr(127462 + i) for i in range(26))

        description = []

        for x, option in enumerate(options):
            description += f"\n{reactions[x]}: {option}"

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
                raise BadArgs("Please enter a user id", show_help=True)

            user = ctx.guild.get_member(userid)

        if not user:
            raise BadArgs("That user does not exist")

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

    # add more commands here with the same syntax
    # also just look up the docs lol i can't do everything


def setup(bot):
    bot.add_cog(Commands(bot))
