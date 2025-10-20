# MERMAID Validation System - Core Concepts

## Overview

The MERMAID validation system checks coral reef survey data (collect records) for correctness, completeness, and consistency before allowing submission. Validations can produce three outcomes:
- **OK**: Data passes validation
- **Warning**: Data is valid but may need review (e.g., unusually high fish counts)
- **Error**: Data has problems that must be fixed before submission

## When Validations Run

Validations run at two key points in the data lifecycle:

### 1. Explicit Validation
Users can request validation by POSTing to `/v1/projects/<project>/collectrecords/validate/` with a list of collect record IDs. This runs all validations and stores the results in the collect record's `validations` field, but does not submit the data.

### 2. During Submission
When users submit data via `/v1/projects/<project>/collectrecords/submit/`, the system:
1. First runs all validations
2. Only proceeds to write the data if validation status is **OK**
3. If validation produces warnings or errors, submission is blocked

## Validation Levels

Validations are organized into three levels based on what scope of data they examine:

### FIELD_LEVEL
Validates individual field values in isolation. These checks focus on a single piece of data without considering relationships to other data.

**What it checks:**
- A field has a value (required field validation)
- A field contains a valid data type (e.g., positive integers)
- A field value falls within acceptable ranges (e.g., depth between 0-50m)
- A field references a valid related record (e.g., site exists in the project)

**Examples:**
- `data.sample_event.site` must have a value
- `data.fishbelt_transect.depth` must be between 0 and 50
- `data.sample_event.sample_date` must not be in the future

**Where results appear:**
Results are stored at the specific field path in the validation results. For example, validation results for `data.sample_event.site` appear at that exact location in the results structure.

### ROW_LEVEL
Validates individual rows within observation lists. Each row (observation) is checked independently, producing one validation result per row.

**What it checks:**
- Required fields within each observation
- Valid data values for each observation
- Species/attribute is appropriate for the survey location
- Size measurements are within valid ranges for the species

**Examples:**
- Each fish observation must have a species, size, and count
- Fish size must be within valid range for that species (e.g., 5-200cm)
- Benthic attribute must be valid for the geographic region

**Where results appear:**
Results are stored as an array at the observation list path. For example, validation results for observations in `data.obs_belt_fishes` appear as an array at that location, with one result per observation.

### RECORD_LEVEL
Validates the entire collect record as a whole, examining relationships and aggregations across all data in the record.

**What it checks:**
- Overall data quality and consistency
- Aggregate values (e.g., total biomass calculations)
- Cross-field consistency (e.g., transect data matches observations)
- Relationships between different sections of the record
- Whether the record can be successfully saved to the database

**Examples:**
- Total fish count is within expected range (warning if too few or too many)
- All observations have identical transect data (warning if submitting duplicates)
- Transect combination (site, date, number, depth, width) is unique in the project
- Biomass calculations are within realistic bounds

**Where results appear:**
Results are stored under the special key `$record` in the validation results, since they don't belong to any specific field.

## Validation Types

Each validation is also classified by how it returns results:

### VALUE_VALIDATION_TYPE
Returns a single validation result, regardless of whether it checks one field or the entire record.

**Used for:**
- Field-level checks (single value)
- Record-level checks (whole record produces one result)
- Any validation that produces a single pass/fail/warning outcome

**Example:**
A validation checking if depth is within range produces one result: OK, or ERROR with code "depth_out_of_range".

### LIST_VALIDATION_TYPE
Returns multiple validation results—one for each item in a list (usually observations).

**Used for:**
- Row-level checks where each observation is validated separately
- Produces an array of results matching the array of observations

**Example:**
A validation checking fish sizes produces one result per fish observation, so if there are 25 fish observations, it produces 25 results (which may individually be OK, WARNING, or ERROR).

## Validation Grouping and Ordering

Validations are organized and executed in a specific order:

### Order of Execution
1. **Primary validations** run first in the order they are defined in the protocol validation file (e.g., `belt_fish.py`)
2. **Delayed validations** run only if all primary validations result in OK or WARNING status (no errors)

### Delayed Validations
Some validations are marked with `delay_validation=True`. These are expensive or complex checks that should only run if basic validations pass.

**Why delay validations?**
- Avoid expensive operations if basic validation already failed
- Prevent confusing error messages when fundamental data is invalid
- Most commonly used for the "dry submit" validator

**The Dry Submit Validator:**
This special delayed validator attempts to actually write the collect record to the database in a test transaction (which is then rolled back). It catches issues that may not be detectable by field-level checks, such as:
- Complex database constraint violations
- Issues in related model creation
- Problems with data transformation during the write process

If the dry submit fails, users see an ERROR indicating the record cannot be submitted, often with details about what database operation failed.

### Validation Result Storage
After validations run, results are stored in a nested structure that mirrors the collect record structure:

```
{
  "version": "2",
  "status": "ok" | "warning" | "error",
  "results": {
    "$record": [
      // Record-level validation results
    ],
    "data.sample_event.site": [
      // Field-level validation results for site
    ],
    "data.obs_belt_fishes": [
      [ /* results for observation 0 */ ],
      [ /* results for observation 1 */ ],
      [ /* results for observation 2 */ ],
      // ... one array per observation
    ]
  }
}
```

### Validation Status Hierarchy
The overall validation status follows a hierarchy:
- If ANY validation returns ERROR → overall status is ERROR
- Else if ANY validation returns WARNING → overall status is WARNING
- Else → overall status is OK

## Protocol-Specific Validations

Each survey protocol (Belt Fish, Benthic LIT, Benthic PIT, etc.) has its own set of validations defined in a dedicated file under `src/api/submission/validations/`. The validation sets are tailored to the specific requirements and data structure of each protocol.

**Common validation patterns across protocols:**
- Sample event data (site, management, date) validation
- Observer requirements
- Transect/quadrat specifications
- Protocol-specific observation validation (fish, benthic, bleaching, etc.)
- Uniqueness checks to prevent duplicate submissions
- Dry submit validation (always last, always delayed)

## Summary of Key Concepts

| Concept | Values | Purpose |
|---------|--------|---------|
| **Validation Level** | `FIELD_LEVEL`, `ROW_LEVEL`, `RECORD_LEVEL` | Defines what scope of data is being validated |
| **Validation Type** | `VALUE_VALIDATION_TYPE`, `LIST_VALIDATION_TYPE` | Defines whether validation returns one result or many |
| **Validation Status** | `OK`, `WARNING`, `ERROR` | The outcome of a validation check |
| **Delayed Validation** | `True` or `False` | Whether validation waits for other validations to pass |
| **Results Location** | Field path or `$record` | Where validation results are stored in the results structure |

## Understanding Validation Messages

When a validation fails or warns, it includes:
- **name**: The validator name (e.g., "depth_validator", "fish_size_validator")
- **status**: The validation outcome (ok/warning/error)
- **code**: A machine-readable error code (e.g., "required", "depth_out_of_range")
- **context**: Additional information about the failure (e.g., which observation, what the invalid value was)
- **fields**: Which field(s) were checked by this validator


# Collect Record Validations v2 requests and responses

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
