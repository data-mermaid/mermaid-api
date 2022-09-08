import pytest

from django.db import connection
from django.contrib.gis.db import models

from sqltables.datastructures import SQLTableArg
from sqltables.query import SQLTableManager


class UserTestModel(models.Model):
    sql = """
        SELECT *
        FROM mermaid_testing_table
        WHERE category = '%(category)s'
    """
    sql_args = dict(category=SQLTableArg(required=True))

    name = models.CharField(max_length=100)
    age = models.IntegerField()
    category = models.CharField(max_length=100)

    class Meta:
        db_table = "mermaid_testing_table_subset"
        managed = False
        app_label = "api"

    objects = SQLTableManager()


class UserTestModel2(models.Model):
    sql = """
        SELECT *
        FROM mermaid_testing_table2
    """
    sql_args = dict()

    name = models.CharField(max_length=100)
    user = models.ForeignKey("api.TestUserModel", on_delete=models.DO_NOTHING)

    class Meta:
        db_table = "mermaid_testing_table_subset2"
        managed = False
        app_label = "api"

    objects = SQLTableManager()


class UserTestModel3(models.Model):
    sql = """
        SELECT *
        FROM mermaid_testing_table
        WHERE category = '%(category)s'
        UNION ALL
        SELECT *
        FROM mermaid_testing_table
        WHERE category = '%(category)s'
    """
    sql_args = dict(category=SQLTableArg(required=True))

    name = models.CharField(max_length=100)
    age = models.IntegerField()
    category = models.CharField(max_length=100)

    class Meta:
        db_table = "mermaid_testing_table_subset3"
        managed = False
        app_label = "api"

    objects = SQLTableManager()


@pytest.fixture
def mermaid_testing_table():
    table_sql = """
        CREATE TABLE IF NOT EXISTS mermaid_testing_table (
            id serial primary key,
            name varchar(100),
            age integer,
            category varchar(100)
        )
    """

    table_sql2 = """
        CREATE TABLE IF NOT EXISTS mermaid_testing_table2 (
            id serial primary key,
            name varchar(100),
            user_id INTEGER
        )
    """

    add_records_sql = """
        INSERT INTO mermaid_testing_table(id, name, age, category)
        VALUES (1, 'user1', 10, 'category1');
        INSERT INTO mermaid_testing_table(id, name, age, category)
        VALUES (2, 'user2', 40, 'category2');
        INSERT INTO mermaid_testing_table(id, name, age, category)
        VALUES (3, 'user3', 99, 'category1');
    """

    add_records_sql2 = """
        INSERT INTO mermaid_testing_table2(name, user_id)
        VALUES ('person1', 1);
        INSERT INTO mermaid_testing_table2(name, user_id)
        VALUES ('person1', 2);
        INSERT INTO mermaid_testing_table2(name, user_id)
        VALUES ('person1', 3);
    """

    with connection.cursor() as cursor:
        cursor.execute(table_sql)
        cursor.execute(table_sql2)
        cursor.execute(add_records_sql)
        cursor.execute(add_records_sql2)

    yield

    # with connection.cursor() as cursor:
    #     cursor.execute("DROP TABLE mermaid_testing_table;")
    #     cursor.execute("DROP TABLE mermaid_testing_table2;")


@pytest.fixture
def user_model_class(mermaid_testing_table):
    return UserTestModel


@pytest.fixture
def user_model_class2(mermaid_testing_table):
    return UserTestModel2


@pytest.fixture
def user_model_multi_parameter_class(mermaid_testing_table):
    return UserTestModel3


@pytest.mark.django_db
def test_sql_table(user_model_class):
    qry = user_model_class.objects.all().sql_table(category="category1")

    assert qry.count() == 2

    qry = qry.filter(name="user1")
    assert qry.count() == 1

    record = qry[0]
    assert record.name == "user1"
    assert record.age == 10
    assert record.category == "category1"


@pytest.mark.django_db
def test_multi_parameter_sql_table(user_model_multi_parameter_class):
    qry = user_model_multi_parameter_class.objects.all().sql_table(category="category1")

    assert qry.count() == 4

    qry = qry.filter(name="user1")
    assert qry.count() == 2


@pytest.mark.django_db
def test_sql_table_ordering(user_model_class):
    qry = user_model_class.objects.all().sql_table(category="category1")
    qry = qry.order_by("-age")
    assert qry[0].age == 99
