# New Protcol To Do



## Models

- Add data policy to Project model
- Create Sample unit model
- Create Sample unit method model
- Create Observations model
- Add new protocol static variable and include it in PROTOCOL_MAP
- Update TransectMethod model properties (protocol, subclass)

## Admin

- Admin for sample unit method
  - include observations and observers as inlines

## Ingest

- Define and create schema csv file
- Create test ingest csv file
- Create an ingest serializer
- Update utils ingest

## SQL Models

- Create protocol sql models for Observations, Sample Units and Sample Event summaries

## Validation and Submission

- Create any new validators that are needed for the new protocol
- Create serializer for SampleUnitMethod (example: src/api/resources/benthic_photo_quadrat_transect.py)
- Create serializer for protocol observation (example: src/api/resources/obs_benthic_photo_quadrat.py)
- Create serializer for sample unit (example: src/api/resources/quadrat_transect.py)
- Create a protocol writer class (`writer.py`).
- Create a sample unit methods validations file. Examples:
  -  src/api/submission/validations2/belt_fish.py
  -  src/api/submission/validations2/benthic_photo_quadrat_transect.py

## API Endpoints

- Create a sample unit method endpoint serializer (example: BenthicPhotoQuadratTransectMethodSerializer).
- Create observation summary serializers for CSV, JSON and GeoJSON, examples:
  - ObsBenthicPQTCSVSerializer (CSV)
  - BenthicPQTMethodObsSerializer (JSON)
  - BenthicPQTMethodObsGeoSerializer (GeoJSON)
- Create sample unit (SU) summary serializers for CSV, JSON and GeoJSON, examples:
  - BenthicPQTMethodSUCSVSerializer (CSV)
  - BenthicPQTMethodSUSerializer (JSON)
  - BenthicPQTMethodSUGeoSerializer (GeoJSON)
- Create sample event (SE) summary serializers for CSV, JSON and GeoJSON, examples:
  - BenthicPQTMethodSECSVSerializer (CSV)
  - BenthicPQTMethodSESerializer (JSON)
  - BenthicPQTMethodSEGeoSerializer (GeoJSON)
- Create filtersets for Observation, SU and SE viewsets, examples:
  - BenthicPQTMethodObsFilterSet
  - BenthicPQTMethodSUFilterSet
  - BenthicPQTMethodSEFilterSet
- Create viewsets for Observation, SU and SE viewsets, examples:
  - BenthicPQTProjectMethodObsView
  - BenthicPQTProjectMethodSUView
  - BenthicPQTProjectMethodSEView
- Add new function to support new protocol in summary report [summary_report.py](src/api/reports/summary_report.py)
- Create a sample unit method endpoint viewset, example:  
  - BenthicPhotoQuadratTransectMethodView
- Update api/urls.py with new viewsets, example:

```
  ...
  project_router.register(
      r"benthicpqts/obstransectbenthicpqts",
      BenthicPQTProjectMethodObsView,
      "benthicpqtmethod-obs",
  )
  project_router.register(
      r"benthicpqts/sampleunits", BenthicPQTProjectMethodSUView, "benthicpqtmethod-sampleunit"
  )
  project_router.register(
      r"benthicpqts/sampleevents", BenthicPQTProjectMethodSEView, "benthicpqtmethod-sampleevent"
  )
  ...
  project_router.register(
      r"benthicphotoquadrattransectmethods",
      BenthicPhotoQuadratTransectMethodView,
      "benthicphotoquadrattransectmethod",
  )
  ...

```


**API endpoints example files:**
  - [Benthic Photo Quadrat Transect](https://github.com/data-mermaid/mermaid-api/blob/dev/src/api/resources/sampleunitmethods/benthicphotoquadrattransectmethod.py)
  - [Belt Fish](https://github.com/data-mermaid/mermaid-api/blob/dev/src/api/resources/sampleunitmethods/beltfishmethod.py)