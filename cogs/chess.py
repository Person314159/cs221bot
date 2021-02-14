from discord.ext import commands


POS = {'a': 0, 'b': 1, 'c': 2, 'd': 3, 'e': 4, 'f': 5, 'g': 6, 'h': 7}


class Chess(commands.Cog, name="chess"):
    board = []
    w = 8
    h = 8
    turn = False

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="chessreset")
    @commands.cooldown(1, 5, commands.BucketType.default)
    async def chessreset(self, ctx):
        self.board = [[0 for x in range(self.w)] for y in range(self.h)]
        for y in range(0, 2):
            for x in range(y % 2, 8, 2):
                self.board[x][y] = 2
        for y in range(6, 8):
            for x in range(y % 2, 8, 2):
                self.board[x][y] = 1
        msg = self.print_board()
        await ctx.send(msg)

    @commands.command(name="chess")
    @commands.cooldown(1, 5, commands.BucketType.default)
    async def chess(self, ctx, arg1, *args):
        try:
            left = POS[arg1[0]]
            top = 7 - (int(arg1[1]) - 1)
        except KeyError as e:
            await ctx.send("incorrect input")
            return

        for i in range(len(args)):
            try:
                left_d = POS[args[i][0]]
                top_d = 7-(int(args[i][1])-1)
            except KeyError as e:
                await ctx.send("incorrect input")
                return
            await ctx.send(str(left) + " " + str(top) + " to " + str(left_d) + " " + str(top_d))
            self.move(left, top, left_d, top_d)
            left = left_d
            top = top_d
        self.turn = not self.turn
        msg = self.print_board()
        await ctx.send(msg)

    def move(self, x1, y1, x2, y2):
        if self.turn:
            color = 2
            opponent_color = 1
            sign = 1
        else:
            color = 1
            opponent_color = 2
            sign = -1

        if x1 < 0 or y1 < 0 or x1 > self.w or y1 > self.h or x2 < 0 or y2 < 0 or x2 > self.w or y2 > self.h:
            return

        if self.board[x1][y1] != color or self.board[x2][y2] != 0:
            return

        if (y2 - y1) * sign == 2:
            if x2 - x1 == 2:
                if self.board[(x1 + 1)][y1+sign] == opponent_color:
                    self.board[x1][y1] = 0
                    self.board[x2][y2] = color
                    self.board[(x1 + 1)][y1 + sign] = 0
                    return
                else:
                    return
            elif x2 - x1 == -2:
                if self.board[(x1 - 1)][y1+sign] == opponent_color:
                    self.board[x1][y1] = 0
                    self.board[x2][y2] = color
                    self.board[(x1 - 1)][y1 + sign] = 0
                    return
                else:
                    return
        elif (y2 - y1) * sign == 1:
            self.board[x1][y1] = 0
            self.board[x2][y2] = color
            return

    def print_board(self):
        res = "```"
        for y in range(0, 8):
            res = res + str(8-y) + "| "
            for x in range(0, 8):
                res = res + str(self.board[x][y]) + " "
            res += "\n"
        res = res + "   _______________\n"
        res = res + "   a b c d e f g h\n"
        res += "```"
        return res


def setup(bot):
    bot.add_cog(Chess(bot))
