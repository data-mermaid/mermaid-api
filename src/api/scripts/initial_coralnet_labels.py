import csv
from pathlib import Path

from django.conf import settings

from api.models import BenthicAttribute, Classifier, GrowthForm, Label, LabelMapping


def _get_id(val):
    id = str(val)
    if id == "" or id == "NA":
        return None
    return id


def run():
    labels_csv = Path(settings.BASE_DIR, "data", "initial_label_pop.csv")
    initial_classifier = Classifier.objects.get(name="initial pyspacer classifier")
    classifier_labels = set()

    with open(labels_csv) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            ba_id = _get_id(row["MermaidBaID"])
            gf_id = _get_id(row["MermaidGfID"])
            cn_id = _get_id(row["CoralNetID"])
            cn_label = row["CoralNetName"]
            classifier_label = (
                row["CoralFocus3Label"] if row["CoralFocus3Label"].lower() != "remove" else None
            )
            if classifier_label:
                cl_ba, cl_gf = (classifier_label.split(" - ") + [None])[:2]
                classifier_labels.add((cl_ba, cl_gf))

            label, created = Label.objects.get_or_create(
                benthic_attribute_id=ba_id, growth_form_id=gf_id
            )

            label_mapping, created = LabelMapping.objects.get_or_create(
                label=label,
                provider="CoralNet",
                provider_id=cn_id,
                provider_label=cn_label,
            )

    for cl_ba, cl_gf in classifier_labels:
        ba = BenthicAttribute.objects.get(name=cl_ba)
        gf = GrowthForm.objects.get_or_none(name=cl_gf)
        cl, created = Label.objects.get_or_create(benthic_attribute=ba, growth_form=gf)
        initial_classifier.labels.add(cl)

    print(f"classifier labels created ({initial_classifier.labels.count()})")
    for label in initial_classifier.labels.order_by("benthic_attribute__name", "growth_form__name"):
        print(label.pk, label.name)
