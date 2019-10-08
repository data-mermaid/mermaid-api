## NOTES:

### Serialiazer Arguments

- `many`: is always True and if a dictionary is passed to `data`, it will be wrapped in a list.
- `instance`: is not implemented.
- `project_choices`: pre-fetched choices that require a project id, example: ProjectProfile choices.


### Other

- Records created by serializer are batched, NO signals will be triggered.


## Example Using Ingest Serializer

```python
import csv
import json

from api import mocks
from api.ingest.serializers import BenthicPITCSVSerializer
from api.models import ProjectProfile, Management, Site
from api.resources.project_profile import ProjectProfileSerializer
from api.utils import tokenutils


def run():
    with open("./api/ingest/test_pit.csv", "r") as f:
        reader = csv.DictReader(f)
        _rows = []
        project_id = "4080679f-1145-4d13-8afb-c2f694004f97"
        for row in reader:
            row["project"] = project_id
            row["profile"] = "0e6dc8a8-ae45-4c19-813c-6d688ed6a7c3"
            _rows.append(row)

        token = tokenutils.create_token("google-oauth2|109519544860798433542")
        mock_request = mocks.MockRequest(token=token)

        project_choices = dict()
        project_choices["data__sample_event__site"] = {
            s.name.lower().replace("\t", " "): str(s.id)
            for s in Site.objects.filter(project_id=project_id)
        }

        project_choices["data__sample_event__management"] = {
            m.name.lower().replace("\t", " "): str(m.id)
            for m in Management.objects.filter(project_id=project_id)
        }

        project_choices["project_profiles"] = {
            pp.profile.email.lower(): ProjectProfileSerializer(instance=pp).data
            for pp in ProjectProfile.objects.select_related("profile").filter(
                project_id=project_id
            )
        }

        s = BenthicPITCSVSerializer(
            data=_rows[0],
            many=True,
            project_choices=project_choices,
            context={"request": mock_request},
        )

        is_valid = s.is_valid()
        if is_valid is False:
            errors = s.formatted_errors
            print("{} ERRORS!!! :(".format(num_errors))
        else:
            recs = s.save()
            print("{} SUCCESS!!! _\|/_".format(len(recs)))

```