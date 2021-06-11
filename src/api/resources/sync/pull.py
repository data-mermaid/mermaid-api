from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db import connection



def _get_subquery(queryset, pk_field_name):
    cur = connection.cursor()
    try:
        table_name = queryset.model._meta.db_table
        queryset = queryset.extra(select={"__pk__": f'"{table_name}"."{pk_field_name}"'})
        qry = queryset.query
        template_sql, params = qry.sql_with_params()
        sql = cur.mogrify(template_sql, params)
    finally:
        cur.close()
    return sql.decode()


def _get_records(viewset, filters):
    queryset = viewset.get_queryset()
    model_class = queryset.model
    pk_field_name = model_class._meta.pk.column
    sub_query = _get_subquery(queryset, pk_field_name)
    table_name = model_class._meta.db_table

    updates_filters = [
        "revision.deleted = false",
        *filters
    ]

    updates_sql = f"""
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
            model_select
        INNER JOIN
            revision
        ON
            revision.record_id = model_select."__pk__"
        WHERE
            {" AND ".join(updates_filters)}
        ORDER BY
            revision.updated_on DESC, revision.revision_num  DESC
    """

    updates = queryset.raw(updates_sql)
    

    delete_filters = [
        f'"revision"."table_name" = \'{table_name}\'',
        '"revision"."deleted" = true',
        *filters
    ]
    deletes_sql = f"""
        SELECT
            "revision"."record_id",
            "revision"."revision_num"
        FROM
            "revision"
        WHERE
            {" AND ".join(delete_filters)}
    """

    try:
        cur = connection.cursor()
        cur.execute(deletes_sql)
        deletes = [
            {"id": row[0], "revision_num": row[1]}
            for row in cur.fetchall()
        ]

    finally:
        cur.close()

    return updates, deletes


def get_record(viewset, record_id):
    """Get model record with revision fields included.

        - revision_record_id
        - revision_updated_on
        - revision_revision_num
        - revision_deleted

    :param viewset: ModelViewSet instance
    :type viewset: rest_framework.serializers.viewsets.ModelViewSet
    :param record_id: Id of record to return
    :type record_id: UUID or str
    :return: Updates and deletes
    :rtype: tuple
    """
    filters = [f"revision.record_id = '{record_id}'::uuid"]
    updates, deletes = list(_get_records(viewset, filters))
    if len(updates) == 1:
        return updates[0]
    elif len(deletes) == 1:
        return deletes[0]
    elif not deletes and not updates:
        raise ObjectDoesNotExist()

    raise MultipleObjectsReturned()


def get_records(viewset, revision_num=None, project=None, profile=None):
    """Fetch model records with optional filters:
        * revision numbers greater than `revision_num`
        * `project` uuid
        * `profile` uuid

    Records include revision fields:

        - revision_record_id
        - revision_updated_on
        - revision_revision_num
        - revision_deleted

    :param viewset: ModelViewSet instance
    :type viewset: rest_framework.serializers.viewsets.ModelViewSet
    :param revision_num: Revision number, defaults to None
    :type revision_num: int, optional
    :param project: Project id, defaults to None
    :type project: UUID, optional
    :param profile: Profile id, defaults to None
    :type profile: UUID, optional
    :return: Updates and deletes
    :rtype: tuple
    """
    table_name = viewset.get_queryset().model._meta.db_table
    filters = [f"revision.table_name = '{table_name}'"]

    if project is not None:
        filters.append(f"revision.project_id = '{project}'::uuid")

    if profile is not None:
        filters.append(f"revision.profile_id = '{profile}'::uuid")

    if revision_num is not None:
        filters.append(f"revision.revision_num > {revision_num}")

    return _get_records(viewset, filters)


def serialize_revisions(serializer, updates, deletes, skip_deletes=False):
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
    serialized_updates = []
    serialized_deletes = []

    serialized_updates = serializer(updates, many=True, context={"request": None}).data
    for n, rec in enumerate(updates):
        rev_num = rec.revision_revision_num

        if last_rev_num is None or rev_num > last_rev_num:
            last_rev_num = rev_num
        
        serialized_updates[n]["_last_revision_num"] = rev_num
        serialized_updates[n]["_modified"] = False
        serialized_updates[n]["_deleted"] = False


    if skip_deletes is False:
        for rec in deletes:
            rev_num = rec["revision_num"]

            if last_rev_num is None or rev_num > last_rev_num:
                last_rev_num = rev_num
        
            serialized_deletes.append(
                {"id": str(rec["id"]), "_last_revision_num": rev_num}
            )

    return {"updates": serialized_updates, "deletes": serialized_deletes, "last_revision_num": last_rev_num}


def get_serialized_records(viewset, revision_num=None, project=None, profile=None):
    """Convenience that wraps get_records and serialize_revisions.  If no updates
    are found, last_revision_num is set to revision_num.

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
    updates, deletes = get_records(viewset, revision_num, project, profile)

    serialized_revisions = serialize_revisions(
        serializer, updates, deletes, skip_deletes=revision_num is None
    )

    serialized_revisions["last_revision_num"] = (
        serialized_revisions["last_revision_num"] or revision_num
    )

    return serialized_revisions
