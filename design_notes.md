# Design Notes

## Overview

This document describes the data ingestion, cleaning, sanitization, and join operations performed in this project using Python Pandas. The pipeline processes survey feedback data and user metadata to produce a consolidated fact table to then be used to perform analytics.

## Data Processing Pipeline

The `run_sanitization.py` scripts loads, cleans, joins, and saves data.

### 1. Data Ingestion

- Load `survey_results.csv` and `user_metadata.csv` using pandas
- No sampling applied in production (full dataset loaded)

### 2. Survey Data Sanitization (`sanitize_survey_data`)

- Convert `timestamp` to datetime (invalid values become NaT)
- Strip whitespace from string columns
- Normalize `user_email` to lowercase
- Validate email format (adds `email_valid` boolean column)
- Drop rows with missing `rating` values
- Clip `rating` values to range [1, 5]
- Drop duplicate `submission_id` entries (keep last occurrence)
- Reset index

### 3. User Data Sanitization (`sanitize_user_data`)

- Strip whitespace from string columns
- Normalize `user_email` to lowercase
- Drop duplicate `user_email` entries (first occurrence kept)
- Validate email format (adds `email_valid` boolean column)
- Fill missing `country` values with "Not specified"
- Reset index

### 4. Data Join

- One-to-many left join on `user_email`
- Survey data enriched with user metadata (department, country from user table)
- Unmatched survey responses (no corresponding user) are preserved but flagged

### 5. Output Generation

- Select final columns and export to `fct_survey_feedback.csv`
- This table is ready for BI/Analytics, denormalized, each row representing a single survey submission and identified by an unique identifier.

| Column        | Description                                         |
| ------------- | --------------------------------------------------- |
| submission_id | Unique identifier (for counting distinct responses) |
| timestamp     | Time dimension (for trend analysis)                 |
| user_email    | User dimension (for user-level analysis)            |
| rating        | Primary metric (quantitative measure)               |
| comment_text  | Qualitative data (for text analytics)               |
| region        | Geographic dimension (for regional analysis)        |
| department    | Organizational dimension (for department analysis)  |
| country       | Geographic dimension (granular location analysis)   |
| email_valid   | Sanitization field (to prevent fraudulent surveys)  |

---

## Analytics Pipeline

The `run_analytics.py` script performs aggregations on the processed fact table (only on valid users).

### Aggregation Functions

| Function                                 | Output Columns            | Description                               |
| ---------------------------------------- | ------------------------- | ----------------------------------------- |
| `avg_rating_per_department(df)`          | department, avg_rating    | Average rating grouped by department      |
| `avg_rating_per_region(df)`              | region, avg_rating        | Average rating grouped by region          |
| `rating_distribution_per_department(df)` | department, rating, count | Count of each rating (1-5) per department |

### Chart Generation

| Chart Type        | Output File                                           | Description                              |
| ----------------- | ----------------------------------------------------- | ---------------------------------------- |
| Bar Chart         | `aggregations/avg_rating_per_department.png`          | Average rating by department             |
| Bar Chart         | `aggregations/avg_rating_per_region.png`              | Average rating by region                 |
| Stacked Bar Chart | `aggregations/rating_distribution_per_department.png` | Rating distribution (1-5) per department |

---

## Code Comments & Assumptions

### Timestamp Handling

> **Location:** [src/data_sanitization.py](src/data_sanitization.py#L82-84)

Convert timestamp to datetime, coercing errors to NaT (Not a Time). We assume survey data is still valid even if there is no timestamp.

### String Field Standardization

> **Location:** [src/data_sanitization.py](src/data_sanitization.py#L90-L92)

Strip whitespace from string columns. We could also further standardize some fields like `region` or `department` by having shared DTOs with the APIs to have an enumeration check, instead of plain strings.

### Rating Field Validation

> **Location:** [src/data_sanitization.py](src/data_sanitization.py#L104-L106)

Drop rows with missing `rating` values because we assume it is a necessary field for analytics. If the rating displays a value beyond the allowed range, we clip it to fit [1, 5].

### Duplicate Submission IDs

> **Location:** [src/data_sanitization.py](src/data_sanitization.py#L112-L115)

Fix duplicate `submission_id` entries by dropping the first occurrence. Submission IDs should be unique. In the exploratory analysis we saw that the duplicates were carrying the same data. Thus this might be caused by a mistaken rewrite from the API side, and not actually a different submission GUID conflict (architecture consideration for future).

### Email Validation

> **Location:** [src/data_sanitization.py](src/data_sanitization.py#L152-L156)

Validate emails via regex pattern. We create a new column to store whether the email formats are valid or not (might have been caused by an API write error). We assume there was frontend/backend email validation beforehand that then possibly led to a wrong write in the database. Thus the survey entry/user metadata might still be valid, and we don't want to drop it beforehand.

### User Email Uniqueness

> **Location:** [src/data_sanitization.py](src/data_sanitization.py#L38-L41)

Ensure user uniqueness by dropping duplicate emails (keeping last occurrence). It would be nice to have a `createdAt` field to check when the entry was added to choose which to keep.

### One-to-Many Join Strategy

> **Location:** [run_sanitization.py](run_sanitization.py#L29-L35)

Join survey data with user metadata using a one-to-many relationship: we are assuming one user can have multiple survey responses. We could specify a time cooldown or extra conditions for submitting new survey results in the survey API.

### Unmatched Survey Responses

> **Location:** [run_sanitization.py](run_sanitization.py#L43-L45)

Report unmatched survey responses (names not found in user metadata). We could optionally create a new user metadata entry for missed metadata, or drop the surveys from the survey results table that have no assigned user.

### Join and Sanitization Pipeline Structure

> **Location:** [run_sanitization.py](run_sanitization.py#L65-L66)

We performed the join operation in the same file as the sanitization was performed. We could split this operation in two different steps: data sanitization → save of sanitized dataframes → import sanitized dataframes and join → save joined dataframes.

### Pipeline Separation

> **Location:** [run_analytics.py](run_analytics.py#L45-L48)

We could build a joined pipeline with sanitization+analytics, without the need to reload the previously saved dataframe. But we decided to split them since leaving these two steps of the pipeline separated makes more sense from a hypothetical cloud-deployable service perspective.

### Pandas for Analytics

> **Location:** [run_analytics.py](run_analytics.py#L54-L57)

For this exercise we fully use pandas for analytics, since it is a small dataset. In production pipelines, pandas memory limits makes it unfeasible to use for large datasets. Instead we would use distributed computing pipelines such as Spark.

---

## File Structure

```
├── run_sanitization.py          # Sanitization pipeline - loads, cleans, joins, and saves data
├── run_analytics.py             # Analytics pipeline - runs aggregations and generates charts
├── src/
│   ├── __init__.py
│   ├── data_sanitization.py     # Sanitization functions
│   └── analytics.py             # Analytics aggregation functions
├── data/
│   ├── survey_results.csv       # Input: raw survey data
│   ├── user_metadata.csv        # Input: raw user metadata
│   └── fct_survey_feedback.csv  # Output: processed fact table
├── aggregations/
│   ├── avg_rating_per_department.csv   # Output: avg rating by department
│   ├── avg_rating_per_department.png   # Chart: bar chart
│   ├── avg_rating_per_region.csv       # Output: avg rating by region
│   ├── avg_rating_per_region.png       # Chart: bar chart
│   ├── rating_distribution_per_department.csv  # Output: rating counts
│   └── rating_distribution_per_department.png  # Chart: stacked bar
├── notebooks/
│   └── data_exploration.ipynb   # Exploratory analysis
├── bonus/
```

## Future Considerations & Improvements

- For the exercise we have imported the whole (Pandas) dataset into memory. This is an unfeasible approach for large datasets. Instead we could implement batch read functionalities to have a predictible memory load.
- We have used csv as a data format. That is fine for this exercise, but we could consider large datasets columnar storages as well (e.g: parquet), for efficient batching processing. This could also allow for saving of dataframe metadata that could be useful for the analytics afterwards.
- Add extra sanitizing conditions for some of the fields. We assumed user names were just a single field (not separated in Name and Surname). Regions and Countries ,could also be further sanitized to make sure they belong to an existing class, preventing possible typos or unhandled cases. Timestamp could be splitted into granular date columns (year, quarter, month...) and emails could be anonymized for extra user security.
- Analytics have been performed fully using Pandas, for larger datasets, we could implement distributed computing strategies with tools like PySpark.
- This samples processing worked seamlessly with Python, but for production processing, we should consider schema validation using tools like Pydantic, or use other frameworks that enforce schema validation like C# .NET.

## Bonus Folder

The `bonus/` folder contains the optional assignment related to the Real-Time Architecture Design.
