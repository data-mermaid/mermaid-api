from .fish_attributes import FishAttributeView
from .summary_site import SummarySiteViewModel


def forward_sql():
    sql = [
        FishAttributeView.sql,
        SummarySiteViewModel.sql,
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
        SummarySiteViewModel.reverse_sql,
        FishAttributeView.reverse_sql,
    ]

    output = []
    for s in sql:
        s = s.strip()
        if s[-1] != ";":
            s += ";"

        output.append(s)

    return "\n".join(output)
