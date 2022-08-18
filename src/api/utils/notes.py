import re


SEP = "\n\n"
susets = (
    "benthictransect_set",
    "fishbelttransect_set",
    "quadratcollection_set",
    "quadrattransect_set",
)


def senotes2suset(sample_event, suset_prop, dryrun=False):
    senotes = sample_event.notes.strip()
    if senotes:
        pattern = r"((?:^.*\n)+)(?=\1)"
        while re.search(pattern, senotes, flags=re.MULTILINE):
            senotes = re.sub(pattern, "", f"{senotes}{SEP}", flags=re.MULTILINE)
        senotes = senotes.strip()

        suset = getattr(sample_event, suset_prop)
        if suset:
            for su in suset.all():
                sunotes = su.notes.strip()
                if sunotes:
                    sunotes = f"{sunotes}{SEP}"
                su.notes = f"{sunotes}{senotes}"
                sample_event.notes = ""

                if dryrun:
                    print(
                        f"se id {sample_event.id} su id {su.id} ({suset_prop[:-4]}) su notes:\n{su.notes}"
                    )
                else:
                    su.save()
                    sample_event.save()


def senotes2sunotes(sample_event, dryrun=False):
    for suset in susets:
        senotes2suset(sample_event, suset, dryrun)
