# New Protocol To Do



## Models

- Add protocol constant (e.g. `MACROINVERTEBRATE_PROTOCOL = "macroinvertebrate"`) and include it in `PROTOCOL_MAP`
- Create any new lookup/choice models (e.g. transect width options, size bins, groups of interest) using `BaseChoiceModel` or `BaseModel` as appropriate
- Create taxonomy/attribute models if the protocol has its own species hierarchy, using Django multi-table inheritance (MTI) from `BaseAttributeModel`; create subclasses directly (not the parent) when seeding — Django MTI auto-creates the parent row
- Create Sample unit model (subclass of `Transect`)
- Create Sample unit method model (subclass of `TransectMethod`); set `protocol`, `project_lookup`, and `transect` fields
- Create Observations model (subclass of `BaseModel, JSONMixin`); set `project_lookup`
- Add data policy field to `Project` model
- Update `CollectRecord.obs_keys` dict with new protocol key and observation key list
- Update `CollectRecord.sample_unit` with new `elif` branch for the new protocol
- Update `TransectMethod.protocol` and `TransectMethod.subclass` properties with new `elif hasattr(self, ...)` branch

## Admin

- Add data policy field to `ProjectAdmin.exportable_fields`
- Admin for all new lookup/choice models
- Admin for taxonomy models (use list hierarchy: phylum → class → order → family → genus → species; each with list_display, search_fields, list_filter)
- Admin for sample unit method
  - include observations and observers as inlines

## Migrations

- Run `makemigrations` to generate the schema migration
- Write a separate data migration to seed all lookup data (widths, size bins, taxonomy, etc.)
- If the data migration inserts rows with URL or text fields that may exceed Django's default `max_length`, add `AlterField` operations at the top of the data migration (before `RunPython`) so the schema is widened before the data load; do not rely on a subsequent migration for this
- Use `migrations.RunPython.noop` as the reverse function for data migrations (data is not unwound on rollback)

## Project Utilities

- Add `_copy_[protocol]_transects(sample_event_id_map)` function in `src/api/utils/project.py`, mirroring the `_copy_fish_belt_transects` pattern (copy transect, method, observations, observers)
- Call the new function from `_copy_submitted_data`

## Project Resources

- Update `annotate_num_sample_units()` in `src/api/resources/project.py` with a new UNION ALL branch counting sample units for the new protocol (joining through method → transect → sample event → site → project)

## Choices Endpoint

- Import new lookup models in `src/api/resources/choices.py`
- Add lookup querysets and include them in the `get_choices()` return dict

## Attributes Reference Report

- Add a new tab for the protocol's species/attribute data in `src/api/reports/attributes_report.py`
  - Add a tab name constant and include it in `create_workbook_template()`'s `sheet_names` list
  - Write a `write_[protocol]_species(wb)` function following the pattern of `write_fish_species` / `write_benthic`
  - Use `select_related` to traverse the full taxonomy chain in one query; order by full hierarchy then name
  - Call the new function from `write_attribute_reference()`

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
- Create a protocol writer class (`writer.py`)
- Create a sample unit methods validations file. Examples:
  - src/api/submission/validations2/belt_fish.py
  - src/api/submission/validations2/benthic_photo_quadrat_transect.py

## API Endpoints

- Create a sample unit method endpoint serializer (example: BenthicPhotoQuadratTransectMethodSerializer)
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
