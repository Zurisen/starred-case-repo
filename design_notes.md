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
- Drop duplicate `submission_id` entries (first occurrence dropped)
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

---

## Analytics Pipeline

The `run_analytics.py` script performs aggregations on the processed fact table.

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

> **Location:** [src/data_sanitization.py](src/data_sanitization.py#L75-L78)

Convert timestamp to datetime, coercing errors to NaT (Not a Time). We assume survey data is still valid even if there is no timestamp.

### String Field Standardization

> **Location:** [src/data_sanitization.py](src/data_sanitization.py#L83-L86)

Strip whitespace from string columns. We could also further standardize some fields like `region` or `department` by having shared DTOs with the APIs to have an enumeration check, instead of plain strings.

### Rating Field Validation

> **Location:** [src/data_sanitization.py](src/data_sanitization.py#L97-L100)

Drop rows with missing `rating` values because we assume it is a necessary field for analytics. If the rating displays a value beyond the allowed range, we clip it to fit [1, 5].

### Duplicate Submission IDs

> **Location:** [src/data_sanitization.py](src/data_sanitization.py#L105-L108)

Fix duplicate `submission_id` entries by dropping the first occurrence. Submission IDs should be unique. In the exploratory analysis we saw that the duplicates were carrying the same data. Thus this is caused by a mistaken rewrite from the API side, and not actually a different submission GUID conflict (architecture consideration for future).

### Email Validation

> **Location:** [src/data_sanitization.py](src/data_sanitization.py#L144-L148)

Validate emails via regex pattern. We create a new column to store whether the email formats are valid or not (might have been caused by an API write error). We assume there was frontend/backend email validation beforehand that then possibly led to a wrong write in the database. Thus the survey entry/user metadata might still be valid, and we don't want to drop it beforehand.

### User Email Uniqueness

> **Location:** [src/data_sanitization.py](src/data_sanitization.py#L38-L41)

Ensure user uniqueness by dropping duplicate emails (keeping first occurrence). It would be nice to have a timestamp field to check which entry was added first/last to choose which to keep.

### One-to-Many Join Strategy

> **Location:** [run_sanitization.py](run_sanitization.py#L30-L32)

Join survey data with user metadata using a one-to-many relationship: we are assuming one user can have multiple survey responses. We could specify a time cooldown or extra conditions for submitting new survey results in the survey API.

### Unmatched Survey Responses

> **Location:** [run_sanitization.py](run_sanitization.py#L43-L45)

Report unmatched survey responses (emails not found in user metadata). We could optionally create a new user metadata entry for missed metadata, or drop the surveys from the survey results table that have no assigned user.

### Pipeline Separation

> **Location:** [run_analytics.py](run_analytics.py#L43-L46)

We could build a joined pipeline with sanitization+analytics, without the need to reload the previously saved dataframe. But we decided to split them since leaving these two steps of the pipeline separated makes more sense from a hypothetical cloud-deployable service perspective.

### Pandas for Analytics

> **Location:** [run_analytics.py](run_analytics.py#L48-L51)

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
- We have used csv as a data format. That is fine for this exercise, but we could consider large datasets columnar storages as well (e.g: parquet), for efficient batching processing.
- Add extra sanitizing conditions for some of the fields. We assumed user names were just a single field (not separated in Name and Surname). Regions and Countries ,could also be further sanitized to make sure they belong to an existing class, preventing possible typos or unhandled cases.
- Analytics have been performed fully using Pandas, for larger datasets, we could implement distributed computing strategies with tools like PySpark.

## Bonus Folder

The `bonus/` folder contains the optional assignment related to the Real-Time Architecture Design.
