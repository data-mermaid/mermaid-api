from django.core.exceptions import ObjectDoesNotExist


def _get_model_subquery(model_class):
    return str(model_class.objects.all().query)


def _get_records(model_class, filters):
    sub_query = _get_model_subquery(model_class)
    pk_field_name = model_class._meta.pk.column

    sql = f"""
        WITH model_select AS (
            {sub_query}
        )
        SELECT
            model_select.*,
            revision.record_id as revision_record_id,
            revision.updated_on as revision_updated_on,
            revision.revision_num as revision_revision_num,
            revision.deleted as revision_deleted
        FROM
            revision
        LEFT JOIN
            model_select
        ON
            revision.record_id = model_select."{pk_field_name}"
        WHERE
            {" AND ".join(filters)}
        ORDER BY
            revision.updated_on DESC, revision.revision_num  DESC
    """

    return model_class.objects.raw(sql)


def get_record(model_class, record_id):
    """Get model record with revision fields included.

        - revision_record_id
        - revision_updated_on
        - revision_revision_num
        - revision_deleted

    :param model_class: Model class
    :type model_class: django.db.models.Model
    :param record_id: Id of record to return
    :type record_id: UUID or str
    :return: Model class instance
    :rtype: django.db.models.Model
    """
    filters = [f"revision.record_id = '{record_id}'::uuid"]
    result = list(_get_records(model_class, filters))
    if not result:
        raise ObjectDoesNotExist()
    
    return result[0]


def get_records(model_class, revision_num=None, project=None, profile=None):
    """Fetch model records with optional filters:
        * revision numbers greater than `revision_num`
        * `project` uuid
        * `profile` uuid

    Records include revision fields:

        - revision_record_id
        - revision_updated_on
        - revision_revision_num
        - revision_deleted

    :param model_class: Model class
    :type model_class: django.db.models.Model
    :param revision_num: Revision number, defaults to None
    :type revision_num: int, optional
    :param project: Project id, defaults to None
    :type project: UUID, optional
    :param profile: Profile id, defaults to None
    :type profile: UUID, optional
    :return: Model class instances
    :rtype: django.db.models.query.RawQuerySet
    """
    table_name = model_class._meta.db_table
    filters = [f"revision.table_name = '{table_name}'"]

    if project is not None:
        filters.append(f"revision.project_id = '{project}'::uuid")

    if profile is not None:
        filters.append(f"revision.profile_id = '{profile}'::uuid")

    if revision_num is not None:
        filters.append(f"revision.revision_num > {revision_num}")

    return _get_records(model_class, filters)


def serialize_revisions(serializer, record_set, skip_deletes=False):
    """Serialize model instances that include the field additions of:

        - revision_record_id
        - revision_updated_on
        - revision_revision_num
        - revision_deleted
    
    (record_set: from get_record() or get_records())

    :param serializer: Model's serializer
    :type serializer: rest_framework.serializers.ModelSerializer
    :param record_set: Model instances
    :type record_set: django.db.models.query.RawQuerySet or list
    :param skip_deletes: Don't include deleted records in result, defaults to False
    :type skip_deletes: bool, optional
    :return: Returns updates, deletes and last_revision_num
    :rtype: dict
    """

    last_rev_num = None
    updates = []
    deletes = []
    for rec in record_set:
        rev_num = rec.revision_revision_num

        if last_rev_num is None or rev_num > last_rev_num:
            last_rev_num = rev_num

        if rec.revision_deleted is True and skip_deletes is False:
            deletes.append(
                {"id": str(rec.revision_record_id), "_last_revision_num": rev_num}
            )
            continue
        elif rec.revision_deleted and skip_deletes is True:
            continue

        serialized_rec = serializer(rec, context={"request": None}).data
        serialized_rec["_last_revision_num"] = rev_num
        serialized_rec["_modified"] = False
        serialized_rec["_deleted"] = False
        updates.append(serialized_rec)

    return {
        "updates": updates,
        "deletes": deletes,
        "last_revision_num": last_rev_num,
    }


def get_serialized_records(viewset, revision_num=None, project=None, profile=None):
    """Convenience that wraps get_records and serialize_revisions.

    :param viewset: Viewset of the record source to serialize.
    :type viewset: rest_framework.viewsets.ModelViewSet
    :param revision_num: Revision number, defaults to None
    :type revision_num: int, optional
    :param project: Project id, defaults to None
    :type project: UUID, optional
    :param profile: Profile id, defaults to None
    :type profile: UUID, optional
    :return: Returns updates, deletes and last_revision_num
    :rtype: dict
    """

    serializer = viewset.serializer_class
    model_class = serializer.Meta.model

    record_set = get_records(model_class, revision_num, project, profile)

    return serialize_revisions(
        serializer, record_set, skip_deletes=revision_num is None
    )
