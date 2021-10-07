import asyncio

import discord
import youtube_dl
from discord.ext import commands

from util.badargs import BadArgs

youtube_dl.utils.bug_reports_message = lambda: ""

ytdl_format_options = {
    'format'            : 'bestaudio/best',
    'outtmpl'           : '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames' : True,
    'noplaylist'        : True,
    'nocheckcertificate': True,
    'ignoreerrors'      : False,
    'logtostderr'       : False,
    'quiet'             : True,
    'no_warnings'       : True,
    'default_search'    : 'auto',
    'source_address'    : '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get("title")
        self.url = data.get("url")

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if "entries" in data:
            # take first item from a playlist
            data = data["entries"][0]

        filename = data["url"] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def play(self, ctx, *, url):
        player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
        ctx.voice_client.play(player, after=lambda e: exec("raise BadArgs('Player Error.')") if e else None)

        await ctx.send(f"Now playing: {player.title}")

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def volume(self, ctx, volume: int):
        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        if not 0 <= volume <= 200:
            raise BadArgs("Please input a valid volume percentage between 0 and 200%.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def stop(self, ctx):
        await ctx.voice_client.disconnect()

    @play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                raise BadArgs("You are not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Music(bot))