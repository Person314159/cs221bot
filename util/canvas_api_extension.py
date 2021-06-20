from canvasapi.course import Course
from canvasapi.requester import Requester
from canvasapi.util import combine_kwargs, get_institution_url


def get_course_stream(course_id: int, base_url: str, access_token: str, **kwargs: dict) -> dict:
    """
    Parameters
    ----------
    course_id : `int`
        Course id

    base_url : `str`
        Base URL of the Canvas instance's API

    access_token : `str`
        API key to authenticate requests with

    Returns
    -------
    `dict`
        JSON response for course activity stream
    """

    access_token = access_token.strip()
    base_url = get_institution_url(base_url)
    requester = Requester(base_url, access_token)
    response = requester.request(
        "GET",
        f"courses/{course_id}/activity_stream",
        _kwargs=combine_kwargs(**kwargs)
    )
    return response.json()


def get_course_url(course_id: str, base_url) -> str:
    """
    Parameters
    ----------
    course_id : `str`
        Course id

    base_url : `str`
        Base URL of the Canvas instance's API

    Returns
    -------
    `str`
        URL of course page
    """

    base_url = get_institution_url(base_url)
    return f"{base_url}/courses/{course_id}"


def get_staff_ids(course: Course) -> list[int]:
    """
    Parameters
    ----------
    course : `Course`
        The course to get staff IDs for

    Returns
    -------
    `List[int]`
        A list of the IDs of all professors and TAs in the given course.
    """

    staff = course.get_users(enrollment_type=["teacher", "ta"])
    staff_ids = list(map(lambda user: user.id, staff))

    return staff_ids
