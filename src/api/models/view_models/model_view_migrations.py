from .fish_attributes import FishAttributeView

def forward_sql():
    sql = [
        FishAttributeView.sql,
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
    ]

    output = []
    for s in sql:
        s = s.strip()
        if s[-1] != ";":
            s += ";"

        output.append(s)

    return "\n".join(output)
