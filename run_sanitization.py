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
    # Report unmatched survey responses (emails not found in user metadata). We could optionally create a new user
    # metadata entry for missed metadata. Or drop the surveys from the survey results table that have no assigned user.
    unmatched = df_joined['full_name'].isna().sum()
    if unmatched > 0:
        print(f"Warning: {unmatched} survey response(s) have no matching user metadata.")
    
    # Select final columns and save fact table
    output_cols = ['submission_id', 'timestamp', 'user_email', 'rating', 'comment_text', 'region', 'department', 'country']
    df_fact = df_joined[output_cols]
    df_fact.to_csv('data/fct_survey_feedback.csv', index=False)
    print(f"\nSaved fct_survey_feedback.csv with {len(df_fact)} records.")
    
    print("\nData processing complete!")

