import datetime
import typing

import regex
import html
from typing import List
from piazza_api import Piazza


class PiazzaHandler:
    """Handles requests to a specific Piazza network. Requires an e-mail and password, but if none are
    provided, then they will be asked for in the console (doesn't work for Heroku deploys). API is rate-limited
    (limit is still unknown) so it's recommended to be conservative with FETCH_MAX, FETCH_MIN and only change them if necessary.

    All `fetch_*` functions return JSON directly from Piazza's API and all `get_*` functions parse that JSON.

    Attributes
    ----------
    NAME : `str`
        Name of class (ex. CPSC221)

    ID : `int`
        ID of Piazza forum (usually found at the end of a Piazza's home url)

    EMAIL : `str (optional)`
        Piazza log-in email

    PASSWORD : `str (optional)`
        Piazza password

    GUILD : `discord.Guild`
        Guild assigned to the handler

    FETCH_MAX : `int (optional)`
        Upper limit on posts fetched from Piazza.

    FETCH_MIN: `int (optional)`
        Lower limit on posts fetched from Piazza. Used as the default value for functions that don't need to fetch a lot of posts
    """

    def __init__(self, NAME, ID, EMAIL, PASSWORD, GUILD, FETCH_MAX=60, FETCH_MIN=30):
        self.name = NAME
        self.nid = ID
        self._guild = GUILD
        self._channels = []
        self.url = f"https://piazza.com/class/{self.nid}"
        self.p = Piazza()
        self.p.user_login(email=EMAIL, password=PASSWORD)
        self.network = self.p.network(self.nid)
        self.max = FETCH_MAX
        self.min = FETCH_MIN

    @property
    def piazza_url(self):
        return self.url

    @piazza_url.setter
    def piazza_url(self, url):
        self.url = url

    @property
    def course_name(self):
        return self.name

    @course_name.setter
    def course_name(self, name):
        self.name = name

    @property
    def piazza_id(self):
        return self.nid

    @piazza_id.setter
    def piazza_id(self, nid):
        self.nid = nid

    @property
    def guild(self):
        return self._guild

    @guild.setter
    def guild(self, guild):
        self._guild = guild

    @property
    def channels(self):
        return self._channels

    @channels.setter
    def channels(self, channels):
        self._channels = channels

    def add_channel(self, channel):
        if channel not in self._channels:
            self._channels.append(channel)

    def fetch_post_instance(self, postID) -> dict:
        """
        Returns a JSON object representing a Piazza post with ID `postID`, or returns None if post doesn't exist

        Parameters
        ----------
        postID : `int`
            requested post ID
        """
        post = self.network.get_post(postID)

        if self.checkIfPrivate(post):
            raise Exception("Post not found.")

        return post

    def fetch_recent_notes(self, lim=100) -> List[dict]:
        """
        Returns up to `lim` JSON objects representing instructor's notes that were posted today

        Parameters
        ----------
        lim : `int (optional)`
            Upper limit on posts fetched. Must be in range [FETCH_MIN, FETCH_MAX] (inclusive)
        """
        posts = self.fetch_posts_in_range(seconds=60*60*5, lim=lim)
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
            Upper limit on posts fetched. Must be in range [FETCH_MIN, FETCH_MAX] (inclusive)
        """
        posts = self.network.iter_all_posts(limit=lim or self.min)
        response = []

        for post in posts:
            if self.checkIfPrivate(post):
                continue

            if post["bucket_name"] and post["bucket_name"] == "Pinned":
                response.append(post)

        return response

    def fetch_posts_in_range(self, days=1, seconds=0, lim=100) -> List[dict]:
        """
        Returns up to `lim` JSON objects that represent a Piazza post posted today
        """
        if lim < 0:
            raise Exception(f"Invalid lim for fetch_posts_in_days(): {lim}")

        posts = self.network.iter_all_posts(limit=min(self.max, lim))
        date = datetime.date.today()
        result = []

        for post in posts:
            # [2020,9,19] from 2020-09-19T22:41:52Z
            created_at = [int(x) for x in post["created"][:10].split("-")]
            created_at = datetime.date(created_at[0], created_at[1], created_at[2])

            if self.checkIfPrivate(post):
                continue
            elif (date - created_at).days <= days and (date-created_at).seconds <= seconds:
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

    def get_post(self, postID) -> typing.Union[dict, None]:
        """
        Returns a dict that contains post information to be formatted and returned as an embed

        Parameters
        ----------
        postID : `int`
            int associated with a Piazza post ID
        """
        post = self.fetch_post_instance(postID)

        if post:
            postType = "Note" if post["type"] == "note" else "Question"
            response = {
                "subject": post["history"][0]["subject"],
                "num": f"@{postID}",
                "url": f"{self.url}?cid={postID}",
                "post_type": postType,
                "post_body": self.clean_response(self.get_body(post)),
                "ans_type": "",
                "ans_body": "",
                "more_answers": False,
                "num_answers": 0
            }

            answers = post["children"]
            answerHeading, answerBody = "", ""

            if answers:
                answer = answers[0]

                if answer["type"] == "followup":
                    if answers[1]["type"] == "followup":
                        answerHeading = "Follow-up Post"
                        answerBody = answer["subject"]
                    else:
                        answerHeading = "Instructor Answer" if answer["type"] == "i_answer" else "Student Answer"
                        answerBody = self.clean_response(self.get_body(answers[1]))
                else:
                    answerHeading = "Instructor Answer" if answer["type"] == "i_answer" else "Student Answer"
                    answerBody = self.clean_response(self.get_body(answer))

                if len(answers) > 1:
                    response.update({"more_answers": True})
                    response.update({"num_answers": len(answers)})
            else:
                answerHeading = "Answers"
                answerBody = "No answers yet :("

            response.update({"ans_type": answerHeading})
            response.update({"ans_body": answerBody})
            response.update({"tags": ", ".join(post["tags"] if post["tags"] else "None")})
            return response
        else:
            return None

    def get_posts_in_range(self, showLimit=10, days=1, seconds=0) -> List[List[dict]]:
        if showLimit < 1:
            raise Exception(f"Invalid showLimit for get_posts_in_range(): {showLimit}")

        posts = self.fetch_posts_in_range(days=days, seconds=seconds, lim=self.max)
        instr, stud = [], []
        response = []

        def create_post_dict(post, tag) -> dict:
            return {
                "type": tag,
                "num": post["nr"],
                "subject": self.clean_response(post["history"][0]["subject"]),
                "url": f"{self.url}?cid={post['nr']}"
            }

        def filter_tag(post, arr, tagged):
            """Sorts posts by instructor or student and append it to the respective array of posts"""

            for tag in post["tags"]:
                if tag == tagged:
                    arr.append(create_post_dict(post, tag))
                    break

        # first adds all instructor notes to update, then student notes
        # for student notes, show first 10 and indicate there's more to be seen for today
        for post in posts:
            filter_tag(post, instr, "instructor-note")

        if len(posts) - len(instr) <= showLimit:
            for p in posts:
                filter_tag(p, stud, "student")
        else:
            for i in range(showLimit + 1):
                filter_tag(posts[i], stud, "student")

        response.append(instr)
        response.append(stud)
        return response

    def get_recent_notes(self) -> List[dict]:
        """
        Fetches `FETCH_MIN` posts, filters out non-important (not instructor notes or pinned) posts and
        returns an array of corresponding post details
        """
        posts = self.fetch_recent_notes(lim=self.min)
        response = []

        for post in posts:
            post_details = {
                "num": post["nr"],
                "subject": self.clean_response(post["history"][0]["subject"]),
                "url": f"{self.url}?cid={self.nid}"
            }
            response.append(post_details)

        return response

    @staticmethod
    def checkIfPrivate(post) -> bool:
        return post["status"] == "private" or post["change_log"][0]["v"] == "private"

    @staticmethod
    def clean_response(res):
        if len(res) > 1024:
            res = res[:1000]
            res += "...\n\n *(Read more)*"

        tagRegex = regex.compile("<.*?>")
        res = html.unescape(regex.sub(tagRegex, "", res))

        if len(res) < 1:
            res += "An image or video was posted in response."

        return res

    @staticmethod
    def get_body(res):
        body = res["history"][0]["content"]

        if not body:
            raise Exception("Body not found.")

        return body
