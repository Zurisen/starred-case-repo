"""
Analytics utility functions for performing aggregations on survey feedback data.
"""
import pandas as pd


def avg_rating_per_department(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate the average rating per department.
    
    Args:
        df: DataFrame containing 'department' and 'rating' columns.
        
    Returns:
        DataFrame with columns: department, avg_rating
    """
    result = (
        df.groupby('department', as_index=False)['rating']
        .mean()
        .rename(columns={'rating': 'avg_rating'})
        .round({'avg_rating': 2})
    )
    return result


def avg_rating_per_region(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate the average rating per region.
    
    Args:
        df: DataFrame containing 'region' and 'rating' columns.
        
    Returns:
        DataFrame with columns: region, avg_rating
    """
    result = (
        df.groupby('region', as_index=False)['rating']
        .mean()
        .rename(columns={'rating': 'avg_rating'})
        .round({'avg_rating': 2})
    )
    return result


def rating_distribution_per_department(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate the distribution of ratings (1-5) per department.
    
    Args:
        df: DataFrame containing 'department' and 'rating' columns.
        
    Returns:
        DataFrame with columns: department, rating, rating_count
    """
    result = (
        df.groupby(['department', 'rating'], as_index=False)
        .size()
        .rename(columns={'size': 'rating_count'})
    )
    return result
