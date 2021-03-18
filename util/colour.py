from typing import Optional, Tuple

import discord
import webcolors


def rgb_to_hsl(r: float, g: float, b: float) -> Tuple[float, float, float]:
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


def hsl_to_rgb(h: float, s: float, l: float) -> Tuple[float, float, float]:
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


def rgb_to_cmyk(r: float, g: float, b: float) -> Tuple[float, float, float, float]:
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


def cmyk_to_rgb(c: float, m: float, y: float, k: float) -> Tuple[float, float, float]:
    c /= 100
    m /= 100
    y /= 100
    k /= 100
    r = 255 * (1 - c) * (1 - k)
    g = 255 * (1 - m) * (1 - k)
    b = 255 * (1 - y) * (1 - k)
    return r, g, b


def rgb_to_hex(r: int, g: int, b: int) -> str:
    return hex(r * 16 ** 4 + g * 16 ** 2 + b)[2:].zfill(6)


def closest_colour(requested_colour: Tuple[int, int, int]) -> str:
    min_colours = {}

    for key, name in webcolors.CSS3_HEX_TO_NAMES.items():
        r_c, g_c, b_c = webcolors.hex_to_rgb(key)
        rd = (r_c - requested_colour[0]) ** 2
        gd = (g_c - requested_colour[1]) ** 2
        bd = (b_c - requested_colour[2]) ** 2
        min_colours[(rd + gd + bd)] = name

    return min_colours[min(min_colours.keys())]


def get_colour_name(requested_colour: Tuple[int, int, int]) -> Tuple[Optional[str], str]:
    try:
        closest_name = actual_name = webcolors.rgb_to_name(requested_colour)
    except ValueError:
        closest_name = closest_colour(requested_colour)
        actual_name = None

    return actual_name, closest_name


css = {"lightsalmon"   : "0xFFA07A", "salmon": "0xFA8072", "darksalmon": "0xE9967A", "lightcoral": "0xF08080", "indianred": "0xCD5C5C", "crimson": "0xDC143C", "firebrick": "0xB22222", "red": "0xFF0000", "darkred": "0x8B0000", "coral": "0xFF7F50", "tomato": "0xFF6347", "orangered": "0xFF4500", "gold": "0xFFD700", "orange": "0xFFA500", "darkorange": "0xFF8C00", "lightyellow": "0xFFFFE0", "lemonchiffon": "0xFFFACD", "lightgoldenrodyellow": "0xFAFAD2", "papayawhip": "0xFFEFD5", "moccasin": "0xFFE4B5", "peachpuff": "0xFFDAB9", "palegoldenrod": "0xEEE8AA", "khaki": "0xF0E68C", "darkkhaki": "0xBDB76B", "yellow": "0xFFFF00", "lawngreen": "0x7CFC00", "chartreuse": "0x7FFF00", "limegreen": "0x32CD32", "lime": "0x00FF00", "forestgreen": "0x228B22", "green": "0x008000", "darkgreen": "0x006400", "greenyellow": "0xADFF2F", "yellowgreen": "0x9ACD32", "springgreen": "0x00FF7F", "mediumspringgreen": "0x00FA9A", "lightgreen": "0x90EE90", "palegreen": "0x98FB98", "darkseagreen": "0x8FBC8F",
       "mediumseagreen": "0x3CB371", "seagreen": "0x2E8B57", "olive": "0x808000", "darkolivegreen": "0x556B2F", "olivedrab": "0x6B8E23", "lightcyan": "0xE0FFFF", "cyan": "0x00FFFF", "aqua": "0x00FFFF", "aquamarine": "0x7FFFD4", "mediumaquamarine": "0x66CDAA", "paleturquoise": "0xAFEEEE", "turquoise": "0x40E0D0", "mediumturquoise": "0x48D1CC", "darkturquoise": "0x00CED1", "lightseagreen": "0x20B2AA", "cadetblue": "0x5F9EA0", "darkcyan": "0x008B8B", "teal": "0x008080", "powderblue": "0xB0E0E6", "lightblue": "0xADD8E6", "lightskyblue": "0x87CEFA", "skyblue": "0x87CEEB", "deepskyblue": "0x00BFFF", "lightsteelblue": "0xB0C4DE", "dodgerblue": "0x1E90FF", "cornflowerblue": "0x6495ED", "steelblue": "0x4682B4", "royalblue": "0x4169E1", "blue": "0x0000FF", "mediumblue": "0x0000CD", "darkblue": "0x00008B", "navy": "0x000080", "midnightblue": "0x191970", "mediumslateblue": "0x7B68EE", "slateblue": "0x6A5ACD", "darkslateblue": "0x483D8B", "lavender": "0xE6E6FA", "thistle": "0xD8BFD8",
       "plum"          : "0xDDA0DD", "violet": "0xEE82EE", "orchid": "0xDA70D6", "fuchsia": "0xFF00FF", "magenta": "0xFF00FF", "mediumorchid": "0xBA55D3", "mediumpurple": "0x9370DB", "blueviolet": "0x8A2BE2", "darkviolet": "0x9400D3", "darkorchid": "0x9932CC", "darkmagenta": "0x8B008B", "purple": "0x800080", "indigo": "0x4B0082", "pink": "0xFFC0CB", "lightpink": "0xFFB6C1", "hotpink": "0xFF69B4", "deeppink": "0xFF1493", "palevioletred": "0xDB7093", "mediumvioletred": "0xC71585", "white": "0xFFFFFF", "snow": "0xFFFAFA", "honeydew": "0xF0FFF0", "mintcream": "0xF5FFFA", "azure": "0xF0FFFF", "aliceblue": "0xF0F8FF", "ghostwhite": "0xF8F8FF", "whitesmoke": "0xF5F5F5", "seashell": "0xFFF5EE", "beige": "0xF5F5DC", "oldlace": "0xFDF5E6", "floralwhite": "0xFFFAF0", "ivory": "0xFFFFF0", "antiquewhite": "0xFAEBD7", "linen": "0xFAF0E6", "lavenderblush": "0xFFF0F5", "mistyrose": "0xFFE4E1", "gainsboro": "0xDCDCDC", "lightgray": "0xD3D3D3", "silver": "0xC0C0C0", "darkgray": "0xA9A9A9",
       "gray"          : "0x808080", "dimgray": "0x696969", "lightslategray": "0x778899", "slategray": "0x708090", "darkslategray": "0x2F4F4F", "black": "0x000000", "cornsilk": "0xFFF8DC", "blanchedalmond": "0xFFEBCD", "bisque": "0xFFE4C4", "navajowhite": "0xFFDEAD", "wheat": "0xF5DEB3", "burlywood": "0xDEB887", "tan": "0xD2B48C", "rosybrown": "0xBC8F8F", "sandybrown": "0xF4A460", "goldenrod": "0xDAA520", "peru": "0xCD853F", "chocolate": "0xD2691E", "saddlebrown": "0x8B4513", "sienna": "0xA0522D", "brown": "0xA52A2A", "maroon": "0x800000"}


def color_embed(colour: str, r: int, g: int, b: int, c: float, m: float, y: float, k: float, h: float, s: float, l: float) -> discord.Embed:
    hex_ = f"#{rgb_to_hex(r, g, b)}"
    rgb = f"rgb({r},{g},{b})"
    hsl = f"hsl({round(h, 2)},{round(s, 2)}%,{round(l, 2)}%)"
    cmyk = f"cmyk({round(c, 2)}%,{round(m, 2)}%,{round(y, 2)}%,{round(k, 2)}%)"
    css_code = get_colour_name((r, g, b))[1]
    embed = discord.Embed(title=colour, description="", colour=int(hex_[1:], 16))
    embed.add_field(name="Hex", value=hex_, inline=True)
    embed.add_field(name="RGB", value=rgb, inline=True)
    embed.add_field(name="HSL", value=hsl, inline=True)
    embed.add_field(name="CMYK", value=cmyk, inline=True)
    embed.add_field(name="CSS", value=css_code, inline=True)
    embed.set_thumbnail(url=f"https://serux.pro/rendercolour/?rgb={r},{g},{b}")
    return embed


def rgb_embed(r: int, g: int, b: int, colour: str) -> discord.Embed:
    h, s, l = rgb_to_hsl(r, g, b)
    c, m, y, k = rgb_to_cmyk(r, g, b)
    return color_embed(colour, r, g, b, c, m, y, k, h, s, l)


def hsl_embed(h: float, s: float, l: float, colour: str) -> discord.Embed:
    h -= (h // 360) * 360
    r, g, b = hsl_to_rgb(h, s, l)
    c, m, y, k = rgb_to_cmyk(r, g, b)
    r = round(r)
    g = round(g)
    b = round(b)
    return color_embed(colour, r, g, b, c, m, y, k, h, s, l)


def cmyk_embed(c: float, m: float, y: float, k: float, colour: str) -> discord.Embed:
    r, g, b = cmyk_to_rgb(c, m, y, k)
    h, s, l = rgb_to_hsl(r, g, b)
    r = round(r)
    g = round(g)
    b = round(b)
    return color_embed(colour, r, g, b, c, m, y, k, h, s, l)


def css_embed(colour: str) -> discord.Embed:
    r = int(css[colour][2:4], 16)
    g = int(css[colour][4:6], 16)
    b = int(css[colour][6:], 16)
    h, s, l = rgb_to_hsl(r, g, b)
    c, m, y, k = rgb_to_cmyk(r, g, b)
    return color_embed(colour, r, g, b, c, m, y, k, h, s, l)
