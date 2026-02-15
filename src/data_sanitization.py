"""
Data sanitization module.
"""
import re
import pandas as pd
from models.defaults import DEPARTMENT_DEFAULT, COUNTRY_DEFAULT, REGION_DEFAULT

# Simple email regex pattern
_EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


def sanitize_user_data(df: pd.DataFrame, copy: bool = True) -> pd.DataFrame:
    """
    Sanitize user metadata dataframe.
    
    - Strip whitespace from string columns
    - Normalize email to lowercase
    - Drop duplicate user_email entries (keep last occurrence)
    - Validate email format
    
    Args:
        df: Raw user metadata dataframe
        copy: If True, work on a copy to avoid side effects. If False, modify in place.
        
    Returns:
        Sanitized dataframe
    """
    if copy:
        df = df.copy()
    
    # Strip whitespace from string columns
    string_cols = ['user_email', 'full_name', 'department', 'country']
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].str.strip()
    
    # Normalize email to lowercase
    df['user_email'] = df['user_email'].str.lower()
    
    # Ensure user uniqueness by dropping duplicate emails (keep last occurrence).
    dupe_count = df['user_email'].duplicated().sum()
    if dupe_count > 0:
        # Check if duplicates have different data
        dupe_emails = df[df['user_email'].duplicated(keep=False)]['user_email'].unique()
        for email in dupe_emails:
            rows = df[df['user_email'] == email]
            if not rows.drop('user_email', axis=1).nunique().eq(1).all():
                print(f"WARNING: Duplicate user_email '{email}' has differing data:")
                print(rows)
        print(f"Dropping {dupe_count} duplicate user_email(s), keeping last occurrence.")
        df = df.drop_duplicates(subset='user_email', keep='last')
    
    # Validate emails
    df = validate_emails(df, 'user_email')
    
    # Fill missing country values with "Not specified" instead of dropping them
    if 'country' in df.columns:
        df['country'] = df['country'].fillna(COUNTRY_DEFAULT)
    
    if 'department' in df.columns:
        df['department'] = df['department'].fillna(DEPARTMENT_DEFAULT)
        
    # Reset index after sanitization
    df = df.reset_index(drop=True)
    
    return df

def sanitize_survey_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sanitize survey results dataframe.
    
    - Convert timestamp to datetime (invalid values become NaT)
    - Strip whitespace from string columns
    - Normalize email to lowercase
    - Fix duplicate submission_ids by dropping last duplicated entry
    
    Args:
        df: Raw survey results dataframe
        
    Returns:
        Sanitized dataframe
    """
    df = df.copy()
    
    ## INFO
    # Convert timestamp to datetime, coerce errors to NaT (not a time)
    # since we assume survey data is still valid even if there is no timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    invalid_timestamps = df['timestamp'].isna().sum()
    if invalid_timestamps > 0:
        print(f"{invalid_timestamps} invalid timestamp(s) found and set to NaT.")
    
    ## INFO
    # Strip whitespace from string columns. We could also further standarize some fields like region or department
    # by having some shared DTO with the APIs to have an enumeration check, instead of plain strings.
    string_cols = ['submission_id', 'user_email', 'comment_text', 'region', 'country']
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].str.strip()

    # Normalize email to lowercase
    df['user_email'] = df['user_email'].str.lower()

    # Validate emails format
    df = validate_emails(df, 'user_email')

    ## INFO
    # Drop rows with missing rating values because we assume it is a necessary field for analytics.
    # If the rating displays a value beyond the allowed range, we clip it to fit.
    if 'rating' in df.columns:
        df = df.dropna(subset=['rating'])
        df['rating'] = df['rating'].clip(lower=1, upper=5)

    if 'region' in df.columns:
        df['region'] = df['region'].fillna(REGION_DEFAULT)


    ## INFO
    # Fix duplicate submission_ids by dropping them. Submission ids should be unique. In the exploratory analysis
    # we saw that the duplicates were carrying the same data. Thus this is caused by a mistaken rewrite from the API side, and
    # not actually a different submission GUID conflict (we'll comment more about this in the architecture designsection)
    df = _fix_duplicate_submission_ids(df)

    # Reset index after sanitization
    df = df.reset_index(drop=True)

    return df


def is_valid_email(email: str) -> bool:
    """
    Check if an email address is valid.
    
    Args:
        email: Email string to validate
        
    Returns:
        True if valid, False otherwise
    """
    if pd.isna(email) or not isinstance(email, str):
        return False
    return bool(_EMAIL_PATTERN.match(email.strip()))


def validate_emails(df: pd.DataFrame, email_col: str = 'user_email', copy: bool = True) -> pd.DataFrame:
    """
    Add a column indicating whether each email is valid.
    
    Args:
        df: DataFrame with email column
        email_col: Name of the email column
        copy: If True, work on a copy to avoid side effects. If False, modify in place.
    Returns:
        DataFrame with 'email_valid' column added
    """
    if copy:
        df = df.copy()
    ## INFO
    # Validate emails via regex pattern. We are going to create a new column to bool store whether
    # the email formats are valid or not (might have been caused by an API write error or something like that).
    # So we are assuming that there was an frontend/backend email validation beforehand that then possibly lead to
    # a wrong writing in the db. Thus the survey entry/user metadata might still be valid, and we dont want to drop it beforehand
    df['email_valid'] = df[email_col].apply(is_valid_email)
    invalid_count = (~df['email_valid']).sum()
    if invalid_count > 0:
        print(f"{invalid_count} invalid email(s) found.")
    return df



def _fix_duplicate_submission_ids(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove all but one occurrence of duplicate submission_ids, keeping the last occurrence.
    Also verify if duplicates have different data.
    """
    dupe_ids = df['submission_id'][df['submission_id'].duplicated(keep=False)].unique()
    for dupe_id in dupe_ids:
        rows = df[df['submission_id'] == dupe_id]
        if not rows.drop('submission_id', axis=1).nunique().eq(1).all():
            print(f"WARNING: Duplicate submission_id '{dupe_id}' has differing data:")
            print(rows)
    df = df.drop_duplicates(subset='submission_id', keep='last')
    return df




def validate_data(df_survey: pd.DataFrame, df_user: pd.DataFrame) -> dict:
    """
    Validate sanitized data and return validation results.
    
    Args:
        df_survey: Sanitized survey dataframe
        df_user: Sanitized user dataframe
        
    Returns:
        Dictionary with validation results
    """
    results = {
        'survey_missing_values': df_survey.isnull().sum().to_dict(),
        'user_missing_values': df_user.isnull().sum().to_dict(),
        'survey_duplicate_ids': df_survey['submission_id'].duplicated().sum(),
        'user_duplicate_emails': df_user['user_email'].duplicated().sum(),
        'survey_invalid_emails': (~df_survey['email_valid']).sum() if 'email_valid' in df_survey.columns else 0,
        'user_invalid_emails': (~df_user['email_valid']).sum() if 'email_valid' in df_user.columns else 0,
        'rating_range': (df_survey['rating'].min(), df_survey['rating'].max()),
        'unique_regions': df_survey['region'].unique().tolist(),
        'unique_departments': df_user['department'].unique().tolist(),
        'unique_countries': df_user['country'].unique().tolist(),
    }
    return results


def print_validation_report(results: dict) -> None:
    """Print a formatted validation report."""
    print("=" * 50)
    print("DATA VALIDATION REPORT")
    print("=" * 50)
    
    print("\n--- Missing Values (Survey) ---")
    for col, count in results['survey_missing_values'].items():
        if count > 0:
            print(f"  {col}: {count}")
    
    print("\n--- Missing Values (User) ---")
    for col, count in results['user_missing_values'].items():
        if count > 0:
            print(f"  {col}: {count}")
    
    print(f"\n--- Duplicate Check ---")
    print(f"  Survey duplicate IDs: {results['survey_duplicate_ids']}")
    print(f"  User duplicate emails: {results['user_duplicate_emails']}")
    
    print(f"\n--- Email Validation ---")
    print(f"  Survey invalid emails: {results['survey_invalid_emails']}")
    print(f"  User invalid emails: {results['user_invalid_emails']}")
    
    print(f"\n--- Value Ranges ---")
    print(f"  Rating range: {results['rating_range'][0]} - {results['rating_range'][1]}")
    print(f"  Unique regions: {results['unique_regions']}")
    print(f"  Unique departments: {results['unique_departments']}")
    print(f"  Unique countries: {results['unique_countries']}")
    
    print("=" * 50)
