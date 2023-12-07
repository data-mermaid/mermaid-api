import re


def camel_case(string: str) -> str:
    s = re.sub(r"(_|-)+", " ", string).title().replace(" ", "")
    return "".join([s[0].lower(), s[1:]])
