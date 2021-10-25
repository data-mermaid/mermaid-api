Collect Record Validations v2
-----------------------------

Url: `/v1/projects/<project>/collectrecords/validate/`
Method: `POST`

### Payload

```
{
	"ids": ["ce87508d-1533-4d36-b836-634ab911954f"], <-- Collect Record ids
	"version": "2"                                   <-- Validation version
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
      "last_validated": [str] Last time validation had been run, format: iso8601
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
  "fields": [list] List of attributes used in by validator,
  "status": [str] Validator output status, options include ["ok", "warning", "error", "ignore"],
  "context": [dict] Any additional information that adds more context to the validation that was run,
  "validation_id": [str] Required system generated value
}
```
