# MERMAID Revisions



### Source Types

Identifiers to relate to the different models that are supported by MERMAID revisions.

* collect_records
* project_sites
* project_managements
* project_profiles
* projects
* benthic_attributes
* fish_families
* fish_genera
* fish_species
* choices

## Pull

Fetch the latest updates and deletes for a given source type(s).  Source types have different
required payload properties:

`project` and `profile`

* collect_records

`project`

* project_sites
* project_managements
* project_profiles
* projects

No required properties

* benthic_attributes
* fish_families
* fish_genera
* fish_species
* choices

**METHOD:** `POST`

### Payload

#### Schema

```
    {
        "<SOURCE TYPE>": {
            "last_revision": [int, null],
            "project": [str, null],
            "profile": [str, null], 
        },
        ...
    }

```

#### Example

```
    {
        "collect_records": {
            "last_revision": 1932,
            "project": "a2dd5697-6ceb-41d4-9a03-6a837bc97997",
            "profile": "832082a0-2c79-4e41-97c2-bd33a652064b",
        },
        "fish_families": {
            "last_revision": null
        }
    }
```

### Response


#### Schema

```
    {
        "<SOURCE TYPE>": {
            "updates": Array,
            "deletes": Array,
            "removes": Array,
            "last_revision_num": int, 
        },
        ...
    }
```

`updates`: Each includes 3 system properties along with the record's properties:

    * `_last_revision_num`: Latest revision number for this record
    * `_modified`: Property available for client applications for tracking record edits, set to `false`
    * `_deleted`: Property available for client applications for tracking deleted records, set to `false`

`deletes`: Only includes the record `id` and the system property `_last_revision_num`.
`removes`: Only includes the record `id` and the system property `_last_revision_num`.


#### Example

```
    {
        "collect_records: {
            "updates": [
                "_last_revision_num": 857,
                "_modified": false
                "_deleted": false
                "id": "f5c8f06a-8ba0-4385-8e9e-ad154c059d94",
                ... other collect record properties ...
            ],
            "deletes": [{
                "id": "f504559a-dc31-4c64-b590-0ca10d02a64e",
                "_last_revision_num": 434
            }],
            "removes": [{
                "id": "fe04559a-dc31-4c64-b590-0ca10d22264e",
                "_last_revision_num": 435
            }]
        },
        "fish_families": {...}
    }
```


## Push

Push new, edited and deleted records.

**METHOD:** `POST`

### Payload

#### Schema

```
    {
        "<SOURCE TYPE>": [
            {
                "_modified": bool,
                "_last_revision_num": [int, null],
                "_deleted": bool,
                ... other record properties ...
            },
            ..
        ]
    }
```

#### Example

```
    {
        "collect_records": [
            {
                "_modified": true,
                "_last_revision_num": null,
                "_deleted": false,
                "id": "eb076980-2716-4dfb-bfbb-d772fb0845ec",
                ...
            },
            {
                "_modified": true,
                "_last_revision_num": 343,
                "_deleted": true,
                "id": "ff076980-2716-4dfb-bfbb-d772fb084533"
            }
        ],
        "project_sites": [
            {
                "id": "c5b69197-0024-4024-9703-840d96413cb2",
                ...
            }
        ],
        ...
    }
```

### Response

In the push response, for each source type, the array of objects returned follows the same order as in the payload.


#### Schema

```
    {
        "collect_records": [
            {
                "status_code": int,    
                "message": str,    
                "data": [object or null]
            },
            ...
        ],
        ...
    }
```

`status_code`: Uses http status codes. (example: 200, 201, 400, etc)
`message`: A message is included if there was an error with the record (status_code >= 400)
`data`: Depending on the status_code:
    
    * 200/201: Returns the update record
    * 400: Returns an object of validation errors

#### Example

```
    {
        "collect_records": [
            {
                "status_code": 200,
                "message": ",
                "data": {
                    "id": "eb076980-2716-4dfb-bfbb-d772fb0845ec",
                    "_last_revision_num": 8,
                    "_modified": false,
                    "_deleted": false
                }
            },
            {
                "status_code": 204,
                "id": "ff076980-2716-4dfb-bfbb-d772fb084533"
            }
            ...    
        ],
        "project_sites": [
            {
                "status_code": 400,
                "message": "Validation Error",
                "data": {
                    "location": "This field is required.",
                    "country": "This field is required.",
                    "reef_type": "This field is required.",
                    "reef_zone": "This field is required.",
                    "exposure": "This field is required."
                }
            }
        ]
    }

```