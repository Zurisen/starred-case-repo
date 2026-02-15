"""
Entry point for running analytics on survey feedback data.
"""
import pandas as pd
import matplotlib.pyplot as plt
from src.analytics import (
    avg_rating_per_department,
    avg_rating_per_region,
    rating_distribution_per_department
)


def plot_avg_rating_bar(df: pd.DataFrame, group_col: str, output_path: str, title: str):
    """Create a bar chart for average ratings."""
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(df[group_col], df['avg_rating'], color='steelblue', edgecolor='black')
    ax.set_xlabel(group_col.replace('_', ' ').title())
    ax.set_ylabel('Average Rating')
    ax.set_title(title)
    ax.set_ylim(0, 5)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def plot_rating_distribution_stacked(df: pd.DataFrame, output_path: str):
    """Create a stacked bar chart for rating distribution per department."""
    pivot = df.pivot(index='department', columns='rating', values='rating_count').fillna(0)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    pivot.plot(kind='bar', stacked=True, ax=ax, colormap='RdYlGn', edgecolor='black')
    ax.set_xlabel('Department')
    ax.set_ylabel('Count')
    ax.set_title('Rating Distribution per Department')
    ax.legend(title='Rating', bbox_to_anchor=(1.02, 1), loc='upper left')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


if __name__ == '__main__':

    ## INFO
    # We could build a joined pipeline with sanitization+analytics, whithout the need to reload the previously 
    # saved dataframe. But we decided to split them since leaving these two steps of the pipeline separated
    # makes more sense from an hypothetical cloud-deployable service perspective.
    df_fact = pd.read_csv('data/fct_survey_feedback.csv')
    
    # Only include users with valid emails
    df_fact = df_fact[df_fact['email_valid'] == True]
    
    ## INFO
    # For this exercise we will fully use pandas for analytics, since it is a small dataset. In production pipelines
    # pandas memory limits makes it unfeasible to use for large datasets. Instead we would use distributed computing
    # pipelines such as Spark.
    print("=== Average Rating per Department ===")
    df_dept = avg_rating_per_department(df_fact)
    print(df_dept)
    df_dept.to_csv('aggregations/avg_rating_per_department.csv', index=False)
    print()
    
    print("=== Average Rating per Region ===")
    df_region = avg_rating_per_region(df_fact)
    print(df_region)
    df_region.to_csv('aggregations/avg_rating_per_region.csv', index=False)
    print()
    
    print("=== Rating Distribution per Department ===")
    df_dist = rating_distribution_per_department(df_fact)
    print(df_dist)
    df_dist.to_csv('aggregations/rating_distribution_per_department.csv', index=False)
    
    print("\nSaved aggregations to aggregations/ folder.")
    
    # Generate charts
    print("\nGenerating charts...")
    plot_avg_rating_bar(df_dept, 'department', 'aggregations/avg_rating_per_department.png', 'Average Rating per Department')
    plot_avg_rating_bar(df_region, 'region', 'aggregations/avg_rating_per_region.png', 'Average Rating per Region')
    plot_rating_distribution_stacked(df_dist, 'aggregations/rating_distribution_per_department.png')
    print("Saved charts to aggregations/ folder.")
