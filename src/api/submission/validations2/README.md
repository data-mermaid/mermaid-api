Collect Record Validations v2
-----------------------------

Url: `/v1/projects/<project>/collectrecords/validate/`
Method: `POST`

### Payload

```
{
	"ids": ["ce87508d-1533-4d36-b836-634ab911954f"], <-- Collect Record ids
	"version": "2"                                   <-- Validation version (default: "1")
}
```

### Response

```
{
  "<collect record id>: {
    "status": ["ok", "warning", "error"],
    "record": {
      ... collect record attributes ...
    }
  }
}

```

## Collect Record Validation

```
{
  ... other collect record attributes ...
  "validations": {
      "status": [str] Overall validator output status, options include ["ok", "warning", "error"],
      "version": [str] Validation version "2",
      "last_validated": [str] Last time validation has been run. Format: iso8601
      "results": {
        ... validation results - see details below ...
      }
    }
  
}

```

#### Validation Results


```
{
  "results":{
    "$record": [list] Record level validator results,
    "<attribute>": [Dict[str, list]] Attribute level validator results.  Tree structure of dict matches that of the collect record.

        Example:
        {
          "id": "3fe649d8-2c9a-4b0b-811f-abcdef123456",
          "updated_by": "0e6dc8a8-ae45-4c19-813c-6d688ed6a7c3",
          "created_on": "2021-10-26T11:51:20.611977Z",
          "updated_on": "2021-10-26T12:10:03.488247Z",
          "stage": 5,
          "created_by": "0e6dc8a8-ae45-4c19-813c-abcdef123456",
          "project": "8c213ce8-7973-47a5-9359-abcdef123456",
          "profile": "0e6dc8a8-ae45-4c19-813c-abcdef123456"
          "data": {
            "fishbelt_transect": {
              "depth": 13.0
            }
          }
          ...
          "validations": {
            "results": {
              "data": {
                "fishbelt_transect": {
                  "depth": [
                    ... validator results ...
                  ]
                }
              }
            }
          }
        }

    ...
  }
}
```

**Valdator Result:**

```
{
  "code": [str] Validation Code,
  "name": [str] Validator name,
  "fields": [list] List of attributes used by validator,
  "status": [str] Validator output status, options include ["ok", "warning", "error", "ignore"],
  "context": [dict] Any additional information that adds more context to the validation that was run,
  "validation_id": [str] Required system generated value
}
```
