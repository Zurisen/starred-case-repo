"""
Main entry point for data processing pipeline.
"""
import pandas as pd
from src.data_sanitization import (
    sanitize_survey_data,
    sanitize_user_data,
    validate_data,
    print_validation_report
)
from models.defaults import DEPARTMENT_DEFAULT, COUNTRY_DEFAULT


if __name__ == '__main__':
    """Load, sanitize, and validate the datasets."""
    print("Loading datasets...")
    df_survey = pd.read_csv('data/survey_results.csv')
    df_user = pd.read_csv('data/user_metadata.csv')
    print(f"Loaded {len(df_survey)} survey records and {len(df_user)} user records.")
    
    print("\nSanitizing survey data...")
    df_survey = sanitize_survey_data(df_survey)
    
    print("\nSanitizing user data...")
    df_user = sanitize_user_data(df_user)
    
    print("\nValidating data...")
    results = validate_data(df_survey, df_user)
    print_validation_report(results)
    
    ## INFO
    # Join survey data with user metadata one-to-many: we are assuming one user can have multiple survey responses.
    # We could specify a time cooldown or extra conditions for submitting new survey results in the survey API.
    print("\nJoining survey data with user metadata...")
    df_joined = pd.merge(
        df_survey,
        df_user,
        on='user_email',
        how='left',
        suffixes=('_survey', '_user')
    )
    print(f"Joined dataset: {len(df_joined)} records")
    
    ## INFO
    # Report unmatched survey responses (names not found in user metadata). We could optionally create a new user
    # metadata entry for missed metadata. Or drop the surveys from the survey results table that have no assigned user.
    unmatched_mask = df_joined['full_name'].isna()
    unmatched = unmatched_mask.sum()
    if unmatched > 0:
        print(f"Warning: {unmatched} survey response(s) have no matching user metadata.")
        print("Rows with unmatched user metadata:")
        print(df_joined[unmatched_mask])
    
    # Apply default values to unmatched rows
    df_joined.loc[unmatched_mask, 'department'] = DEPARTMENT_DEFAULT
    df_joined.loc[unmatched_mask, 'country'] = COUNTRY_DEFAULT
    
    # Combine email_valid columns from both sources (and logic: if None is True, result is False)
    email_valid_survey = df_joined['email_valid_survey'].fillna(False)
    email_valid_user = df_joined['email_valid_user'].fillna(False)
    # Ensure correct types to avoid future downcasting warning
    email_valid_survey = email_valid_survey.infer_objects(copy=False)
    email_valid_user = email_valid_user.infer_objects(copy=False)
    df_joined['email_valid'] = email_valid_survey & email_valid_user
    
    # Select final columns and save fact table
    output_cols = ['submission_id', 'timestamp', 'user_email', 'rating', 'comment_text', 'region', 'department', 'country', 'email_valid']
    df_fact = df_joined[output_cols]

    ## INFO
    # We performed the join operation in the same file than the sanitization was performed. We could split this operation in two different
    # operations: data sanitiazion --> save of sanitized dataframes --> import sanitized dataframes and join --> save joined dataframes.
    df_fact.to_csv('data/fct_survey_feedback.csv', index=False)
    print(f"\nSaved fct_survey_feedback.csv with {len(df_fact)} records.")
    
    print("\nData processing complete!")

