sqltables
---------

Use SQL statement to defined the datasource for a Django model.


## Usage

Assume you have a table in your database, something like this...

```
 CREATE TABLE IF NOT EXISTS mermaid_testing_table (
    id serial primary key,
    name varchar(100),
    age integer,
    category varchar(100)
)
```

Your model could look like this...

```
class TestUserModel(models.Model):
    sql = """
        SELECT *
        FROM mermaid_testing_table
        WHERE category = '%s'
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
```

Few things to note:

* `sql`: Select statement that will be used to etch the data.  The model fields defined
need to exist in the select columns.
* `sql_args`: Arguments that are resolved in the `sql` when running queries.
* `db_table`: In SQLTables, `db_table` is used to define an alias for the `sql` statement.
* `managed = False`: This is **NOT** a managed table

## Querying


```
qry = TestUserModel.objects.all().sql_table(category="category1")
qry = qry.filter(name="user1").order_by("-age")

```



## Limitations

* When filtering you must call `all()` first before calling `sql_table`
* Does not support joins. For example:

    `TestUserModel.objects.all().sql_table().filter(user__name="Matt")`