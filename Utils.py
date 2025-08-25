import math
import json


def erfinv(x):
    if x <= -1 or x >= 1:
        raise Exception
    if x == 0:
        return 0
    a = 0
    b = 4 * x
    if x < 0:
        a, b = b, a
    for _ in range(100):
        c = (a + b) / 2
        if math.erf(c) > x:
            b = c
        else:
            a = c
    return c


def load_json_data(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def write_json_data(obj, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        data = json.dump(obj, f, sort_keys=True, indent=4)
