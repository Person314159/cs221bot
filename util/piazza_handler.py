import asyncio
import datetime
import html
import re
import typing
from operator import itemgetter
from typing import List

import discord
import piazza_api.exceptions
from piazza_api import Piazza


# Exception for when a post ID is invalid or the post is private etc.
class InvalidPostID(Exception):
    """
    Exception raised when a Piazza post ID is invalid, refers to a non-existent post, or refers to a private post.
    """
    pass


class PiazzaHandler:
    """
    Handles requests to a specific Piazza network. Requires an e-mail and password, but if none are
    provided, then they will be asked for in the console (doesn't work for Heroku deploys). API is rate-limited
    (max is 55 posts in about 2 minutes?) so it's recommended to be conservative with fetch_max, fetch_min and only change them if necessary.

    All `fetch_*` functions return JSON directly from Piazza's API and all `get_*` functions parse that JSON.

    # todo missing docs for some attributes
    Attributes
    ----------
    name : `str`
        Name of class (ex. CPSC221)

    nid : `str`
        ID of Piazza forum (usually found at the end of a Piazza's home url)

    email : `str (optional)`
        Piazza log-in email

    password : `str (optional)`
        Piazza password

    guild : `discord.Guild`
        Guild assigned to the handler

    fetch_max : `int (optional)`
        Upper limit on posts fetched from Piazza.

    fetch_min: `int (optional)`
        Lower limit on posts fetched from Piazza. Used as the default value for functions that don't need to fetch a lot of posts
    """

    def __init__(self, name: str, nid: str, email: str, password: str, guild: discord.Guild, fetch_max: int = 55, fetch_min: int = 30):
        self._name = name
        self.nid = nid
        self._guild = guild
        self._channels = []
        self.url = f"https://piazza.com/class/{self.nid}"
        self.p = Piazza()
        self.p.user_login(email=email, password=password)
        self.network = self.p.network(self.nid)
        self.fetch_max = fetch_max
        self.fetch_min = fetch_min

    @property
    def piazza_url(self) -> str:
        return self.url

    @piazza_url.setter
    def piazza_url(self, url: str) -> None:
        self.url = url

    @property
    def course_name(self) -> str:
        return self._name

    @course_name.setter
    def course_name(self, name: str) -> None:
        self._name = name

    @property
    def piazza_id(self) -> str:
        return self.nid

    @piazza_id.setter
    def piazza_id(self, nid: str) -> None:
        self.nid = nid

    @property
    def channels(self) -> List[int]:
        return self._channels

    @channels.setter
    def channels(self, channels: List[int]) -> None:
        self._channels = channels

    @property
    def guild(self) -> discord.Guild:
        return self._guild

    @guild.setter
    def guild(self, guild: discord.Guild) -> None:
        self._guild = guild

    def add_channel(self, channel: int) -> None:
        if channel not in self.channels:
            self._channels.append(channel)

    def remove_channel(self, channel: int) -> None:
        if channel in self.channels:
            self._channels.remove(channel)

    def fetch_post_instance(self, post_id: int) -> dict:
        """
        Returns a JSON object representing a Piazza post with id `post_id`, or returns None if post doesn't exist

        Parameters
        ----------
        post_id : `int`
            requested post id
        """

        try:
            post = self.network.get_post(post_id)
        except piazza_api.exceptions.RequestError as ex:
            raise InvalidPostID("Post not found.") from ex

        if self.check_if_private(post):
            raise InvalidPostID("Post is Private.")

        return post

    async def fetch_recent_notes(self, lim: int = 55) -> List[dict]:
        """
        Returns up to `lim` JSON objects representing instructor's notes that were posted today

        Parameters
        ----------
        lim : `int (optional)`
            Upper limit on posts fetched. Must be in range [fetch_min, fetch_max] (inclusive)
        """

        posts = await self.fetch_posts_in_range(days=0, seconds=60 * 60 * 5, lim=lim)
        response = []

        for post in posts:
            if post["tags"][0] == "instructor-note" or post["bucket_name"] == "Pinned":
                response.append(post)

        return response

    def fetch_pinned(self, lim: int = 0) -> List[dict]:
        """
        Returns up to `lim` JSON objects representing pinned posts\n
        Since pinned posts are always the first notes shown in a Piazza, lim can be a small value.

        Parameters
        ----------
        lim : `int`
            Upper limit on posts fetched. Must be in range [fetch_min, fetch_max] (inclusive)
        """

        posts = self.network.iter_all_posts(limit=lim or self.fetch_min)
        response = []

        for post in posts:
            if self.check_if_private(post):
                continue

            if post["bucket_name"] and post["bucket_name"] == "Pinned":
                response.append(post)

        return response

    async def fetch_posts_in_range(self, days: int = 1, seconds: int = 0, lim: int = 55) -> List[dict]:
        """
        Returns up to `lim` JSON objects that represent a Piazza post posted today
        """

        if lim < 0:
            raise ValueError(f"Invalid lim for fetch_posts_in_days(): {lim}")

        posts = []

        feed = self.network.get_feed(limit=lim, offset=0)

        for cid in map(itemgetter("id"), feed["feed"]):
            post = None
            retries = 5

            while not post and retries:
                try:
                    post = self.network.get_post(cid)
                except piazza_api.exceptions.RequestError as ex:
                    retries -= 1

                    if "foo fast" in str(ex):
                        await asyncio.sleep(1)
                    else:
                        break
            if post:
                posts.append(post)

        date = datetime.date.today()
        result = []

        for post in posts:
            # [2020,9,19] from 2020-09-19T22:41:52Z
            created_at = [int(x) for x in post["created"][:10].split("-")]
            created_at = datetime.date(created_at[0], created_at[1], created_at[2])

            if self.check_if_private(post):
                continue
            elif (date - created_at).days <= days and (date - created_at).seconds <= seconds:
                result.append(post)

        return result

    def get_pinned(self) -> List[dict]:
        """
        Returns an array of `self.min` objects containing a pinned post's post id, title, and url.
        """

        posts = self.fetch_pinned()
        response = []

        for post in posts:
            post_details = {
                "num": post["nr"],
                "subject": post["history"][0]["subject"],
                "url": f"{self.url}?cid={post['nr']}",
            }
            response.append(post_details)

        return response

    def get_post(self, post_id: int) -> typing.Union[dict, None]:
        """
        Returns a dict that contains post information to be formatted and returned as an embed

        Parameters
        ----------
        post_id : `int`
            int associated with a Piazza post ID
        """

        post = self.fetch_post_instance(post_id)

        if post:
            post_type = "Note" if post["type"] == "note" else "Question"
            response = {
                "subject": self.clean_response(post["history"][0]["subject"]),
                "num": f"@{post_id}",
                "url": f"{self.url}?cid={post_id}",
                "post_type": post_type,
                "post_body": self.clean_response(self.get_body(post)),
                "i_answer": None,
                "s_answer": None,
                "num_followups": 0
            }

            answers = post["children"]

            if answers:
                num_followups = 0

                for answer in answers:
                    if answer["type"] == "i_answer":
                        response["i_answer"] = self.clean_response(self.get_body(answer))
                    elif answer["type"] == "s_answer":
                        response["s_answer"] = self.clean_response(self.get_body(answer))
                    else:
                        num_followups += self.get_num_follow_ups(answer)

                response.update({"num_followups": num_followups})

            response.update({"tags": ", ".join(post["tags"] or "None")})
            return response
        else:
            return None

    def get_num_follow_ups(self, answer: dict) -> int:
        return 1 + sum(self.get_num_follow_ups(i) for i in answer["children"])

    async def get_posts_in_range(self, show_limit: int = 10, days: int = 1, seconds: int = 0) -> List[List[dict]]:
        if show_limit < 1:
            raise ValueError(f"Invalid showLimit for get_posts_in_range(): {show_limit}")

        posts = await self.fetch_posts_in_range(days=days, seconds=seconds, lim=self.fetch_max)
        instr, stud = [], []
        response = []

        def create_post_dict(post: dict, tag: str) -> dict:
            return {
                "type": tag,
                "num": post["nr"],
                "subject": self.clean_response(post["history"][0]["subject"]),
                "url": f"{self.url}?cid={post['nr']}"
            }

        def filter_tag(post: dict, arr: List[dict], tagged: str) -> None:
            """Sorts posts by instructor or student and append it to the respective array of posts"""

            for tag in post["tags"]:
                if tag == tagged:
                    arr.append(create_post_dict(post, tag))
                    break

        # first adds all instructor notes to update, then student notes
        # for student notes, show first 10 and indicate there's more to be seen for today
        for post in posts:
            filter_tag(post, instr, "instructor-note")

        if len(posts) - len(instr) <= show_limit:
            for p in posts:
                filter_tag(p, stud, "student")
        else:
            for i in range(show_limit + 1):
                filter_tag(posts[i], stud, "student")

        response.append(instr)
        response.append(stud)
        return response

    async def get_recent_notes(self) -> List[dict]:
        """
        Fetches `fetch_min` posts, filters out non-important (not instructor notes or pinned) posts and
        returns an array of corresponding post details
        """

        posts = await self.fetch_recent_notes(lim=self.fetch_min)
        response = []

        for post in posts:
            post_details = {
                "num": post["nr"],
                "subject": self.clean_response(post["history"][0]["subject"]),
                "url": f"{self.url}?cid={post['nr']}"
            }
            response.append(post_details)

        return response

    @staticmethod
    def check_if_private(post: dict) -> bool:
        return post["status"] == "private"

    @staticmethod
    def clean_response(res: str) -> str:
        if len(res) > 1024:
            res = res[:1000]
            res += "...\n\n *(Read more)*"

        tag_regex = re.compile("<.*?>")
        res = html.unescape(re.sub(tag_regex, "", res))

        if len(res) < 1:
            res += "An image or video was posted in response."

        return res

    @staticmethod
    def get_body(res: dict) -> str:
        body = res["history"][0]["content"]

        if not body:
            raise Exception("Body not found.")

        return body
