import json


def readJSON(jsonfile):
    with open(jsonfile, "r") as f:
        return json.load(f)


def writeJSON(data, jsonfile):
    with open(jsonfile, "w") as f:
        json.dump(data, f, indent=4)
