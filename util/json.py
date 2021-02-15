import json


def read_json(jsonfile: str) -> dict:
    with open(jsonfile, "r") as f:
        return json.load(f)


def write_json(data: dict, jsonfile: str) -> None:
    with open(jsonfile, "w") as f:
        json.dump(data, f, indent=4)
