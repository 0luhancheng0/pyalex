"""
DataFrame Output Feature - PyAlex always returns pandas DataFrames!

This example demonstrates how PyAlex automatically returns pandas DataFrames
instead of lists of dictionaries, making data analysis much easier.
"""

import asyncio

from pyalex import Authors
from pyalex import Works


async def example_basic_dataframe():
    """Basic example showing DataFrame output."""
    print("=" * 80)
    print("Example 1: Basic DataFrame Output")
    print("=" * 80)

    # Fetch works - automatically returns a DataFrame
    works = await Works().filter_by_institution("I97018004").get(per_page=10)

    print(f"\nResult type: {type(works).__name__}")
    print(f"Shape: {works.shape}")
    print(f"Columns: {list(works.columns[:8])}...")

    # Access metadata
    print(f"\nMetadata: {works.attrs.get('meta', {})}")

    # DataFrame operations work as expected
    print("\nMost cited works:")
    top_works = works.nlargest(5, "cited_by_count")[
        ["title", "publication_year", "cited_by_count"]
    ]
    print(top_works.to_string(index=False))

    return works


async def example_data_analysis():
    """Example showing data analysis with DataFrames."""
    print("\n" + "=" * 80)
    print("Example 2: Data Analysis with DataFrames")
    print("=" * 80)

    # Get works from multiple years
    works = await (
        Works()
        .filter_by_institution("I97018004")
        .filter_by_publication_year(start_year=2020, end_year=2023)
        .search("machine learning")
        .get(per_page=50)
    )

    print(f"\nRetrieved {len(works)} works")

    # Group by year and count
    print("\nWorks per year:")
    year_counts = works.groupby("publication_year").size()
    print(year_counts)

    # Calculate average citations per year
    print("\nAverage citations per year:")
    avg_citations = works.groupby("publication_year")["cited_by_count"].mean()
    print(avg_citations.round(1))

    # Filter for highly cited works
    print("\nHighly cited works (>100 citations):")
    highly_cited = works[works["cited_by_count"] > 100]
    print(f"Found {len(highly_cited)} highly cited works")
    print(
        highly_cited[["title", "publication_year", "cited_by_count"]]
        .head()
        .to_string(index=False)
    )


async def example_dataframe_methods():
    """Example showing pandas DataFrame methods."""
    print("\n" + "=" * 80)
    print("Example 3: Using DataFrame Methods")
    print("=" * 80)

    # Get authors
    authors = await Authors().filter_by_affiliation("I97018004").get(per_page=20)

    print(f"\nRetrieved {len(authors)} authors")

    # Sort by works count
    print("\nTop 5 authors by works count:")
    top_authors = authors.nlargest(5, "works_count")[
        ["display_name", "works_count", "cited_by_count"]
    ]
    print(top_authors.to_string(index=False))

    # Statistical summary
    print("\nStatistical summary of works_count:")
    print(authors["works_count"].describe())

    # Filter and select
    print("\nProductive authors (>50 works):")
    productive = authors[authors["works_count"] > 50]
    print(f"Found {len(productive)} productive authors")


async def example_converting_to_list():
    """Example showing how to convert to list if needed."""
    print("\n" + "=" * 80)
    print("Example 4: Converting DataFrame to List")
    print("=" * 80)

    # Get works as DataFrame (always)
    works_df = await Works().search("quantum computing").get(per_page=5)

    print(f"DataFrame type: {type(works_df).__name__}")
    print(f"Shape: {works_df.shape}")

    # Convert to list of dicts if needed
    works_list = works_df.to_dict("records")
    print(f"\nConverted to list type: {type(works_list).__name__}")
    print(f"Length: {len(works_list)}")
    print(f"First item type: {type(works_list[0]).__name__}")

    # Access metadata
    print(f"\nMetadata stored in df.attrs: {works_df.attrs.get('meta', {})}")


async def example_jupyter_notebook():
    """Example showing Jupyter notebook integration."""
    print("\n" + "=" * 80)
    print("Example 5: Jupyter Notebook Integration")
    print("=" * 80)

    print("""
In Jupyter notebooks, DataFrames display beautifully:

```python
from pyalex import Works

# Results are automatically displayed as a formatted table
works = await Works().filter_by_institution('I97018004').get()
works  # This will show a nice HTML table in Jupyter!

# Use pandas operations
works[['title', 'publication_year', 'cited_by_count']].head(10)

# Export to CSV, Excel, etc.
works.to_csv('stanford_works.csv', index=False)
works.to_excel('stanford_works.xlsx', index=False)

# Plot directly
works.groupby('publication_year').size().plot(kind='bar')
```
""")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print(" PyAlex DataFrame Output Feature")
    print(" Making Data Analysis Easier!")
    print("=" * 80)

    print("\nPyAlex always returns pandas DataFrames for query results!")

    # Run examples
    asyncio.run(example_basic_dataframe())
    asyncio.run(example_data_analysis())
    asyncio.run(example_dataframe_methods())
    asyncio.run(example_converting_to_list())
    asyncio.run(example_jupyter_notebook())

    print("\n" + "=" * 80)
    print(" Summary")
    print("=" * 80)
    print("""
✅ PyAlex always returns pandas DataFrames
✅ All pandas methods work seamlessly (groupby, filter, sort, etc.)
✅ Metadata is preserved in df.attrs['meta'] attribute
✅ Perfect for data analysis and visualization
✅ Easy to export to CSV, Excel, JSON, etc.
✅ Beautiful display in Jupyter notebooks
✅ Convert to list with df.to_dict('records') if needed

Benefits:
- No more pd.DataFrame(results) conversion needed!
- Direct access to powerful pandas functionality
- Cleaner, more readable code
- Better performance for data operations
""")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
