
* Values are required for column names that end with a `*`.
* Observers columns repeat for each observer in an observation record.
* Observation interval value, are required but should they be automatically created based on order of records in file???

### Suppressing Validation Warnings and Errors

Validation warnings and errors can be ignored during the ingest process.  To do this, include the query parameter key `validate_config` in the ingest payload.  The value of `valid_config` defines validations that will be ignored, see example below


```
{
    "obs_benthic_pits": ["validate_observation_count", "validate_hard_coral"],
    "len_surveyed": ["validate_range"],
    ...
}

where:
    obs_benthic_pits and len_surveyed: are the validation identifiers.
    ["validate_observation_count", "validate_hard_coral"] |
    ["validate_range"]                                    | : validation tests.
```

**NOTE: Some errors can not be ignored because they are enforced by the database**