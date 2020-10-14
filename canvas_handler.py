import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union

import dateutil.parser.isoparser
import discord
import pytz
from bs4 import BeautifulSoup
from canvasapi.assignment import Assignment
from canvasapi.canvas import Canvas
from canvasapi.course import Course
from canvasapi.paginated_list import PaginatedList

from extra_func import get_course_stream, get_course_url


class CanvasHandler(Canvas):
    """
    Represents a handler for Canvas information for a guild

    Attributes
    ----------
    courses : `List[canvasapi.Course]`
        Courses tracked in guild mode.

    guild : `discord.Guild`
        Guild assigned to this handler.

    timings : `Dict[str, str]`
        Contains course and its last announcement date and time.

    due_week : `Dict[str, List[str]]`
        Contains course and assignment ids due in less than a week.

    due_day : `Dict[str, List[str]]`
        Contains course and assignment ids due in less than a day.
    """

    def __init__(self, API_URL, API_KEY, guild: discord.Guild):
        """
        Parameters
        ----------
        API_URL : `str`
            Base URL of the Canvas instance's API

        API_KEY : `str`
            API key to authenticate requests with

        guild : `discord.Guild`
            Guild to assign to this handler
        """

        super().__init__(API_URL, API_KEY)
        self._courses: List[Course] = []
        self._guild = guild
        self._live_channels: List[discord.TextChannel] = []
        self._timings: Dict[str, str] = {}
        self._due_week: Dict[str, List[str]] = {}
        self._due_day: Dict[str, List[str]] = {}

    @property
    def courses(self) -> List[Course]:
        return self._courses

    @courses.setter
    def courses(self, courses: List[Course]):
        self._courses = courses

    @property
    def guild(self) -> discord.Guild:
        return self._guild

    @property
    def live_channels(self):
        return self._live_channels

    @live_channels.setter
    def live_channels(self, live_channels):
        self._live_channels = live_channels

    @property
    def timings(self):
        return self._timings

    @timings.setter
    def timings(self, timings):
        self._timings = timings

    @property
    def due_week(self):
        return self._due_week

    @due_week.setter
    def due_week(self, due_week):
        self._due_week = due_week

    @property
    def due_day(self):
        return self._due_day

    @due_day.setter
    def due_day(self, due_day):
        self._due_day = due_day

    @staticmethod
    def _ids_converter(ids: Tuple[str, ...]) -> List[int]:
        """
        Converts list of string to list of int, removes duplicates

        Parameters
        ----------
        ids : `Tuple[str, ...]`
            Tuple of string ids

        Returns
        -------
        `List[int]`
            List of int ids
        """

        temp = []

        for i in ids:
            temp.append(int(i))

        temp = list(dict.fromkeys(temp))
        return temp

    def track_course(self, course_ids_str: Tuple[str, ...]):
        """
        Adds course(s) to track

        Parameters
        ----------
        course_ids_str : `Tuple[str, ...]`
            Tuple of course ids
        """

        course_ids = self._ids_converter(course_ids_str)

        for i in course_ids:
            c_ids = [c.id for c in self.courses]

            if i not in c_ids:
                self.courses.append(self.get_course(i))

        for c in course_ids_str:
            if c not in self.timings:
                self.timings[c] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if c not in self.due_week:
                self.due_week[c] = []

            if c not in self.due_day:
                self.due_day[c] = []

    def untrack_course(self, course_ids_str: Tuple[str, ...]):
        """
        Untracks course(s)

        Parameters
        ----------
        course_ids_str : `Tuple[str, ...]`
            Tuple of course ids
        """

        course_ids = self._ids_converter(course_ids_str)

        for i in course_ids:
            c_ids = [c.id for c in self.courses]

            if i in c_ids:
                del self.courses[c_ids.index(i)]

        for c in course_ids_str:
            if c in self.timings:
                self.timings.pop(c)

            if c in self.due_week:
                self.due_week.pop(c)

            if c in self.due_day:
                self.due_day.pop(c)

    def get_course_stream_ch(self, since: Optional[str], course_ids_str: Tuple[str, ...], base_url, access_token) -> List[List[str]]:
        """
        Gets announcements for course(s)

        Parameters
        ----------
        since : `None or str`
            Date/Time from announcement creation to now

        course_ids_str : `Tuple[str, ...]`
            Tuple of course ids

        base_url : `str`
            Base URL of the Canvas instance's API

        access_token : `str`
            API key to authenticate requests with

        Returns
        -------
        `List[List[str]]`
            List of announcement data to be formatted and sent as embeds
        """

        course_ids = self._ids_converter(course_ids_str)

        course_stream_list = []

        for c in self.courses:
            if course_ids:
                if c.id in course_ids:
                    course_stream_list.append(get_course_stream(c.id, base_url, access_token))
            else:
                course_stream_list.append(get_course_stream(c.id, base_url, access_token))

        data_list = []

        for course_stream in course_stream_list:
            for item in course_stream:
                if item["type"] in ["Conversation"]:
                    course = self.get_course(item["course_id"])

                    course_name = course.name
                    course_url = get_course_url(course.id, base_url)

                    title = "Announcement: " + item["title"]

                    url = "https://canvas.ubc.ca/conversations?#filter=type=inbox&course=course_53540"

                    desc = item["latest_messages"][0]["message"]
                    short_desc = "\n".join(desc.split("\n")[:4])

                    ctime_iso = item["created_at"]
                    time_shift = datetime.now() - datetime.utcnow()

                    if ctime_iso is None:
                        ctime_text = "No info"
                    else:
                        ctime_iso_parsed = (dateutil.parser.isoparse(ctime_iso) + time_shift).replace(tzinfo=None)
                        ctime_timedelta = ctime_iso_parsed - datetime.now()

                        if since is not None:
                            if ctime_timedelta < -self._make_timedelta(since):
                                # since announcements are in order
                                break

                        ctime_text = ctime_iso_parsed.strftime("%Y-%m-%d %H:%M:%S")

                    data_list.append([course_name, course_url, title, url, short_desc, ctime_text, course.id])

        return data_list

    def get_assignments(self, due: Optional[str], course_ids_str: Tuple[str, ...], base_url) -> List[List[str]]:
        """
        Gets assignments for course(s)

        Parameters
        ----------
        due : `None or str`
            Date/Time from due date of assignments

        course_ids_str : `Tuple[str, ...]`
            Tuple of course ids

        base_url : `str`
            Base URL of the Canvas instance's API

        Returns
        -------
        `List[List[str]]`
            List of assignment data to be formatted and sent as embeds
        """

        courses_assignments = []
        course_ids = self._ids_converter(course_ids_str)

        for c in self.courses:
            if course_ids:
                if c.id in course_ids:
                    courses_assignments.append([c, c.get_assignments()])
            else:
                courses_assignments.append([c, c.get_assignments()])

        return self._get_assignment_data(due, courses_assignments, base_url)

    def _get_assignment_data(self, due: Optional[str], courses_assignments, base_url: str) -> List[List[str]]:
        """
        Formats all courses assignments as separate assignments"

        Parameters
        ----------
        due : `None or str`
            Date/Time from due date of assignments

        courses_assignments : `List[canvasapi.Course, PaginatedList[canvasapi.Assignment]]`
            List of courses and their assignments

        base_url : `str`
            Base URL of the Canvas instance's API

        Returns
        -------
        `List[List[str]]`
            List of assignment data to be formatted and sent as embeds
        """

        data_list = []

        for course_assignments in courses_assignments:
            course = course_assignments[0]
            course_name = course.name

            for assignment in course_assignments[1]:
                course_url = get_course_url(course.id, base_url)

                ass_id = assignment.__getattribute__("id")

                title = "Assignment: " + assignment.__getattribute__("name")

                url = assignment.__getattribute__("html_url")

                desc_html = assignment.__getattribute__("description")

                if desc_html is None:
                    desc_html = "No description"

                desc_soup = BeautifulSoup(desc_html, "html.parser")
                short_desc = "\n".join(desc_soup.get_text().split("\n")[:4])

                ctime_iso = assignment.__getattribute__("created_at")
                dtime_iso = assignment.__getattribute__("due_at")

                time_shift = datetime.now() - datetime.utcnow()

                if ctime_iso is None:
                    ctime_text = "No info"
                else:
                    ctime_text = (dateutil.parser.isoparse(ctime_iso) + time_shift).strftime("%Y-%m-%d %H:%M:%S")

                if dtime_iso is None:
                    dtime_text = "No info"
                else:
                    dtime_iso_parsed = (dateutil.parser.isoparse(dtime_iso) + time_shift).replace(tzinfo=None)
                    dtime_timedelta = dtime_iso_parsed - datetime.now()

                    if dtime_timedelta < timedelta(0):
                        continue

                    if due is not None:
                        if dtime_timedelta > self._make_timedelta(due):
                            # since assignments are not in order
                            continue

                    dtime_text = dtime_iso_parsed.strftime("%Y-%m-%d %H:%M:%S")

                data_list.append([course_name, course_url, title, url, short_desc, ctime_text, dtime_text, course.id, ass_id])

        return data_list

    @staticmethod
    def _make_timedelta(till_str: str) -> timedelta:
        """
        Makes a datetime.timedelta

        Parameters
        ----------
        till : `str`
            Date/Time from due date of assignments

        Returns
        -------
        `datetime.timedelta`
            Time delta between till and now
        """

        till = re.split(r"[-:]", till_str)

        if till[1] in ["hour", "day", "week", "month", "year"]:
            num = float(till[0])
            options = {
                "hour": timedelta(hours=num),
                "day": timedelta(days=num),
                "week": timedelta(weeks=num),
                "month": timedelta(days=30*num),
                "year": timedelta(days=365*num)
            }

            return abs(options[till[1]])
        elif len(till) == 3:
            year = int(till[0])
            month = int(till[1])
            day = int(till[2])
            return abs(datetime(year, month, day) - datetime.now())
        else:
            year = int(till[0])
            month = int(till[1])
            day = int(till[2])
            hour = int(till[3])
            minute = int(till[4])
            second = int(till[5])
            return abs(datetime(year, month, day, hour, minute, second) - datetime.now())

    def get_course_names(self, url) -> List[List[str]]:
        """
        Gives a list of tracked courses and their urls

        Parameters
        ----------
        url : `str`
            Base URL of the Canvas instance's API

        Returns
        -------
        `List[List[str]]`
            List of course names and their page urls
        """

        course_names = []

        for c in self.courses:
            course_names.append([c.name, get_course_url(c.id, url)])

        return course_names
