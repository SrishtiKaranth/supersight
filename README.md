# Design Document

## 1. Technology Stack

### Processing Engine: PySpark

PySpark was selected as the processing engine because the same DataFrame API and window functions used in this implementation can run on a distributed Spark cluster without modification, making the solution transferable to a production environment without requiring a rewrite. This also aligns with the technology stack referenced in the technical presentation.

While lighter alternatives such as Pandas or DuckDB would be sufficient for the current dataset size, they would need modifications to suit the current stack used by Supersight.

### Storage: PostgreSQL

The aggregated data is consumed by a web application that requires fast, filtered queries by location and date. Relational database tables with proper indexing satisfy this access pattern more effectively than file-based formats such as Parquet or CSV, which are better suited for batch analytics rather than serving a web frontend.

### Web Application: Django

Django was selected for the web application layer as it provides a mature ORM, a built-in templating engine, and a development server that allows for rapid prototyping. The Django models are configured with `managed = False` because the pipeline owns the database schema. Django only reads from the tables and does not participate in schema creation or migration.

## 2. Pipeline Design

The pipeline follows a structured ETL architecture with five stages. This design is informed by the building blocks of ETL architecture as described by Integrate.io (see References in the README).

1. **Extract** reads CSV files from all device directories using an explicitly defined schema (`StructType` with `StringType` for timestamp and `IntegerType` for in/out columns) rather than relying on `inferSchema=True`. This prevents Spark from guessing column types incorrectly when it encounters null or missing values. Device folders are discovered automatically at runtime by scanning the `data/input/` directory, so adding a new device only requires placing its CSV files in a new subfolder without any code changes. The union of all device DataFrames uses `unionByName()` instead of `union()` to prevent silent column misalignment if CSV column ordering varies across devices.

2. **Profile** inspects the raw data before any transformation occurs. This stage reports null counts per column, value ranges for numeric fields, duplicate row counts, and the timestamp range present in the data. During development, profiling revealed two specific issues in the provided dataset: the `out` column in `device_A/2024-01-01.csv` contains a NULL value on one row, and both `device_A/2024-01-02.csv` and `device_B/2024-01-02.csv` contain records with timestamps from `2024-01-01` that have been placed in the wrong date file. These observations directly informed the design of the cleansing stage.

3. **Cleanse** addresses the data quality issue identified during profiling. The only issue in the current dataset is a missing `out` value in `device_A/2024-01-01.csv`. Missing numeric values in the `in` and `out` columns are filled with zero, which is a reasonable default since a missing count indicates no observed movement rather than an unknown value. No rows needed to be dropped from the current dataset as there are no duplicates, no negative counts, and no unparseable timestamps. The cleansing logic is kept intentionally minimal to match the actual data, though it could be extended with additional filters if future data sources introduce other quality issues.

4. **Transform** computes hourly aggregations by truncating each event timestamp to its hour using `date_trunc("hour", ...)`, then grouping by location and hour to sum entries and exits. Net flow is calculated as `total_in - total_out`. Running occupancy is computed using a Spark window function (`Window.partitionBy("location", "date").orderBy("hour")`) that accumulates net flow across hours within the same day, resetting to zero at each date boundary. This partitioning by date is done so that the misplaced record from January 1st appearing in the January 2nd CSV file will still be correctly aggregated under the January 1st occupancy calculation, because the transform groups by the timestamp in the data, not by the source file name. Daily aggregations are derived from the hourly output by summing `total_in` and `total_out` per location per date.

5. **Load** writes the aggregated results to PostgreSQL using `psycopg2.extras.execute_values` with a page size of 1000 rows per batch. This is substantially faster than individual `INSERT` statements because it reduces the number of network round trips to the database. Each table is loaded in its own transaction. If an insert fails, the transaction is rolled back to prevent partial data from being committed, and the exception is re-raised to halt the pipeline. Empty result sets are handled gracefully with a warning log rather than attempting a zero-row insert.

### Pre-flight Validation

Before Spark is initialised or any data is processed, the pipeline performs three sequential checks:

- Executes `SELECT 1` against the database to confirm connectivity. If PostgreSQL is unreachable due to wrong host, port, or credentials, this fails immediately with a clear error rather than allowing the pipeline to proceed and fail later during the load stage.
- Reads and executes the DDL from `sql/create_tables.sql` to create tables and indexes if they do not already exist, then runs `TRUNCATE` to clear previous data. Keeping the DDL in a standalone SQL file means the schema definition is readable without navigating Python code.
- Queries `information_schema.columns` and compares every column name and data type against an expected definition. If a column is missing, has the wrong type, or an unexpected column exists, the pipeline logs each mismatch and terminates. This catches situations such as a manual schema change that would cause the pipeline to insert data into the wrong columns.

These checks run before `SparkSession.builder` is called, avoiding the Spark startup cost when the environment is misconfigured.

## 3. Data Modelling

### Output Tables

The pipeline produces two tables:

- **hourly_aggregations** contains one record per location per hour, including entry and exit counts, net flow, and a running occupancy figure that accumulates within each day and resets at midnight.
- **daily_aggregations** contains one record per location per day, including total entries, total exits, and net flow.

### Column Types

Temporal columns use `TIMESTAMP` and `DATE` types rather than `TEXT`. This was a deliberate choice because the web application needs to sort hourly data chronologically and filter by date. Both operations are faster and correct with native temporal types. Storing timestamps as text would require casting on every query and would sort lexicographically rather than chronologically if the format ever varied. All count columns are defined as `INTEGER NOT NULL` to enforce data integrity at the database level and prevent null values from propagating into dashboard calculations.

### Indexing Strategy

Composite indexes on `(location, date)` are created for both tables. These indexes were chosen to match the exact query pattern of the Django dashboard, which issues queries of the form `WHERE location = %s AND date = %s ORDER BY hour`. Without these indexes, every page load would require a full table scan. With them, PostgreSQL can locate the relevant rows directly via index lookup.

### Partitioning Strategy

At the current data volume (9 hourly rows, 4 daily rows), partitioning would add complexity without measurable benefit. If the dataset were to grow to millions of rows:

- PostgreSQL native range partitioning on the `date` column would allow the query planner to skip irrelevant date partitions entirely, and old data could be dropped by removing a partition rather than running a `DELETE` query.
- Within the Spark transformation, the data is already partitioned by `location` and `date` in the window function specification. This is the required partition strategy for computing per-day occupancy correctly, and it would also distribute work evenly across executor cores on a Spark cluster.

## 4. Performance Considerations

### Current Optimisations

- **Explicit schema on CSV reads.** With `inferSchema=True`, Spark reads data twice:once to guess types, once to parse. Defining the `StructType` upfront cuts that to a single pass.
- **Batch inserts with `execute_values`.** All rows go in a single query instead of one `INSERT` per row. `page_size=1000` controls how many rows fit per `VALUES` clause.
- **Single-pass window functions.** Running occupancy uses a cumulative sum over a sorted partition:O(n). A self-join approach where each row sums all preceding rows would be O(n²).
- **Pre-flight checks before Spark initialisation.** Database connectivity, schema creation, and validation all run via `psycopg2` before `SparkSession.builder` is called, so a bad config fails in milliseconds instead of after the 3-5 second JVM startup.

### Scaling to 100x Data Volume

**Processing:**
- Deploy Spark on a cluster (EMR or Dataproc) instead of local mode. The only code change is pointing `.master()` at the cluster URL.
- The `data/input/{device}/{date}.csv` folder structure already maps to Spark partitions. 1000 devices over 365 days would give 365,000 files processed in parallel.

**Storage:**
- Switch from truncate-and-reload to upserts (`INSERT ... ON CONFLICT ... DO UPDATE`) with a `last_processed` watermark table to only ingest new data.
- For heavy analytical scans, a columnar engine like TimescaleDB or ClickHouse would outperform row-oriented PostgreSQL.

**Scheduling:**
- Use Dagster to run the pipeline on a schedule, retry failed stages automatically, and track run history through its web UI.
- Only process new data each run by storing the last processed timestamp in a `pipeline_runs` table and skipping files that have already been ingested.

## 5. Current Trade-offs

1. **No retry logic.** If a stage fails (e.g. a transient database timeout during load), the entire pipeline stops. There is no automatic retry at the stage level.
3. **Credentials in environment variables.** Database credentials are read from a `.env` file. This is acceptable for local development but not suitable for production where secrets should be stored in a dedicated secrets manager.
4. **Spark runs in local mode.** All processing happens on a single machine. This is sufficient for the current dataset but would need a cluster deployment for larger volumes.
5. **CSV as the input format.** CSVs are uncompressed, have no schema, and must be fully parsed on every read. A format like Parquet would be more efficient at scale. CSVs also limit the pipeline to batch processing. For real-time updates, sensors would push events to Kafka or RabbitMQ and a stream processor like Spark Streaming or Flink would handle the aggregation.

## 6. Production Improvements

1. **Incremental processing** Record the last processed timestamp per device in a `pipeline_runs` table. Each run only reads new files and uses upserts instead of truncating the tables.
2. **Pipeline monitoring** Track stage execution time and row counts (raw, cleaned, rejected, aggregated) to detect throughput issues and data volume changes.
3. **Alerting** Notify via Slack when the rejection rate exceeds a defined threshold, indicating a possible sensor fault or source format change.
4. **Secret management** Store database credentials in AWS Secrets Manager or HashiCorp Vault instead of environment variables to prevent exposure in logs or container configurations.
5. **CI/CD** Run tests against a test database on every commit. Deploy through a staging environment before production using a container image.
6. **Data quality gates** Define thresholds for null rate, minimum row count per device per day, and maximum timestamp age. If any threshold is breached during profiling, halt the pipeline before loading into the dashboard tables.
7. **OLTP/OLAP split** PostgreSQL handles the current dashboard workload well as the queries are filtered lookups by location and date (OLTP). At larger scale, analytical queries such as year-long trend analysis across all locations (OLAP) would benefit from a column-oriented database like ClickHouse or TimescaleDB. The pipeline would load into both: PostgreSQL for the dashboard and the OLAP database for analytics.
