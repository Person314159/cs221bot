import os
import pathlib


def create_file_if_not_exists(file_path: str) -> None:
    """
    Creates file with given path (as str) if the file does not already exist.
    All required directories are created, too.
    """

    pathlib.Path(os.path.dirname(file_path)).mkdir(parents=True, exist_ok=True)

    with open(file_path, "a"):
        pass
