"""BigQuery Database functions and helpers"""
# Standard library imports
from datetime import datetime
import logging
import os
import re

# Third-party imports
from google.cloud import bigquery

# Local imports
import gcp
from settings import (
    LazySetting, logger,
    GOOGLE_BIGQUERY_DATASET, GOOGLE_BIGQUERY_CTE, GOOGLE_BIGQUERY_DEFINITIONS,
    GOOGLE_BIGQUERY_QUERIES,
    GOOGLE_CLOUD_PROJECT, GOOGLE_COMPUTE_REGION,
    CORPUS_ID
)
from utils import (
    duck_dict
)

def _bq_client(project=GOOGLE_CLOUD_PROJECT):
    """Return a BigQuery client"""
    return bigquery.Client(
        project=str(GOOGLE_CLOUD_PROJECT if project is None else project),
        credentials=gcp.credentials())


def _bq_dataset(project=GOOGLE_CLOUD_PROJECT, dataset=GOOGLE_BIGQUERY_DATASET):
    """Return a BigQuery dataset reference"""
    dataset_id=_bq_idstr(str(
        GOOGLE_BIGQUERY_DATASET if dataset is None else dataset))
    dataset_ref = bigquery.DatasetReference(
        project=str(GOOGLE_CLOUD_PROJECT if project is None else project),
        dataset_id=dataset_id)
    return dataset_ref


def _bq_param(name, value):
    """Return a BigQuery query parameter"""
    bq_type = "STRING"
    if isinstance(value, int):
        bq_type = "INT64"
    if isinstance(value, list):
        return bigquery.ArrayQueryParameter(name, bq_type, value)
    return bigquery.ScalarQueryParameter(name, bq_type, str(value))


def _bq_idstr(value, dashes=False, tolower=False):
    """Convert a value to a valid BigQuery identifier (table, column, etc.)"""
    assert value is not None, "BigQuery ID cannot be None"
    value = str(value)
    assert value, "Empty BigQuery ID"
    if dashes:
        id = re.sub(r"[^-a-zA-Z0-9_]+", "_", str(value))
    else:
        id = re.sub(r"[^a-zA-Z0-9_]+", "_", str(value))
    id = id.strip('_')
    if tolower:
        return id.lower()
    return id


def api(version="v2"):
    """Build discovery-based API client for BigQuery"""
    import googleapiclient.discovery
    return googleapiclient.discovery.build(
        "bigquery", version, credentials=gcp.credentials())


def clean_sql(sql, pretty=False):
    """Clean up SQL statement and fix common issues"""
    # properly backtick-escaped `IDs` by replacing funny characters
    sql = re.sub(
        r'`([^`\n]+)`',
        lambda m: re.sub(r'[^`a-zA-Z0-9]', '_', m.group(0)),
        sql)

    # HACK: replace underscores back to dashes for UUIDs (dataset / table names)
    sql = re.sub(
        r'`[a-f0-9]{8}_[a-f0-9]{4}_[a-f0-9]{4}_[a-f0-9]{4}_[a-f0-9]{12}`',
        lambda m: m.group(0).replace('_', '-'),
        sql)

    if pretty:
        kwargs = {
            "reindent": True,
            "keyword_case": 'upper',
        }
    else:
        kwargs = {
            "strip_comments": True,
            "strip_whitespace": True,
        }

    # cleanup SQL using sqlparse and regex
    try:
        import sqlparse
        sql = sqlparse.format(sql, **kwargs)
    except ModuleNotFoundError:
        pass
    return sql


def common_table_expressions(subfolder=GOOGLE_BIGQUERY_CTE,
                             project_id=GOOGLE_CLOUD_PROJECT,
                             dataset=GOOGLE_BIGQUERY_DATASET):
    """Return dict of Common Table Expressions to use with BigQuery calls"""
    cte_map = {}
    if not str(subfolder):
        return cte_map
    dirname = os.path.join(os.path.dirname(__file__), str(subfolder))
    for filename in os.listdir(dirname):
        if filename.endswith(".bq"):
            with open(os.path.join(dirname, filename), "rt") as f:
                cte_name = filename.rsplit('.', 1)[0]
                cte_contents = f.read().replace(
                    "__dataset__", str(dataset)).replace(
                    "__project__", str(project_id))

                # replace /`ck<dev|test|prod|etc>/ with dataset in cte_contents
                cte_contents = re.sub(
                    r"\/`ck[a-z]{3,6}?\.", f"`{dataset}.", cte_contents)

                cte_map[cte_name] = cte_contents

    # sort CTE map by key name
    return dict(sorted(cte_map.items(), key=lambda item: item[0]))


def definition(name, subfolder=GOOGLE_BIGQUERY_DEFINITIONS, type=None,
               raw=False, project_id=GOOGLE_CLOUD_PROJECT,
               dataset=GOOGLE_BIGQUERY_DATASET):
    """Load JSON definition data for a BigQuery table or view"""
    if not str(subfolder):
        return None

    if type is None:
        type = "view" if is_view_name(name) else "table"

    def_dict = None
    plural_type = type + "s"  # tables, views, etc.
    dirname = os.path.join(os.path.dirname(__file__), str(subfolder),
                           plural_type)
    filename = os.path.join(dirname, f"{name}.json")
    if os.path.exists(filename):
        with open(filename, "rt") as f:
            def_dict = duck_dict(f.read())

    if def_dict is None:
        return None

    if type in {"table", "view"}:  # add tableReference and cast to Table class
        def_dict["tableReference"] = {
            "projectId": str(project_id),
            "datasetId": str(dataset),
            "tableId": str(name)
        }

        if type == "view":
            view_query = queries(project_id=project_id, dataset=dataset)[name]
            def_dict["view"] = {"query": view_query}

        if not raw:
            table = bigquery.Table.from_api_repr(def_dict)
            if type == "view":
                table.view_query = view_query
            return table

    # for all other misc. definitions just return the dict
    return def_dict


def insert(table, **kwargs):
    """Streaming insert of a single row into a BigQuery table
    
    See: cloud.google.com/python/docs/reference/bigquery/latest/google.cloud.bigquery.client.Client#google_cloud_bigquery_client_Client_insert_rows_json
    """
    from google.api_core.exceptions import Conflict, NotFound
    client = _bq_client(project=kwargs.get("project"))

    dataset =_bq_dataset(
        project=kwargs.get("project"), dataset=kwargs.get("dataset"))
    table_ref = dataset.table(table)

    # insert_rows_json() is faster because no table schema need be known BUT
    # it also does NOT apply local type conversions as a trade-off
    # (so we must convert datetime objects to ISO strings here)
    row_to_insert = {
        key: value for key, value in kwargs.items()
        if key not in {"project", "dataset", "table"}}
    for key, value in row_to_insert.items():
        if isinstance(value, datetime):
            row_to_insert[key] = value.isoformat()
        elif isinstance(value, LazySetting):
            row_to_insert[key] = value.get()

    attempt, max_attempts = 0, 1
    rows_to_insert = [row_to_insert]
    while attempt < max_attempts:
        attempt += 1
        try:
            logger.debug("[BQ] INSERT: %s -> %s", table_ref, row_to_insert)
            errors = client.insert_rows_json(table_ref, rows_to_insert)
            if errors:
                logger.error("[BQ] INSERT ERROR: %s", errors)
                return False
        except NotFound:
            table_def = definition(table, type="table",
                                   project_id=table_ref.project,
                                   dataset=table_ref.dataset_id)
            if not table_def:
                logger.error("[BQ] INSERT NO DEFINITION: %s", table)
                return False
            elif attempt > 1:
                logger.error("[BQ] INSERT NOT FOUND: %s", table_ref)
                return False
            try:
                client.create_table(table_def)
            except Conflict:  # 409 Conflict: Table already exists
                pass  # this can be due to eventual consistency issues
            max_attempts += 1
        except Exception as e:
            logger.error("[BQ] INSERT EXCEPTION: %s", e)
            return False
    return True


def is_view_name(name):
    """Return True if name is a view name"""
    if "view" in name.split("_"):
        return True
    if name.startswith("v_") or name.endswith("_v"):
        return True
    if name.startswith("vw_") or name.endswith("_vw"):
        return True
    return False


def load_csv(filename, table=None, description=None, labels=None,
             dataset=CORPUS_ID, location=GOOGLE_COMPUTE_REGION, checksum=None,
             overwrite=False, nowait=False, project=GOOGLE_CLOUD_PROJECT):
    """Load a CSV file into a BigQuery table
    :param filename: Name of CSV file to load
    :param table: Name of table to load into or None to use filename
    :param description: Description of table to create
    :param labels: Optional dictionary of labels to add to table
    :param dataset: Name of dataset to load into
    :param location: Location of dataset to load into
    :param checksum: Optional checksum to use to skip loading if already loaded
    :param overwrite: Overwrite existing table if it exists?
    :param nowait: Return immediately without waiting for job to complete
    :param project: Name of project to load into
    :return: BigQuery Job
    """
    from google.api_core.exceptions import NotFound

    client = _bq_client(project=project)
    dataset_ref = client.dataset(_bq_idstr(str(dataset)))

    labels = labels.copy() if labels else {}

    # create "checksum" label so we can detect changes
    checksum = _bq_idstr(checksum, tolower=True)
    if len(checksum) > 63:
        checksum = checksum[:63]
    labels["checksum"] = checksum

    table = make_name(filename) if table is None else table
    table_ref = dataset_ref.table(str(table))
    is_new_table = False

    if not overwrite:
        try:
            table_obj = client.get_table(table_ref)
            # retrieve value of label "checksum"
            table_checksum = table_obj.labels.get("checksum", "")
            if checksum and labels["checksum"] == table_checksum:
                logger.info("[BQ] SKIP: %s -> %s (checksum=%s)",
                            filename, table, checksum)
                return None
        except NotFound as notfound_err:
            is_new_table = True
            if "Not found: Dataset" in str(notfound_err):
                logger.info("[BQ] Creating dataset %s", dataset_ref)
                dataset_obj = bigquery.Dataset(dataset_ref)
                dataset_obj.location = str(location)
                dataset_obj.default_table_expiration_ms = \
                    30 * 24 * 60 * 60 * 1000  # 30 days
                dataset_obj = client.create_dataset(dataset_obj)
            pass

    job_extra_kwargs = {}
    if labels:
        job_extra_kwargs["labels"] = labels
    if is_new_table and description:
        job_extra_kwargs["destination_table_description"] = description

    job_config = bigquery.LoadJobConfig(
        allow_quoted_newlines=True,
        allow_jagged_rows=True,
        autodetect=True,  # Automatically detect the schema
        max_bad_records=9999,
        skip_leading_rows=1,
        source_format=bigquery.SourceFormat.CSV,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        **job_extra_kwargs,
    )

    if filename.startswith("gs://"):
        job = client.load_table_from_uri(filename, table_ref,
                                         job_config=job_config)
    else:
        assert os.path.exists(filename), "File not found: %s" % filename

        # count rows in existing CSV
        num_rows = 0
        with open(filename, "rt") as f:
            num_rows = sum(1 for line in f)
            num_rows -= 1  # ignore header row

        logger.info("[BQ] Loading %s (%.2f MB, %d rows) into %s:%s", filename,
                    os.path.getsize(filename) / 1024 / 1024, num_rows,
                    dataset, table)
        with open(filename, "rb") as source_file:
            job = client.load_table_from_file(source_file, table_ref,
                                            job_config=job_config)

    logger.info("[BQ] JOB %s: LOAD %s -> %s", job.job_id, filename, table)

    if not nowait:
        wait(job)

    if not is_new_table or not nowait:
        table_obj = client.get_table(table_ref)
        logger.info("[BQ] Loaded %d rows and %d columns to %s",
                    table_obj.num_rows, len(table_obj.schema), table_obj)

        updated_fields = []

        if description:
            table_obj.description = description
            updated_fields += ["description"]

        if labels:
            table_obj.labels = labels
            updated_fields += ["labels"]

        if not is_new_table and updated_fields:
            table_obj = client.update_table(table_obj, updated_fields)

    return job


def make_name(filename, dashes=False):
    """Make a BigQuery table name from a URI or filename
    :param filename: Filename or URI to use
    :param dashes: Allow dash characters (OK in tables not in dataset)
    """
    return _bq_idstr(os.path.basename(filename).rsplit('.', 1)[0],
                     dashes=dashes)


def queries(subfolder=GOOGLE_BIGQUERY_QUERIES,
            project_id=GOOGLE_CLOUD_PROJECT,
            dataset=GOOGLE_BIGQUERY_DATASET, cte=None):
    """Return dict of named queries to use with BigQuery calls"""
    if cte is None:
        cte = common_table_expressions(project_id=project_id, dataset=dataset)
    if cte:
        sql_prefix = "WITH " + ", ".join([
            f"{name} AS ({sql})" for name, sql in cte.items()]) + "\n\n"
    else:
        sql_prefix = ""

    view_map = {}
    if not str(subfolder):
        return view_map
    dirname = os.path.join(os.path.dirname(__file__), str(subfolder))
    for filename in os.listdir(dirname):
        if filename.endswith(".bq"):
            with open(os.path.join(dirname, filename), "rt") as f:
                view_name = filename.rsplit('.', 1)[0]
                view_contents = f.read().replace(
                    "__dataset__", str(dataset)).replace(
                    "__project__", str(project_id))

                # replace /`ck<dev|test|prod|etc>/ with dataset in view_contents
                view_contents = re.sub(
                    r"\/`ck[a-z]{3,6}?\.", f"`{dataset}.", view_contents)

                view_map[view_name] = sql_prefix + view_contents

    # sort view map by key name
    return dict(sorted(view_map.items(), key=lambda item: item[0]))


def query(sql, *args, **kwargs):
    """Execute a query against the BigQuery database
    :param sql: SQL query to execute
    :param args: Positional arguments (currently ignored!)
    :param kwargs: Keyword arguments to use as query parameters
    :return: List of `google.cloud.bigquery.Row` objects 
    """
    return list(query_yield(sql, *args, **kwargs))


def query_first(sql, *args, **kwargs):
    """Execute a query against the BigQuery database
    :param sql: SQL query to execute
    :param args: Positional arguments (currently ignored!)
    :param kwargs: Keyword arguments to use as query parameters
    :return: First row of results
    """
    for row in query_yield(sql, *args, **kwargs):
        return row


def query_one(sql, *args, **kwargs):
    """Execute a query against the BigQuery database
    :param sql: SQL query to execute
    :param args: Positional arguments (currently ignored!)
    :param kwargs: Keyword arguments to use as query parameters
    :return: First column of first row of results
    """
    for row in query_yield(sql, *args, **kwargs):
        return row[0]


def query_dicts(sql, *args, **kwargs):
    """Execute a query against the BigQuery database
    :param sql: SQL query to execute
    :param args: Positional arguments (currently ignored!)
    :param kwargs: Keyword arguments to use as query parameters
    :return: List of dictionary objects
    """
    return [dict(row.items()) for row in query_yield(sql, *args, **kwargs)]


def query_yield(sql, *args, **kwargs):
    """Execute a query against the BigQuery database
    :param sql: SQL query to execute
    :param args: Positional arguments (currently ignored!)
    :param kwargs: Keyword arguments to use as query parameters
    :return: Generator of BigQuery Row objects"""
    from google.api_core.exceptions import BadRequest, NotFound

    # sanity check SQL (must be query not DDL)
    assert sql
    sql_words = clean_sql(sql, pretty=False).split()
    assert sql_words[0].upper() in {"SELECT", "WITH"}, \
        "SQL must start with SELECT or WITH"

    # SQL prefix (e.g. CTEs) is processed by not logged
    cte = kwargs.pop("cte", common_table_expressions())
    if cte:
        assert isinstance(cte, dict)
        sql_prefix = "WITH " + ", ".join([
            f"{name} AS ({sql})" for name, sql in cte.items()]) + "\n\n"
    else:
        sql_prefix = ""

    if 'where' in kwargs:
        where = kwargs.pop("where")
        if isinstance(where, str):
            sql += " WHERE " + where
        elif where:
            sql += " WHERE " + " AND ".join(where)

    if 'order_by' in kwargs:
        order_by = kwargs.pop("order_by")
        if isinstance(order_by, str):
            sql += " ORDER BY " + order_by
        elif order_by:
            sql += " ORDER BY " + ", ".join(order_by)

    job_config = bigquery.QueryJobConfig()
    query_params = []

    # positional parameters: use args in order
    if len(args) > 0:
        query_params += [_bq_param(None, arg) for i, arg in enumerate(args)]

    # named parameters: find matching kwargs
    for kwarg_name, kwarg_value in kwargs.items():
        if f"@{kwarg_name}" not in sql:
            continue
        query_params += [_bq_param(kwarg_name, kwarg_value)]

    if query_params:
        job_config.query_parameters = query_params

    # set default project & dataset
    job_config.default_dataset = _bq_dataset(
        project=kwargs.get("project"), dataset=kwargs.get("dataset"))

    # get flattened version of SQL with whitespace normalized
    logger.debug("[BQ] %s: %s %s", job_config.default_dataset,
                 " ".join(sql.strip().split()), query_params)

    try:
        results = _bq_client(project=kwargs.get("project")).query(
            sql_prefix + sql, job_config=job_config)
        for row in results:
            yield row
    except (BadRequest, NotFound) as _:
        # log the ENTIRE query if it fails
        logger.error("[BQ] %s: %s %s %s", job_config.default_dataset,
                      sql_prefix, " ".join(sql.strip().split()), query_params)
        raise


def save(name_or_definition, type=None,
         fields=("schema","description","labels","view_query"),
         project_id=GOOGLE_CLOUD_PROJECT,
         dataset=GOOGLE_BIGQUERY_DATASET):
    """Create/update a BigQuery table or view
    :param name_or_definition: Name of table or view to create or Table object
    :param type: Type of object to create (table or view); default is table
    :param fields: List of fields to update (if table already exists)
    :param project_id: Project ID to create table in
    :param dataset: Dataset to create table in
    :return: Table object
    """
    from google.api_core.exceptions import Conflict

    if isinstance(name_or_definition, str):
        table = definition(name_or_definition, type=type, project_id=project_id,
                           dataset=dataset)
    elif isinstance(name_or_definition, bigquery.Table):
        table = name_or_definition
    else:
        table = None

    if not table:
        raise ValueError("Invalid table: <%s> %s" % (
                         __builtins__['type'](name_or_definition),
                         name_or_definition))

    client = _bq_client(project=table.project)

    # remove "schema" from table definition for views (not allowed in create)
    view_schema = None
    if table.view_query and table.schema is not None:
        view_schema = table.schema
        table_repr = table.to_api_repr()
        table_repr.pop("schema", None)
        table = bigquery.Table.from_api_repr(table_repr)

    try:
        created_table = client.create_table(table)
        if created_table and not table.view_query:
            return created_table
        updated_table = created_table  # for view updates
    except Conflict:  # Already Exists
        updated_table = client.update_table(table, fields)

    # add "schema" in a separate patch call
    if table.view_query and view_schema is not None:
        table.schema = view_schema
        updated_table = client.update_table(table, ["schema"])

    return updated_table


def schema_str(table, dataset=CORPUS_ID, project=GOOGLE_CLOUD_PROJECT):
    """Generate a single-line schema string for a BigQuery table"""
    client = _bq_client(project=project)
    table_obj = client.get_table(client.dataset(_bq_idstr(dataset)).table(table))
    return ",".join([f"{field.name}:{field.field_type}"
                     for field in table_obj.schema])


def wait(jobs, location=GOOGLE_COMPUTE_REGION, project_id=GOOGLE_CLOUD_PROJECT):
    """Wait for a list of BigQuery jobs to complete"""
    if not jobs:
        return
    if not isinstance(jobs, list):
        jobs = [jobs]

    logger.debug("[BQ] START WAIT: %d job(s)", len(jobs))

    client = _bq_client(project=project_id)
    for i, job in enumerate(jobs):
        if isinstance(job, str):
            job = client.get_job(job, location=str(location))
        logger.debug("[BQ] WAIT %d/%d: %s (%s)", 1+i, len(jobs),
                     job.job_id, job.state)
        if job.state == "DONE":
            continue
        job.result()  # wait for job to complete
        logger.debug("[BQ] WAIT %d/%d: %s (%s)", 1+i, len(jobs),
                     job.job_id, job.state)

    logger.debug("[BQ] DONE WAIT: %d job(s)", len(jobs))
