import asyncio
import math
import random
import re
from io import BytesIO

import discord
from binarytree import Node
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from util.badargs import BadArgs


class Tree(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def bst(self, ctx):
        """
        `!bst` __`Binary Search Tree analysis tool`__
        **Usage:** !bst <node> [node] [...]
        **Examples:**
        `!bst 2 1 3` displays a BST in ASCII and PNG form with root node 2 and leaves 1, 3
        `!bst 4 5 6` displays a BST in ASCII and PNG form with root node 4, parent node 5 and leaf 6

        Launching the command activates a 60 second window during which additional unprefixed commands can be called:

        `pre`        displays pre-order traversal of the tree
        `in`         displays in-order traversal of the tree
        `level`      displays level-order traversal of the tree
        `post`       displays post-order traversal of the tree
        `about`      displays characteristics of the tree
        `pause`      stops the 60 second countdown timer
        `unpause`    starts the 60 second countdown timer
        `show`       displays the ASCII and PNG representations of the tree again
        `exit`       exits the window

        `insert <node> [node] [...]` inserts nodes into the tree
        **Example:** `insert 5 7 6`  inserts nodes 5, 7 and 6, in that order

        `delete <node> [node] [...]` deletes nodes from the tree
        **Example:** `delete 7 8 9`  deletes nodes 7, 8 and 9, in that order
        """

        numbers = []

        for num in ctx.message.content[5:].replace(",", "").split():
            if re.fullmatch(r"[+-]?((\d+(\.\d*)?)|(\.\d+))", num):
                try:
                    numbers.append(int(round(float(num))))
                except ValueError:
                    numbers.append(float(num))
            else:
                raise BadArgs("Please provide valid numbers for the tree.")

        if not numbers:
            raise BadArgs("Please provide some numbers for the tree.", show_help=True)

        root = Node(numbers[0])

        nodes = [root]
        highlighted = []

        def insert(subroot, num, highlight=False):
            if num in root.values:
                return

            if highlight:
                highlighted.append(subroot.val)

            if num < subroot.val:
                if not subroot.left:
                    subroot.left = Node(num)

                    if highlight:
                        highlighted.append(num)

                    nodes.append(subroot.left)
                else:
                    insert(subroot.left, num, highlight)
            elif num > subroot.val:
                if not subroot.right:
                    subroot.right = Node(num)

                    if highlight:
                        highlighted.append(num)

                    nodes.append(subroot.right)
                else:
                    insert(subroot.right, num, highlight)

        def delete(subroot, num):
            if subroot is not None:
                if subroot.val == num:
                    if subroot.left is not None and subroot.right is not None:
                        parent = subroot
                        predecessor = subroot.left

                        while predecessor.right is not None:
                            parent = predecessor
                            predecessor = predecessor.right

                        if parent.right == predecessor:
                            parent.right = predecessor.left
                        else:
                            parent.left = predecessor.left

                        predecessor.left = subroot.left
                        predecessor.right = subroot.right

                        ret = predecessor
                    else:
                        if subroot.left is not None:
                            ret = subroot.left
                        else:
                            ret = subroot.right

                    nodes.remove(subroot)
                    del subroot
                    return ret
                else:
                    if subroot.val > num:
                        if subroot.left:
                            subroot.left = delete(subroot.left, num)
                    else:
                        if subroot.right:
                            subroot.right = delete(subroot.right, num)

            return subroot

        def get_node(num):
            for node in nodes:
                if node.val == num:
                    return node

            return None

        for num in numbers[1:]:
            insert(root, num)

        timeout = 60
        display = True
        filex = None
        text = ""

        while True:
            if display:
                if root.height > 8:
                    raise BadArgs("Tree is too high to reasonably display. Exiting.")

                entries = list(filter(lambda x: x[0] is not None, [[b, i] for b, i in zip(root.values, range(1, len(root.values) + 1))]))
                levels = root.height + 1
                fsize = max(10, 60 - 7 * root.height)
                font = ImageFont.truetype("boxfont_round.ttf", fsize)

                radius = max(10, 100 - 10 * root.height)
                width = 2 * radius * (2 ** (root.height + 1))
                height = 2 * radius * (root.height + 2)
                basey = height // (levels + 1)

                text = f"```{root}\n```"
                smallest = [math.inf, 1]

                for entry in entries:
                    if entry[0] < smallest[0]:
                        smallest = entry

                reflevel = math.floor(math.log(smallest[1], 2))
                basex = width // (2 ** reflevel + 1)
                refx = int(basex - 2 * radius)

                if basex != width // 2:
                    refx = 0
                    offset = 0
                else:
                    offset = radius

                image = Image.new("RGBA", (width - refx - offset, height), (255, 255, 255, 255))
                layer = Image.new("RGBA", (width - refx - offset, height), (0, 0, 0, 0))
                drawing = ImageDraw.Draw(image)
                drawing2 = ImageDraw.Draw(layer)
                currentlevel = 2
                x = width // 2
                y = basey * currentlevel

                if root.val in highlighted:
                    col = (0, 128, 128, 255)
                else:
                    col = (0, 0, 255, 255)

                drawing2.ellipse([(x - radius - refx, basey - radius), (x + radius - refx, basey + radius)], fill=col, outline=(0, 0, 0, 255))
                ln = drawing2.textsize(str(root.val), font=font)[0] / 2
                drawing2.text((x - refx - fsize // 2 - ln, basey - fsize // 2), str(root.val), fill=(255, 168, 0, 255), font=font)

                for entry in entries[1:]:
                    await asyncio.sleep(0)

                    if math.floor(math.log(entry[1], 2)) > currentlevel - 1:
                        currentlevel += 1
                        y = basey * currentlevel

                    multiplier = entry[1] - 2 ** (currentlevel - 1) + 1
                    basex = width // (2 ** (currentlevel - 1) + 1)
                    x = basex * multiplier
                    prevx = width // (2 ** (currentlevel - 2) + 1)
                    prevx *= (multiplier + 1) // 2

                    if entry[0] in highlighted:
                        col = (0, 128, 128, 255)
                        linecol = col
                    else:
                        col = (0, 0, 255, 255)
                        linecol = (0, 0, 0, 255)

                    drawing.line([(prevx - refx, basey * (currentlevel - 1)), (x - refx, y)], fill=linecol, width=7)
                    drawing2.ellipse([(x - radius - refx, y - radius), (x + radius - refx, y + radius)], fill=col, outline=(0, 0, 0, 255))
                    ln = drawing2.textsize(str(entry[0]), font=font)[0] / 2
                    drawing2.text((x - refx - fsize // 2 - ln, y - fsize // 2), str(entry[0]), fill=(255, 168, 0, 255), font=font)

                image.alpha_composite(layer)
                filex = BytesIO()
                image.save(filex, "PNG", optimize=True)
                filex.seek(0)
                await ctx.send("> " + text.replace("\n", "\n> "), file=discord.File(filex, "bst.png"))
                display = False
                highlighted = []

            def check(m):
                return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id

            try:
                message = await self.bot.wait_for("message", timeout=timeout, check=check)
            except asyncio.exceptions.TimeoutError:
                return

            command = message.content.replace(",", "").replace("!", "").lower()
            timeout = 60

            if command.startswith("level"):
                await ctx.send("Level-Order Traversal:\n**" + "  ".join([str(n.val) for n in root.levelorder]) + "**")
            elif command.startswith("pre"):
                await ctx.send("Pre-Order Traversal:\n**" + "  ".join([str(n.val) for n in root.preorder]) + "**")
            elif command.startswith("post"):
                await ctx.send("Post-Order Traversal:\n**" + "  ".join([str(n.val) for n in root.postorder]) + "**")
            elif command.startswith("in") and not command.startswith("ins"):
                await ctx.send("In-Order Traversal:\n**" + "  ".join([str(n.val) for n in root.inorder]) + "**")
            elif command.startswith("about"):
                embed = discord.Embed(title="Binary Search Tree Info", description="> " + text.replace("\n", "\n> "), color=random.randint(0, 0xffffff))
                embed.add_field(name="Height:", value=str(root.height))
                embed.add_field(name="Balanced?", value=str(root.is_balanced))
                embed.add_field(name="Complete?", value=str(root.is_complete))
                embed.add_field(name="Full?", value=str(root.is_strict))
                embed.add_field(name="Perfect?", value=str(root.is_perfect))
                embed.add_field(name="Number of leaves:", value=str(root.leaf_count))
                embed.add_field(name="Max Leaf Depth:", value=str(root.max_leaf_depth))
                embed.add_field(name="Min Leaf Depth:", value=str(root.min_leaf_depth))
                embed.add_field(name="Max Node Value:", value=str(root.max_node_value))
                embed.add_field(name="Min Node Value:", value=str(root.min_node_value))
                embed.add_field(name="Entries:", value=str(root.size))
                embed.add_field(name="Pre-Order Traversal:", value=" ".join([str(n.val) for n in root.preorder]))
                embed.add_field(name="In-Order Traversal:", value=" ".join([str(n.val) for n in root.inorder]))
                embed.add_field(name="Level-Order Traversal:", value=" ".join([str(n.val) for n in root.levelorder]))
                embed.add_field(name="Post-Order Traversal:", value=" ".join([str(n.val) for n in root.postorder]))

                if root.left:
                    embed.add_field(name="In-Order Predecessor:", value=max(filter(lambda x: x is not None, root.left.values)))

                if root.right:
                    embed.add_field(name="In-Order Successor:", value=min(filter(lambda x: x is not None, root.right.values)))

                filex.seek(0)
                await ctx.send(embed=embed, file=discord.File(filex, "bst.png"))
            elif command.startswith("pause"):
                timeout = 86400
                await ctx.send("Timeout paused.")
            elif command.startswith("unpause"):
                timeout = 60
                await ctx.send("Timeout reset to 60 seconds.")
            elif command.startswith("show"):
                display = True
            elif command.startswith("insert"):
                for entry in command[7:].split():
                    try:
                        num = float(entry)
                    except Exception as e:
                        await ctx.send(str(e))
                    else:
                        if math.modf(num)[0] == 0:
                            num = int(round(num))

                        insert(root, num, highlight=True)

                display = True
            elif command.startswith("delete"):
                delet = []

                for entry in command[7:].split():
                    try:
                        num = float(entry)
                    except Exception:
                        pass
                    else:
                        if root.size == 1:
                            await ctx.send("Tree has reached one node in size. Stopping deletions.")
                            break

                        if math.modf(num)[0] == 0:
                            num = int(round(num))

                        if not get_node(num):
                            continue

                        delet.append(str(num))

                        root = delete(root, num)

                await ctx.send(f"Deleted {','.join(delet)}.")
                display = True
            elif command.startswith("exit"):
                return await ctx.send("Exiting.")
            elif command.startswith("bst"):
                return


def setup(bot):
    bot.add_cog(Tree(bot))
