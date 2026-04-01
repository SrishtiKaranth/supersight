# People Counting Data Pipeline

This project implements a data pipeline for processing people movement events collected by sensors installed at different locations. Each sensor records the number of people entering and exiting over time. The pipeline processes these raw events into aggregated datasets suitable for analytics and visualization, and a Django-based web application is included to demonstrate how the output integrates with a frontend.

## Architecture Overview

```
CSV files → PySpark Pipeline → PostgreSQL ← Django Web Application
```

- **Pipeline**: Built with PySpark. Reads raw CSV data from each device, performs data profiling and cleansing, computes hourly and daily aggregations, and loads the results into PostgreSQL.
- **PostgreSQL**: Serves as the central data store for aggregated output. Runs as a Docker container.
- **Web Application**: Built with Django. Queries PostgreSQL and renders a dashboard displaying per-device hourly breakdowns alongside visual summaries.

## Project Structure

```
supersight/
├── run.sh                          # Setup and run everything
├── docker-compose.yml              # PostgreSQL container definition
├── pipeline/
│   ├── data/input/                 # Raw CSV files organised by device
│   │   ├── device_A/
│   │   └── device_B/
│   ├── sql/
│   │   └── create_tables.sql       # Table definitions (DDL)
│   ├── src/
│   │   ├── config/                 # Application settings and logging configuration
│   │   ├── db_connection/          # PostgreSQL connection management
│   │   ├── extract/                # Data extraction from CSV sources
│   │   ├── transform/              # Hourly and daily aggregation logic
│   │   ├── load/                   # Batch loading into PostgreSQL
│   │   ├── quality/                # Data profiling, cleansing, and schema validation
│   │   └── main.py                 # Pipeline entry point and orchestration
│   └── requirements.txt
└── web-application/
    ├── api/                        # Django application
    ├── webapplicationsetup/        # Django project configuration
    ├── manage.py
    └── requirements.txt
```

## Prerequisites

- Python 3.9 or higher
- Java 11 or higher (required by PySpark)
- Docker (for running PostgreSQL)

## Setup and Execution

```bash
./run.sh
```

This single script starts PostgreSQL, sets up virtual environments, installs dependencies, runs the pipeline, and starts the web application.

The pipeline executes the following stages in order:

1. Verifies database connectivity
2. Creates tables and validates the schema against expected definitions
3. Extracts raw events from all device CSV files
4. Profiles the input data (null counts, value ranges, duplicate detection)
5. Cleanses the data (fills missing values)
6. Computes hourly and daily aggregations
7. Loads the results into PostgreSQL using batch inserts

The dashboard is accessible at **http://localhost:8000/**. It presents both devices side by side, each with an hourly data table and a chart showing the distribution of entries and exits.

## Output Schema

**hourly_aggregations**: One record per device per hour.

| Column    | Type      | Description                                        |
|-----------|-----------|----------------------------------------------------|
| id        | SERIAL PK | Auto-incrementing primary key                      |
| location  | TEXT      | Device identifier (for example, device_A)          |
| hour      | TIMESTAMP | Start of the hour window                           |
| date      | DATE      | Calendar date                                      |
| total_in  | INTEGER   | Number of people entering during this hour         |
| total_out | INTEGER   | Number of people exiting during this hour          |
| net_flow  | INTEGER   | Difference between entries and exits               |
| occupancy | INTEGER   | Cumulative net flow for the day, starting from zero|

**daily_aggregations**: One record per device per day.

| Column    | Type      | Description                                        |
|-----------|-----------|----------------------------------------------------|
| id        | SERIAL PK | Auto-incrementing primary key                      |
| location  | TEXT      | Device identifier                                  |
| date      | DATE      | Calendar date                                      |
| total_in  | INTEGER   | Total entries for the day                          |
| total_out | INTEGER   | Total exits for the day                            |
| net_flow  | INTEGER   | Difference between total entries and exits         |

Both tables include composite indexes on `(location, date)` to support the query patterns used by the web application.

## References

The following resources informed the design and structure of this project:

- [Structuring an ETL Pipeline Project: Best Practices](https://medium.com/@aliakbarhosseinzadeh/structuring-an-etl-pipeline-project-best-practices-5ed1e4d5a601):The pipeline directory structure follows the conventions outlined in this article, including the separation of extract, transform, load, and quality modules, along with dedicated configuration and logging packages.
- [The 6 Building Blocks of ETL Architecture](https://www.integrate.io/blog/etl-architecture-building-blocks/):The pipeline design is informed by the building blocks described in this article: extraction, profiling, cleansing, transformation, and loading.
