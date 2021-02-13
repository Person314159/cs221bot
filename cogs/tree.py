import asyncio
import glob
import math
import os
import random
import re

import discord
from binarytree import Node
from discord.ext import commands

from util.badargs import BadArgs


class Tree(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
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
                    numbers.append(int(num))
                except ValueError:
                    numbers.append(float(num))
            else:
                raise BadArgs("Please provide valid numbers for the tree.")

        if not numbers:
            raise BadArgs("Please provide some numbers for the tree.", show_help=True)

        root = Node(numbers[0])

        nodes = [root]

        def insert(subroot, num):
            if num < subroot.val:
                if not subroot.left:
                    node = Node(num)
                    subroot.left = node
                    nodes.append(node)
                else:
                    insert(subroot.left, num)
            else:
                if not subroot.right:
                    node = Node(num)
                    subroot.right = node
                    nodes.append(node)
                else:
                    insert(subroot.right, num)

        def delete(subroot, num):
            if subroot:
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
            if not get_node(num):
                insert(root, num)

        timeout = 60
        display = True

        def draw_bst(root):
            graph = root.graphviz()
            graph.render("bst", format="png")

        while True:
            if display:
                draw_bst(root)
                text = f"```{root}\n```"
                await ctx.send(text, file=discord.File("bst.png"))
                display = False

            def check(m):
                return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id

            try:
                message = await self.bot.wait_for("message", timeout=timeout, check=check)
            except asyncio.exceptions.TimeoutError:
                for f in glob.glob("bst*"):
                    os.remove(f)

                return await ctx.send("Timed out.", delete_after=5)

            command = message.content.replace(",", "").replace("!", "").lower()

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

                await ctx.send(embed=embed, file=discord.File("bst.png"))
            elif command.startswith("pause"):
                timeout = 86400
                await ctx.send("Timeout paused.")
            elif command.startswith("unpause"):
                timeout = 60
                await ctx.send("Timeout reset to 60 seconds.")
            elif command.startswith("show"):
                display = True
            elif command.startswith("insert"):
                add = []

                for entry in command[7:].split():
                    if re.fullmatch(r"[+-]?((\d+(\.\d*)?)|(\.\d+))", entry):
                        try:
                            num = int(entry)
                        except ValueError:
                            num = float(entry)
                    else:
                        continue

                    add.append(str(num))

                    if not get_node(num):
                        insert(root, num)

                await ctx.send(f"Inserted {','.join(add)}.")
                display = True
            elif command.startswith("delete"):
                remove = []

                for entry in command[7:].split():
                    try:
                        num = float(entry)
                    except Exception:
                        continue

                    if root.size == 1:
                        await ctx.send("Tree has reached one node in size. Stopping deletions.")
                        break

                    if math.modf(num)[0] == 0:
                        num = int(round(num))

                    if not get_node(num):
                        continue

                    remove.append(str(num))
                    root = delete(root, num)

                await ctx.send(f"Deleted {','.join(remove)}.")
                display = True
            elif command.startswith("exit"):
                for f in glob.glob("bst*"):
                    os.remove(f)

                return await ctx.send("Exiting.")
            elif command.startswith("bst"):
                return


def setup(bot):
    bot.add_cog(Tree(bot))
