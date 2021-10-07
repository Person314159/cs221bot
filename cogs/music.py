"""
Copyright (c) 2019 Valentin B.
A simple music bot written in discord.py using youtube-dl.
Though it's a simple example, music bots are complex and require much time and knowledge until they work perfectly.
Use this as an example or a base for your own bot and extend it as you want. If there are any bugs, please let me know.
Requirements:
Python 3.5+
You also need FFmpeg in your PATH environment variable or the FFmpeg.exe binary in your bot's directory on Windows.
"""

import asyncio
import functools
import itertools
import math
import random

import discord
import youtube_dl
from async_timeout import timeout
from discord.ext import commands

# Silence useless bug reports messages
from util.badargs import BadArgs

youtube_dl.utils.bug_reports_message = lambda: ""


class VoiceError(Exception):
    pass


class YTDLError(Exception):
    pass


class YTDLSource(discord.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        "format"            : "bestaudio/best",
        "extractaudio"      : True,
        "audioformat"       : "mp3",
        "outtmpl"           : "%(extractor)s-%(id)s-%(title)s.%(ext)s",
        "restrictfilenames" : True,
        "noplaylist"        : True,
        "nocheckcertificate": True,
        "ignoreerrors"      : False,
        "logtostderr"       : False,
        "quiet"             : True,
        "no_warnings"       : True,
        "default_search"    : "auto",
        "source_address"    : "0.0.0.0",
    }

    FFMPEG_OPTIONS = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options"       : "-vn",
    }

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 0.5):
        super().__init__(source, volume)

        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data

        self.uploader = data.get("uploader")
        self.uploader_url = data.get("uploader_url")
        date = data.get("upload_date")
        self.upload_date = date[6:8] + "." + date[4:6] + "." + date[0:4]
        self.title = data.get("title")
        self.thumbnail = data.get("thumbnail")
        self.description = data.get("description")
        self.duration = self.parse_duration(int(data.get("duration")))
        self.tags = data.get("tags")
        self.url = data.get("webpage_url")
        self.views = data.get("view_count")
        self.likes = data.get("like_count")
        self.dislikes = data.get("dislike_count")
        self.stream_url = data.get("url")

    def __str__(self):
        return f"**{self.title}** by **{self.uploader}**"

    @classmethod
    async def create_source(cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(cls.ytdl.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError(f"Couldn't find anything that matches `{search}`")

        if "entries" not in data:
            process_info = data
        else:
            process_info = None
            for entry in data["entries"]:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError(f"Couldn't find anything that matches `{search}`")

        webpage_url = process_info["webpage_url"]
        partial = functools.partial(cls.ytdl.extract_info, webpage_url, download=False)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError(f"Couldn't fetch `{webpage_url}`")

        if "entries" not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info["entries"].pop(0)
                except IndexError:
                    raise YTDLError(f"Couldn't retrieve any matches for `{webpage_url}`")

        return cls(ctx, discord.FFmpegPCMAudio(info["url"], **cls.FFMPEG_OPTIONS), data=info)

    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []

        if days > 0:
            duration.append(f"{days} days")
        if hours > 0:
            duration.append(f"{hours} hours")
        if minutes > 0:
            duration.append(f"{minutes} minutes")
        if seconds > 0:
            duration.append(f"{seconds} seconds")

        return ", ".join(duration)


class Song:
    __slots__ = ("source", "requester")

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    def create_embed(self):
        embed = discord.Embed(title="Now playing", description=f"```css\n{self.source.title}\n```", color=random.randint(0, 0xFFFFFF))
        embed.add_field(name="Duration", value=self.source.duration)
        embed.add_field(name="Requested by", value=self.requester.mention)
        embed.add_field(name="Uploader", value=f"[{self.source.uploader}]({self.source.uploader_url})")
        embed.add_field(name="URL", value=f"[Click]({self.source.url})")
        embed.set_thumbnail(url=self.source.thumbnail)
        return embed


class SongQueue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]


class VoiceState:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx

        self.current = None
        self.voice: discord.VoiceClient = None
        self.next = asyncio.Event()
        self.songs = SongQueue()

        self._loop = False
        self._volume = 0.5
        self.skip_votes = set()

        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def is_playing(self):
        return self.voice and self.current

    async def audio_player_task(self):
        while True:
            self.next.clear()

            if not self.loop:
                # Try to get the next song within 10 seconds.
                # If no song will be added to the queue in time,
                # the player will disconnect due to performance
                # reasons.
                try:
                    async with timeout(10):
                        self.current = await self.songs.get()
                except asyncio.TimeoutError:
                    self.bot.loop.create_task(self.stop())
                    return

            self.current.source.volume = self._volume
            self.voice.play(self.current.source, after=self.play_next_song)
            await self.current.source.channel.send(embed=self.current.create_embed())

            await self.next.wait()

    def play_next_song(self, error=None):
        if error:
            raise VoiceError(str(error))

        self.next.set()

    def skip(self):
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.songs.clear()

        if self.voice:
            await self.voice.disconnect()
            self.voice = None


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_states = {}
        self.voice_state = None

    def get_voice_state(self, ctx: commands.Context):
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    async def cog_before_invoke(self, ctx: commands.Context):
        self.voice_state = self.get_voice_state(ctx)

    @commands.command(hidden=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def summon(self, ctx: commands.Context, *, channel: discord.VoiceChannel = None):
        if not channel and not ctx.author.voice:
            raise VoiceError("You are neither connected to a voice channel nor specified a channel to join.")

        destination = channel or ctx.author.voice.channel
        if self.voice_state.voice:
            await self.voice_state.voice.move_to(destination)
            return

        self.voice_state.voice = await destination.connect()

    @commands.command(hidden=True, aliases=["l"])
    async def leave(self, ctx: commands.Context):
        if not self.voice_state.voice:
            return await ctx.send("Not connected to any voice channel.")

        await self.voice_state.stop()
        del self.voice_states[ctx.guild.id]

    @commands.command(hidden=True)
    async def volume(self, ctx: commands.Context, *, volume: int):
        if not self.voice_state.is_playing:
            return await ctx.send("Nothing being played at the moment.")

        if 0 > volume > 200:
            return await ctx.send("Volume must be between 0 and 200")

        self.voice_state.volume = volume / 100
        await ctx.send(f"Volume of the player set to {volume}%")

    @commands.command(hidden=True)
    async def now(self, ctx: commands.Context):
        await ctx.send(embed=self.voice_state.current.create_embed())

    @commands.command(hidden=True)
    async def pause(self, ctx: commands.Context):
        if not self.voice_state.is_playing and self.voice_state.voice.is_playing():
            self.voice_state.voice.pause()
            await ctx.message.add_reaction("⏯")

    @commands.command(hidden=True)
    async def resume(self, ctx: commands.Context):
        if not self.voice_state.is_playing and self.voice_state.voice.is_paused():
            self.voice_state.voice.resume()
            await ctx.message.add_reaction("⏯")

    @commands.command(hidden=True)
    async def stop(self, ctx: commands.Context):
        self.voice_state.songs.clear()

        if not self.voice_state.is_playing:
            self.voice_state.voice.stop()
            await ctx.message.add_reaction("⏹")

    @commands.command(hidden=True, aliases=["s"])
    async def skip(self, ctx: commands.Context):
        if not self.voice_state.is_playing:
            raise BadArgs("Not playing any music right now...")

        voter = ctx.message.author
        if voter == self.voice_state.current.requester:
            await ctx.message.add_reaction("⏭")
            self.voice_state.skip()
        elif voter.id not in self.voice_state.skip_votes:
            self.voice_state.skip_votes.add(voter.id)
            total_votes = len(self.voice_state.skip_votes)

            if total_votes >= 3:
                await ctx.message.add_reaction("⏭")
                self.voice_state.skip()
            else:
                await ctx.send(f"Skip vote added, currently at **{total_votes}/3**")

        else:
            await ctx.send("You have already voted to skip this song.")

    @commands.command(hidden=True, aliases=["q"])
    async def queue(self, ctx: commands.Context, *, page: int = 1):
        if not self.voice_state.songs:
            return await ctx.send("Empty queue.")

        items_per_page = 10
        pages = math.ceil(len(self.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ""
        for i, song in enumerate(self.voice_state.songs[start:end], start=start):
            queue += f"`{i + 1}.` [**{song.source.title}**]({song.source.url})\n"

        embed = (discord.Embed(description=f"**{len(self.voice_state.songs)} tracks:**\n\n{queue}")
                 .set_footer(text=f"Viewing page {page}/{pages}"))
        await ctx.send(embed=embed)

    @commands.command(hidden=True)
    async def shuffle(self, ctx: commands.Context):
        if len(self.voice_state.songs) == 0:
            return await ctx.send("Empty queue.")

        self.voice_state.songs.shuffle()
        await ctx.message.add_reaction("✅")

    @commands.command(hidden=True, aliases=["r"])
    async def remove(self, ctx: commands.Context, index: int):
        if len(self.voice_state.songs) == 0:
            return await ctx.send("Empty queue.")

        self.voice_state.songs.remove(index - 1)
        await ctx.message.add_reaction("✅")

    @commands.command(hidden=True)
    async def loop(self, ctx: commands.Context):
        if not self.voice_state.is_playing:
            return await ctx.send("Nothing being played at the moment.")

        # Inverse boolean value to loop and unloop.
        self.voice_state.loop = not self.voice_state.loop
        await ctx.message.add_reaction("✅")

    @commands.command(hidden=True, aliases=["p"])
    async def play(self, ctx: commands.Context, *, search: str):
        if not ctx.voice_client:
            destination = ctx.author.voice.channel
            if self.voice_state.voice:
                await self.voice_state.voice.move_to(destination)
                return

            self.voice_state.voice = await destination.connect()

        async with ctx.typing():
            try:
                source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop)
            except YTDLError as e:
                await ctx.send(f"An error occurred while processing this request: {e}", delete_after=5)
            else:
                song = Song(source)

                await self.voice_state.songs.put(song)
                await ctx.send(f"Enqueued {source}")

    @play.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise BadArgs("You are not connected to any voice channel.")

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise BadArgs("Bot is already in a voice channel.")


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Music(bot))