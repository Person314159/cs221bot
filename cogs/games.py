import asyncio
import random
from datetime import datetime
from io import BytesIO

import chess
import discord
from cairosvg import svg2png
from chess import pgn, svg
from discord.ext import commands
from discord.ext.commands import BadArgument, MemberConverter


class Games(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def chess(self, ctx: commands.Context, *args: str):
        """
        `!chess` __`Play chess`__

        **Usage:** !chess <user>

        **Examples:**
        `!chess abc#1234` starts a game of chess with abc#1234

        **Note:**
        Moves are in standard algebraic notation (e4, Nxf7, etc).
        """

        try:
            user = await MemberConverter().convert(ctx, " ".join(args))
        except BadArgument:
            return await ctx.send("That user doesn't exist.", delete_after=5)

        board = chess.Board()
        game = pgn.Game()
        node = None
        players = [ctx.author, user]
        random.shuffle(players)
        turn = chess.WHITE
        game.headers["Date"] = datetime.today().strftime("%Y.%m.%d")
        game.headers["White"] = players[chess.WHITE].display_name
        game.headers["Black"] = players[chess.BLACK].display_name

        def render_board(board: chess.Board) -> BytesIO:
            boardimg = chess.svg.board(board=board, lastmove=board.peek() if board.move_stack else None, check=board.king(turn) if board.is_check() or board.is_checkmate() else None, flipped=board.turn == chess.BLACK)
            res = BytesIO()
            svg2png(bytestring=boardimg, write_to=res)
            res.seek(0)
            return res

        res = render_board(board)
        game_msg = await ctx.send(f"{players[turn].mention}, its your turn.", file=discord.File(res, "file.png"))

        while True:
            try:
                msg = await self.bot.wait_for("message", timeout=600, check=lambda msg: msg.channel == ctx.channel and msg.author.id == players[turn].id)
            except asyncio.TimeoutError:
                return await ctx.send("Timed out.", delete_after=5)

            if msg.content == "exit":
                res = render_board(board)
                game.headers["Result"] = "0-1" if turn == chess.WHITE else "1-0"
                await game_msg.delete()
                return await ctx.send(f"{players[turn].mention} resigned. {players[not turn].mention} wins.\n{str(game)}", file=discord.File(res, "file.png"))

            try:
                move = board.push_san(msg.content)
            except ValueError:
                continue

            await msg.delete()

            if not node:
                node = game.add_variation(move)
            else:
                node = node.add_variation(move)

            res = render_board(board)
            await game_msg.delete()

            if board.outcome() is not None:
                game.headers["Result"] = board.outcome().result()

                if board.is_checkmate():
                    return await ctx.send(f"Checkmate!\n\n{players[not turn].mention} wins.\n{str(game)}", file=discord.File(res, "file.png"))
                else:
                    return await ctx.send(f"Draw!\n{str(game)}", file=discord.File(res, "file.png"))

            turn = not turn
            game_msg = await ctx.send(f"{players[turn].mention}, its your turn." + ("\n\nCheck!" if board.is_check() else ""), file=discord.File(res, "file.png"))


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Games(bot))
