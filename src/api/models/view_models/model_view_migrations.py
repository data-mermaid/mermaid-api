from .fish_attributes import FishAttributeView
from .invert_attributes import InvertAttributeView


def forward_sql():
    sql = [
        FishAttributeView.sql,
        InvertAttributeView.sql,
    ]
    output = []
    for s in sql:
        s = s.strip()
        if s[-1] != ";":
            s += ";"

        output.append(s)

    return reverse_sql() + "\n".join(output)


def reverse_sql():
    sql = [
        FishAttributeView.reverse_sql,
        InvertAttributeView.reverse_sql,
    ]

    output = []
    for s in sql:
        s = s.strip()
        if s[-1] != ";":
            s += ";"

        output.append(s)

    return "\n".join(output)
