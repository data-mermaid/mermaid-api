from api.ingest.serializers import BenthicPITCSVSerializer
import csv
import json
from pprint import pprint

# from api.resources.choices import ChoiceViewSet
# import itertools


def run():
    with open("./api/ingest/test_pit.csv", "r") as f:
        reader = csv.DictReader(f)
        _rows = []
        for row in reader:
            row["project"] = "4080679f-1145-4d13-8afb-c2f694004f97"
            row["profile"] = "0e6dc8a8-ae45-4c19-813c-6d688ed6a7c3"
            _rows.append(row)
        
        # print(json.dumps(_rows[0], indent=4))
        # print("\n\n")

        # s = BenthicPITCSVSerializer(
        #     data=_rows[0],
        #     many=False
        # )
        s = BenthicPITCSVSerializer(
            data=_rows[0:2],
            many=True
        )
        is_valid = s.is_valid()
        if is_valid is False:
            print(json.dumps(s.errors, indent=4))
            # for err in s.errors:
            #     print(json.dumps(err, indent=4))
            #     break
        else:
            print('s.cleaned_data: {}'.format(s.validated_data))
            print("Success!!! _\|/_")


# def build_choices(key, choices):
#     return [(c["name"], str(c["id"])) for c in choices[key]["data"]]


# def create_choices_sheet():

#     _choices = ChoiceViewSet().get_choices()
#     visibility_choices = build_choices("visibilities", _choices)
#     current_choices = build_choices("currents", _choices)
#     relative_depth_choices = build_choices("relativedepths", _choices)
#     tide_choices = build_choices("tides", _choices)
#     reef_slopes_choices = build_choices("reefslopes", _choices)
#     # benthic_attributes_choices = [
#     #     (ba.name.lower(), str(ba.id)) for ba in BenthicAttribute.objects.all()
#     # ]
#     growth_form_choices = build_choices("growthforms", _choices)

#     choices = list(
#         itertools.zip_longest(
#             visibility_choices,
#             current_choices,
#             relative_depth_choices,
#             tide_choices,
#             reef_slopes_choices,
#             growth_form_choices,
#         )
#     )
#     header = [
#         "Visibility ID",
#         "Visibility Name",
#         "Current ID",
#         "Current Name",
#         "Relative Depth ID",
#         "Relative Depth Name",
#         "Depth ID",
#         "Depth Name",
#         "Reef Slope ID",
#         "Reef Slope Name",
#         "Growth Form ID",
#         "Growth Form Name",
#     ]
#     with open("choices.csv", "w") as w:
#         w.write(",".join(header))
#         w.write("\n")
#         for v, c, rd, d, rs, gf in choices:
#             row = [
#                 v[1] if v is not None else '',
#                 v[0] if v is not None else '',
#                 c[1] if c is not None else '',
#                 c[0] if c is not None else '',
#                 rd[1] if rd is not None else '',
#                 rd[0] if rd is not None else '',
#                 d[1] if d is not None else '',
#                 d[0] if d is not None else '',
#                 rs[1] if rs is not None else '',
#                 rs[0] if rs is not None else '',
#                 gf[1] if gf is not None else '',
#                 gf[0] if gf is not None else '',
#             ]
#             w.write(",".join(row))
#             w.write("\n")
