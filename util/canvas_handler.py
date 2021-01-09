import os
import re
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Union

import dateutil.parser.isoparser
import discord
from bs4 import BeautifulSoup
from canvasapi.canvas import Canvas
from canvasapi.course import Course
from canvasapi.module import Module, ModuleItem
from canvasapi.paginated_list import PaginatedList

from util import create_file
from util.canvas_api_extension import get_course_stream, get_course_url

# Stores course modules and channels that are live tracking courses
# Do *not* put a slash at the end of this path
COURSES_DIRECTORY = "./data/courses"

CINDA_CANVAS_ID = 1073


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

    due_week : `Dict[str, List[int]]`
        Contains course and assignment ids due in less than a week.

    due_day : `Dict[str, List[int]]`
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
        self._due_week: Dict[str, List[int]] = {}
        self._due_day: Dict[str, List[int]] = {}

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
    def _ids_converter(ids: Tuple[str]) -> Set[int]:
        """
        Converts tuple of string to set of int, removing duplicates. Each string
        must be parsable to an int.

        Parameters
        ----------
        ids : `Tuple[str]`
            Tuple of string ids

        Returns
        -------
        `Set[int]`
            List of int ids
        """

        return set(int(i) for i in ids)

    def track_course(self, course_ids_str: Tuple[str], get_unpublished_modules: bool):
        """
        Cause this CanvasHandler to start tracking the courses with given IDs.

        For each course, if the bot is tracking the course for the first time,
        the course's modules will be downloaded from Canvas and saved in the course's
        directory (located in /data/courses/). If `get_unpublished_modules` is `True`, and
        we have access to unpublished modules for the course, then we will save both published and
        unpublished modules to file. Otherwise, we will only save published modules.

        Parameters
        ----------
        course_ids_str : `Tuple[str]`
            Tuple of course ids

        get_unpublished_modules: `bool`
            True if we should attempt to store unpublished modules for the courses in `course_ids_str`;
            False otherwise
        """

        course_ids = self._ids_converter(course_ids_str)
        c_ids = {c.id for c in self.courses}

        new_courses = tuple(self.get_course(i) for i in course_ids if i not in c_ids)
        self.courses.extend(new_courses)

        for c in course_ids_str:
            if c not in self.timings:
                self.timings[c] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if c not in self.due_week:
                self.due_week[c] = []

            if c not in self.due_day:
                self.due_day[c] = []

        for c in new_courses:
            modules_file = f"{COURSES_DIRECTORY}/{c.id}/modules.txt"
            watchers_file = f"{COURSES_DIRECTORY}/{c.id}/watchers.txt"
            self.store_channels_in_file(self._live_channels, watchers_file)

            if self._live_channels:
                create_file.create_file_if_not_exists(modules_file)

                # Here, we will only download modules if modules_file is empty.
                if os.stat(modules_file).st_size == 0:
                    self.download_modules(c, get_unpublished_modules)

    @staticmethod
    def download_modules(course: Course, incl_unpublished: bool):
        """
        Download all modules for a Canvas course, storing each module's ID
        in `{COURSES_DIRECTORY}/{course.id}/modules.txt`. Includes unpublished modules if
        `incl_unpublished` is `True` and we have access to unpublished modules for the course.

        Assumption: {COURSES_DIRECTORY}/{course.id}/modules.txt exists.
        """

        modules_file = f"{COURSES_DIRECTORY}/{course.id}/modules.txt"

        with open(modules_file, "w") as m:
            for module in CanvasHandler.get_all_modules(course, incl_unpublished):
                m.write(f"{str(module.id)}\n")

    @staticmethod
    def get_all_modules(course: Course, incl_unpublished: bool) -> List[Union[Module, ModuleItem]]:
        """
        Returns a list of all modules for the given course. Includes unpublished modules if
        `incl_unpublished` is `True` and we have access to unpublished modules for the course.
        """

        all_modules = []

        for module in course.get_modules():
            # If module does not have the "published" attribute, then the host of the bot does
            # not have access to unpublished modules. Reference: https://canvas.instructure.com/doc/api/modules.html
            if incl_unpublished or not hasattr(module, "published") or module.published:
                all_modules.append(module)

                for item in module.get_module_items():
                    # See comment about the "published" attribute above.
                    if incl_unpublished or not hasattr(item, "published") or item.published:
                        all_modules.append(item)

        return all_modules

    @staticmethod
    def store_channels_in_file(text_channels: List[discord.TextChannel], file_path: str):
        """
        For each text channel provided, we add its id to the file with given path if the file does
        not already contain the id.
        """

        if text_channels:
            create_file.create_file_if_not_exists(file_path)

            with open(file_path, "r") as f:
                existing_ids = f.readlines()

            ids_to_add = set(map(lambda channel: str(channel.id) + "\n", text_channels))

            with open(file_path, "w") as f:
                for channel_id in existing_ids:
                    if channel_id in ids_to_add:
                        ids_to_add.remove(channel_id)

                    f.write(channel_id)

                for channel_id in ids_to_add:
                    f.write(channel_id)

    def untrack_course(self, course_ids_str: Tuple[str]):
        """
        Cause this CanvasHandler to stop tracking the courses with given IDs.

        Parameters
        ----------
        course_ids_str : `Tuple[str, ...]`
            Tuple of course ids
        """

        course_ids = self._ids_converter(course_ids_str)
        c_ids = {c.id: c for c in self.courses}

        ids_of_removed_courses = []

        for i in filter(c_ids.__contains__, course_ids):
            self.courses.remove(c_ids[i])
            ids_of_removed_courses.append(i)

        for c in course_ids_str:
            if c in self.timings:
                del self.timings[c]

            if c in self.due_week:
                del self.due_week[c]

            if c in self.due_day:
                del self.due_day[c]

        for i in ids_of_removed_courses:
            watchers_file = f"{COURSES_DIRECTORY}/{i}/watchers.txt"
            self.delete_channels_from_file(self.live_channels, watchers_file)

            # If there are no more channels watching the course, we should delete that course's directory.
            if os.stat(watchers_file).st_size == 0:
                shutil.rmtree(f"{COURSES_DIRECTORY}/{i}")

    @staticmethod
    def delete_channels_from_file(text_channels: List[discord.TextChannel], file_path: str):
        """
        For each text channel provided, we remove its id from the file with given path
        if the id is contained in the file.
        """

        create_file.create_file_if_not_exists(file_path)

        with open(file_path, "r") as f:
            channel_ids = f.readlines()

        ids_to_remove = set(map(lambda channel: str(channel.id) + "\n", text_channels))

        with open(file_path, "w") as f:
            for channel_id in channel_ids:
                if channel_id not in ids_to_remove:
                    f.write(channel_id)

    def get_course_stream_ch(self, since: Optional[str], course_ids_str: Tuple[str, ...], base_url: str, access_token: str) -> List[List[str]]:
        """
        Gets announcements for course(s)

        Parameters
        ----------
        since : `None or str`
            Date/Time from announcement creation to now. If None, then all announcements are returned,
            regardless of date of creation.

        course_ids_str : `Tuple[str, ...]`
            Tuple of course ids. If this parameter is an empty tuple, then this function gets announcements
            for *all* courses being tracked by this CanvasHandler.

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
        course_streams = tuple(get_course_stream(c.id, base_url, access_token) for c in self.courses if (not course_ids) or c.id in course_ids)
        data_list = []

        for stream_iter in map(iter, course_streams):
            for item in filter(lambda i: i["type"] == "Conversation" and i["participant_count"] == 2, stream_iter):
                messages = item.get("latest_messages")

                # Idea behind this hack:
                # If we assume that any message from Cinda is an announcement, then
                # we can just treat all such messages as announcements.
                # Below are the conditions necessary to consider a message as an announcement:
                # 1. The message cannot have any replies (no one replies to announcements).
                # 2. The number of participants is 2. This is checked in the filter condition above.
                # 3. Cinda is the author of the message.

                if messages and len(messages) == 1:
                    if messages[0].get("author_id") == CINDA_CANVAS_ID:
                        course = self.get_course(item["course_id"])
                        course_url = get_course_url(course.id, base_url)
                        title = "Announcement: " + item["title"]
                        short_desc = "\n".join(item["latest_messages"][0]["message"].split("\n")[:4])
                        ctime_iso = item["created_at"]

                        if ctime_iso is None:
                            ctime_text = "No info"
                        else:
                            time_shift = datetime.now() - datetime.utcnow()
                            ctime_iso_parsed = (dateutil.parser.isoparse(ctime_iso) + time_shift).replace(tzinfo=None)

                            # A timedelta representing how long ago the conversation was created.
                            ctime_timedelta = datetime.now() - ctime_iso_parsed

                            if since and ctime_timedelta >= self._make_timedelta(since):
                                break

                            ctime_text = ctime_iso_parsed.strftime("%Y-%m-%d %H:%M:%S")

                        data_list.append([course.name, course_url, title, item["html_url"], short_desc, ctime_text, course.id])

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

        course_ids = self._ids_converter(course_ids_str)
        courses_assignments = {c: c.get_assignments() for c in self.courses if not course_ids or c.id in course_ids}

        return self._get_assignment_data(due, courses_assignments, base_url)

    def _get_assignment_data(self, due: Optional[str], courses_assignments: Dict[Course, PaginatedList], base_url: str) -> List[List[str]]:
        """
        Formats all courses assignments as separate assignments

        Parameters
        ----------
        due : `None or str`
            Date/Time from due date of assignments

        courses_assignments : `Dict[Course, PaginatedList of Assignments]`
            List of courses and their assignments

        base_url : `str`
            Base URL of the Canvas instance's API

        Returns
        -------
        `List[List[str]]`
            List of assignment data to be formatted and sent as embeds
        """

        data_list = []

        for course, assignments in courses_assignments.items():
            course_name = course.name
            course_url = get_course_url(course.id, base_url)

            for assignment in filter(lambda asgn: asgn.published, assignments):
                ass_id = assignment.__getattribute__("id")
                title = "Assignment: " + assignment.__getattribute__("name")
                url = assignment.__getattribute__("html_url")
                desc_html = assignment.__getattribute__("description") or "No description"

                short_desc = "\n".join(BeautifulSoup(desc_html, "html.parser").get_text().split("\n")[:4])

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

                    if dtime_timedelta < timedelta(0) or (due and dtime_timedelta > self._make_timedelta(due)):
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
        till_str : `str`
            Date/Time from due date of assignments

        Returns
        -------
        `datetime.timedelta`
            Time delta between till and now
        """

        till = re.split(r"[-:]", till_str)

        if till[1] in ["hour", "day", "week"]:
            return abs(timedelta(**{till[1] + "s": float(till[0])}))
        elif till[1] in ["month", "year"]:
            return abs(timedelta(days=(30 if till[1] == "month" else 365) * float(till[0])))

        year, month, day = int(till[0]), int(till[1]), int(till[2])

        if len(till) == 3:
            return abs(datetime(year, month, day) - datetime.now())

        hour, minute, second = int(till[3]), int(till[4]), int(till[5])
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

        return [[c.name, get_course_url(c.id, url)] for c in self.courses]
