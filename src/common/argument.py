from functools import reduce

# verify if any is provided
def verify_any(kwargs: dict, kany: list[str]) -> bool:
    return reduce(lambda x, y: (x and not y) or (not x and y), [key in kwargs for key in kany]) if kany is not None and len(kany) > 0 else True

# verify if all are provided
def verify_all(kwargs: dict, kall: list[str]) -> bool:
    return reduce(lambda x, y: x and y, [key in kwargs for key in kall], True)
