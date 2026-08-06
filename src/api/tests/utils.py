import csv
from io import StringIO


def get_csv_rows(client, token, url):
    response = client.get(url, HTTP_AUTHORIZATION=f"Bearer {token}")
    f = StringIO(b"".join(response.streaming_content).decode("utf-8"))
    reader = csv.DictReader(f, delimiter=",")
    fieldnames = reader.fieldnames
    return fieldnames, list(reader), response
