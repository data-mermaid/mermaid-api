Collect Records
===============


Data collected during one of the sample unit method surveys (i.e. Fish Belt, Benthic PIT, etc) is stored in a Collect Record.  Collect records are different then other types of records in MERMAID and go through a stepped staged process to help ensure the finalized record is valid, clean data. This staged process is Save, Validate, and Submit.


Save
----

A collect record can be saved at any point even if it is partially populated or in an invalid state.  The record can be thought of as being in a "draft" state.


Validate
--------

Saved records can be validated by calling the `collect record's validation endpoint`_, which responds with the overall validation status (`ok`, `warning` or `error`) and an updated copy of the collect record that was validated but now includes the detailed results individual details.  

Example validate response
::

    {
        "f5c8f06a-8ba0-4385-8e9e-ad154c059d94": {
            "status": "error",
            "record": {
                "id": "ffffffff-8ba0-4385-8e9e-ad154c059d94",
                ... trimmed ...
                "validations": {
                    "status": "error",
                    "results": {
                        "site": {
                            "wrapped": {
                                "status": "error",
                                "message": "Site record not available for similarity validation"
                            },
                            "validate_exists": {
                                "status": "error",
                                "message": "Site: Record doesn't exist"
                            }
                        },
                        "depth": {
                            "validate_range": {
                                "status": "warning",
                                "message": "Depth value outside range of 1 and 30"
                            }
                        },
                        "observers": {
        ... trimmed ...
    }    

In the record's detailed validations section, validations that have a status of `warning` can be be suppressed by changing the validation's status to `ignore` and re-saving the record.  Based on example above, the depth warning can be suppressed as follows:

::

    ... trimmed ...
    "depth": {
        "validate_range": {
            "status": "ignore",
            "message": "Depth value outside range of 1 and 30"
        }
    },
    ... trimmed ...


The save/validate process continues until the overall record validation status is `ok`.  The validated record is now ready to submit.


Submit
------

Submitting a collect record moves the complete and valid record from its "editing" stage to a more finalized stage. The record can be submitted by calling the `collect record's submit endpoint`_.  The moved record is:

1. now is included in MERMAID reporting.
2. and is only available for edits by `Admin` project users.


For details on how to call Save, Validate, and Submit please refer to the `Collect Record Endpoints`_.

.. _`Collect Record Endpoints`: ./projects.html#projects-project-id-collectrecords
.. _`collect record's validation endpoint`: ./projects.html#projects-project-id-collectrecords
.. _`collect record's submit endpoint`: ./projects.html#projects-project-id-collectrecords