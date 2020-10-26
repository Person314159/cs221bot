import os
import re
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

import dateutil.parser.isoparser
import discord
from bs4 import BeautifulSoup
from canvasapi.canvas import Canvas
from canvasapi.course import Course

from util import create_file
from util.canvas_api_extension import get_course_stream, get_course_url

# Stores course modules and channels that are live tracking courses
# Do *not* put a slash at the end of this path
COURSES_DIRECTORY = "./data/courses"


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
    def _ids_converter(ids: Tuple[str, ...]) -> Set[int]:
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

        return set(int(i) for i in ids)

    def track_course(self, course_ids_str: Tuple[str, ...]):
        """
        Adds course(s) to track

        Parameters
        ----------
        course_ids_str : `Tuple[str, ...]`
            Tuple of course ids
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
            modules_file = f'{COURSES_DIRECTORY}/{c.id}/modules.txt'
            watchers_file = f'{COURSES_DIRECTORY}/{c.id}/watchers.txt'
            self.store_channels_in_file(tuple(self._live_channels), watchers_file)

            if self._live_channels:
                create_file.create_file_if_not_exists(modules_file)

                # Here, we will only download modules if modules_file is empty.
                if os.stat(modules_file).st_size == 0:
                    self.download_modules(c)

    @staticmethod
    def download_modules(course: Course):
        """
        Download all modules for a Canvas course, storing each module's URL (or name/title
        if the url does not exist) in {COURSES_DIRECTORY}/{course.id}/modules.txt.

        Assumption: {COURSES_DIRECTORY}/{course.id}/modules.txt exists.
        """

        modules_file = f'{COURSES_DIRECTORY}/{course.id}/modules.txt'

        with open(modules_file, 'w') as f:
            for module in course.get_modules():
                if hasattr(module, 'name'):
                    f.write(module.name + '\n')

                for item in module.get_module_items():
                    if hasattr(item, 'title'):
                        if hasattr(item, 'html_url'):
                            f.write(item.html_url + '\n')
                        else:
                            f.write(item.title + '\n')

    @staticmethod
    def store_channels_in_file(text_channels: Tuple[discord.TextChannel], file_path: str):
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

    def untrack_course(self, course_ids_str: Tuple[str, ...]):
        """
        Untracks course(s)

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
            watchers_file = f'{COURSES_DIRECTORY}/{i}/watchers.txt'
            self.delete_channels_from_file(self.live_channels, watchers_file)

            # If there are no more channels watching the course, we should delete that course's directory.
            if os.stat(watchers_file).st_size == 0:
                shutil.rmtree(f'{COURSES_DIRECTORY}/{i}')

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
        course_stream_list = tuple(get_course_stream(c.id, base_url, access_token) for c in self.courses if (not course_ids) or c.id in course_ids)
        data_list = []

        url = "https://canvas.ubc.ca/conversations?#filter=type=inbox&course=course_53540"

        for item in (i for c_s in course_stream_list for i in c_s if i['type'] == "Conversation"):
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
                ctime_timedelta = ctime_iso_parsed - datetime.now()
                if since and ctime_timedelta < -self._make_timedelta(since):
                    break

                ctime_text = ctime_iso_parsed.strftime("%Y-%m-%d %H:%M:%S")

            data_list.append([course.name, course_url, title, url, short_desc, ctime_text, course.id])

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
        courses_assignments = [[c, c.get_assignments()] for c in self.courses if not course_ids or c.id in course_ids]

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
            course_url = get_course_url(course.id, base_url)

            for assignment in course_assignments[1]:
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
            return abs(timedelta(days=(30 if till[1] == "month" else 365) * float(till[1])))

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
