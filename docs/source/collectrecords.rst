Collect Records
===============

Data collected during one of the sample unit method surveys (i.e. Fish Belt, Benthic PIT, etc) is stored in a Collect Record. Collect records are different then other types of records in MERMAID and go through a staged process to help ensure the finalized record is valid, clean data. The stages in this process are ``Save``, ``Validate``, and ``Submit``.

Save
----

A collect record can be saved at any point even if it is partially populated or in an invalid state. The record can be thought of as being in a "draft" state. Saving a record marks its validation results as ``stale``: they are kept, but the record has to be validated again before it can be submitted.

Validate
--------

Saved records can be validated by calling the `collect record's validation endpoint`_ with a list of record ids. It responds, for each record, with the overall validation status (``ok``, ``warning`` or ``error``) and an updated copy of the record that includes the detailed validation results in its ``validations`` property.

Example validate response:
::

    {
        "f5c8f06a-8ba0-4385-8e9e-ad154c059d94": {
            "status": "warning",
            "record": {
                "id": "f5c8f06a-8ba0-4385-8e9e-ad154c059d94",
                ... trimmed ...
                "validations": {
                    "version": "2",
                    "status": "warning",
                    "last_validated": "2026-11-24 17:48:45.076205+00:00",
                    "results": {
                        "$record": [
                            {
                                "name": "observation_count_validator",
                                "code": "too_few_observations",
                                "status": "warning",
                                "fields": ["data.obs_belt_fishes"],
                                "context": {"observation_count_range": [5, 200]},
                                "validation_id": "63043489232e671a4f9231fdf6d2665f"
                            },
                            ... trimmed ...
                        ],
                        "data": {
                            "fishbelt_transect": {
                                "sample_time": [
                                    {
                                        "name": "sample_time_validator",
                                        "code": null,
                                        "status": "ok",
                                        "fields": ["data.fishbelt_transect.sample_time"],
                                        "context": null,
                                        "validation_id": "54a37d1511e3e31b3abe1b3ea3f93357"
                                    }
                                ],
                                ... trimmed ...
                            },
                            "obs_belt_fishes": [
                                [ ... results for the first observation ... ],
                                [ ... results for the second observation ... ],
                                [
                                    {
                                        "name": "fish_size_validator",
                                        "code": "max_fish_size",
                                        "status": "warning",
                                        "fields": ["data.obs_belt_fishes"],
                                        "context": {
                                            "max_length": 30.0,
                                            "observation_id": "d6d1a667-2605-449f-8974-4182f01a353e"
                                        },
                                        "validation_id": "2b289dc99c02e9ae1c764e8a71cca3cc"
                                    },
                                    ... trimmed ...
                                ]
                            }
                        }
                    }
                }
            }
        }
    }

The ``results`` tree follows the shape of the record's ``data``:

- Results about a single field are a list under that field's path, e.g. ``results.data.fishbelt_transect.sample_time``.
- Results about the record as a whole are a list under ``results["$record"]``.
- Results about observations are a list per observation, in the same order as the observations, e.g. ``results.data.obs_belt_fishes[2]`` for the third observation. Each result's ``context.observation_id`` names its observation.

Each individual result has a ``status`` (``ok``, ``warning``, ``error`` or ``ignore``), a ``code`` identifying the specific problem (``null`` when the status is ``ok``), and a ``validation_id`` identifying the check that produced it. Use ``code`` to tell warnings apart, e.g. ``too_few_observations``, ``low_density``, ``max_fish_size`` or ``similar_date_sample_unit``.

Ignoring a warning
~~~~~~~~~~~~~~~~~~

A result with a status of ``warning`` can be ignored by changing its ``status`` to ``ignore``, saving the record, and validating it again. Leave the result's ``validation_id`` and ``code`` unchanged: they are how MERMAID recognizes the warning on the next validation. For example, to ignore the ``too_few_observations`` warning above:

::

    ... trimmed ...
    "$record": [
        {
            "name": "observation_count_validator",
            "code": "too_few_observations",
            "status": "ignore",
            ... unchanged ...
        },
    ... trimmed ...

The record can be saved with a ``PUT`` of the whole record, or with a ``PATCH`` that sends just the record's ``project`` and ``validations``::

    PATCH /v1/projects/<project_id>/collectrecords/<record_id>/
    {"project": "<project_id>", "validations": { ... the record's validations, with ignores set ... }}

An ignore is kept each time the record is validated again, including after the record is edited, as long as the same check still produces the same warning (the same ``validation_id`` and ``code``). If the check now passes, produces a different warning, or produces an error, the ignore no longer applies. Errors cannot be ignored. Ignores on observations follow the observation, so deleting or reordering observations does not move them.

The save/validate process continues until the overall record validation status is ``ok``. Every warning on a record has to be ignored or fixed before the record can be submitted. The validated record is now ready to submit.


Submit
------

Submitting a collect record moves the complete and valid record from its "editing" stage to a finalized stage. The record can be submitted by calling the `collect record's submit endpoint`_. Submitting validates the record again first, and only submits it if the result is ``ok``. Otherwise the response includes the record with its new validation results. The moved record is now:

1. included in MERMAID reporting
2. only available for edits by `admin` project users

For details on how to call Save, Validate, and Submit please refer to the `Collect Record Endpoints`_.

Ignoring warnings programmatically
----------------------------------

MERMAID supports ignoring specific warnings through the API, as described above, so they can be ignored by a script. MERMAID does not offer bulk ignoring in Collect or in mermaidr.

An ignore means that a person reviewed that warning on that record and accepted it. Ignoring warnings in bulk with a script is the user's choice, made at the expense of data quality, and data submitted this way is not marked differently from data that was reviewed record by record. Only ignore warnings you have decided are expected for your data.

A script that ignores chosen warnings:

1. Lists your collect records in a project: ``GET /v1/projects/<project_id>/collectrecords/``. Only the records you own are returned, so the script must run as the person who owns them (for imported data, the person who imported it).
2. Validates any records that have not been validated since they were last saved (``validations.status`` missing or ``stale``).
3. For each record whose ``validations.status`` is ``warning``, walks ``validations.results`` and sets ``status`` to ``ignore`` on each result whose ``status`` is ``warning`` and whose ``code`` is one of the chosen codes. All three kinds of results (field, ``$record`` and observation) have to be covered.
4. Saves those records with ``PATCH`` and validates them again.
5. Submits the records that are now ``ok``.
6. Repeats steps 1–5 until a pass changes nothing. Submitting a sample unit can create new warnings on other records: for example, ``similar_date_sample_unit`` warns about other *submitted* sample units at the same site and management regime within 30 days, so it can appear on a record only after a neighbouring record is submitted.

Records with errors, or with warnings that were not chosen, stay in Collecting for review in Collect.

An example R script that does this, using mermaidr to sign in: :download:`ignore_warnings.R <_static/examples/ignore_warnings.R>`.

.. _`Collect Record Endpoints`: ./projects.html#projects-project-id-collectrecords
.. _`collect record's validation endpoint`: ./projects.html#projects-project-id-collectrecords
.. _`collect record's submit endpoint`: ./projects.html#projects-project-id-collectrecords
