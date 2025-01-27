import os
import shlex
import subprocess

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS
from django.db.transaction import Atomic, get_connection

sql_dir = os.path.join(os.path.sep, "tmp", "mermaid")
db_params = {
    "db_user": settings.DATABASES["default"]["USER"],
    "db_host": settings.DATABASES["default"]["HOST"],
    "db_name": settings.DATABASES["default"]["NAME"],
}


def _run(command, std_input=None, to_file=None):
    try:
        proc = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except Exception as e:
        print(command)
        raise e

    data, err = proc.communicate(input=std_input)

    if to_file is not None:
        with open(to_file, "w") as f:
            f.write("DATA: \n")
            f.write(data)
            f.write("ERR: \n")
            f.write(err)
    else:
        print(data)
        print(err)


def view_pickle(view_name):
    sql_file = os.path.join(sql_dir, "{}.sql".format(view_name))

    dump_params = db_params.copy()
    dump_params["view"] = view_name
    dump_params["sql_loc"] = sql_file

    dump_cmd_str = (
        "pg_dump -U {db_user} -h {db_host} -d {db_name} -t public.{view} --schema-only -f {sql_loc}"
    )
    dump_command = shlex.split(dump_cmd_str.format(**dump_params))
    _run(dump_command)

    drop_params = db_params.copy()
    drop_params["view"] = view_name

    drop_cmd_str = (
        "psql -U {db_user} -h {db_host} -d {db_name} -c 'DROP MATERIALIZED VIEW public.{view}'"
    )
    drop_command = shlex.split(drop_cmd_str.format(**drop_params))
    _run(drop_command)


def view_unpickle(view_name):
    sql_file = os.path.join(sql_dir, "{}.sql".format(view_name))
    if not os.path.isfile(sql_file):
        print("Cannot unpickle: {} does not exist".format(sql_file))
        return

    params = db_params.copy()
    params["sql_loc"] = sql_file

    cmd_str = "psql -U {db_user} -h {db_host} -d {db_name} -q -f {sql_loc}".format(**params)
    command = shlex.split(cmd_str)
    _run(command)

    _run(shlex.split("rm {}".format(sql_file)))


class LockedAtomicTransaction(Atomic):
    """
    Does a atomic transaction, but also locks the entire table for any transactions,
    for the duration of this transaction. Although this is the only way to avoid
    concurrency issues in certain situations, it should be used with
    caution, since it has impacts on performance, for obvious reasons...
    """

    def __init__(self, model, using=None, savepoint=None, durable=False):
        if using is None:
            using = DEFAULT_DB_ALIAS
        super().__init__(using, savepoint, durable)
        self.model = model

    def __enter__(self):
        super(LockedAtomicTransaction, self).__enter__()

        # Make sure not to lock, when sqlite is used, or you'll run into problems while running tests!!!
        if settings.DATABASES[self.using]["ENGINE"] != "django.db.backends.sqlite3":
            cursor = None
            try:
                cursor = get_connection(self.using).cursor()
                cursor.execute(f"LOCK TABLE {self.model._meta.db_table}")
            finally:
                if cursor and not cursor.closed:
                    cursor.close()
