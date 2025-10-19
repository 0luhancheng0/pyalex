"""
Advanced Filtering Examples

This script demonstrates advanced PyAlex filtering:
- Logical operators (AND, OR, NOT)
- Range filters
- Complex combinations
"""

from pyalex import Works


def example_1_or_filter():
    """Use OR logic to combine multiple values."""
    print("=" * 60)
    print("Example 1: OR Filter - Multiple Keywords")
    print("=" * 60)

    # Search for works about either "deep learning" OR "neural networks"
    results = (
        Works()
        .filter_or(display_name_search=["deep learning", "neural networks"])
        .get(limit=5)
    )

    print(f"Found {len(results)} works:")
    for work in results:
        print(f"  - {work['title'][:80]}...")
        print()


def example_2_range_filter():
    """Filter by numeric ranges."""
    print("=" * 60)
    print("Example 2: Range Filter - Citation Count")
    print("=" * 60)

    # Get highly cited works (more than 100 citations)
    results = (
        Works().filter_gt(cited_by_count=100).filter(publication_year=2020).get(limit=5)
    )

    print(f"Found {len(results)} highly cited works from 2020:")
    for work in results:
        print(f"  - {work['title'][:80]}...")
        print(f"    Citations: {work.get('cited_by_count', 0)}")
        print()


def example_3_not_filter():
    """Exclude certain values."""
    print("=" * 60)
    print("Example 3: NOT Filter - Exclude Types")
    print("=" * 60)

    # Search for works but exclude certain types
    results = (
        Works()
        .search("artificial intelligence")
        .filter_not(
            type="paratext"  # Exclude paratexts
        )
        .get(limit=5)
    )

    print(f"Found {len(results)} works (excluding paratexts):")
    for work in results:
        print(f"  - {work['title'][:80]}...")
        print(f"    Type: {work.get('type', 'N/A')}")
        print()


def example_4_complex_filter():
    """Combine multiple filters."""
    print("=" * 60)
    print("Example 4: Complex Filter Combination")
    print("=" * 60)

    # Complex query: AI papers from 2022-2023 with >10 citations
    results = (
        Works()
        .search("artificial intelligence")
        .filter(publication_year=[2022, 2023])
        .filter_gt(cited_by_count=10)
        .filter(type="article")
        .get(limit=5)
    )

    print(f"Found {len(results)} AI articles (2022-2023, >10 citations):")
    for work in results:
        print(f"  - {work['title'][:80]}...")
        print(
            f"    Year: {work.get('publication_year')}, "
            f"Citations: {work.get('cited_by_count', 0)}"
        )
        print()


def example_5_author_filter():
    """Filter works by author."""
    print("=" * 60)
    print("Example 5: Filter by Author")
    print("=" * 60)

    # Get works by a specific author (using author ID)
    # Note: Replace with actual author OpenAlex ID
    author_id = "https://openalex.org/A5023888391"  # Example ID

    try:
        results = Works().filter(author={"id": author_id}).get(limit=5)

        print(f"Found {len(results)} works by this author:")
        for work in results:
            print(f"  - {work['title'][:80]}...")
            print(f"    Year: {work.get('publication_year', 'N/A')}")
            print()
    except Exception as e:
        print(f"Error: {e}")
        print("(Replace with a valid author OpenAlex ID)")


def example_6_date_range():
    """Filter by date range."""
    print("=" * 60)
    print("Example 6: Date Range Filter")
    print("=" * 60)

    # Get works from last 2 years
    results = (
        Works()
        .search("machine learning")
        .filter_gt(publication_year=2021)
        .filter_lt(publication_year=2024)
        .get(limit=5)
    )

    print(f"Found {len(results)} ML works (2022-2023):")
    for work in results:
        print(f"  - {work['title'][:80]}...")
        print(f"    Year: {work.get('publication_year')}")
        print()


def main():
    """Run all examples."""
    print("\n🎯 PyAlex Advanced Filtering Examples\n")

    try:
        example_1_or_filter()
        example_2_range_filter()
        example_3_not_filter()
        example_4_complex_filter()
        example_5_author_filter()
        example_6_date_range()

        print("\n✅ All examples completed!")
        print("\nKey takeaways:")
        print("  - Use filter_or() for OR logic")
        print("  - Use filter_gt() and filter_lt() for ranges")
        print("  - Use filter_not() to exclude values")
        print("  - Chain filters for complex queries")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure PyAlex is properly configured.")


if __name__ == "__main__":
    main()
