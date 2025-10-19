"""
Demonstrate API and CLI parity - showing that both interfaces now support the same features.

This example shows how to use the new convenience methods in the API that mirror
CLI functionality, ensuring consistent feature availability across both interfaces.
"""

import asyncio

from pyalex import Authors
from pyalex import Funders
from pyalex import Institutions
from pyalex import Works


def example_works_filters():
    """Demonstrate Works convenience methods that match CLI options."""
    print("=" * 80)
    print("WORKS API - Convenience Methods (matches CLI functionality)")
    print("=" * 80)

    # Example 1: Filter by institution (matches --institution-ids in CLI)
    print("\n1. Filter works by institution:")
    print("   API:  Works().filter_by_institution('I97018004')")
    print("   CLI:  pyalex works --institution-ids 'I97018004'")
    works = Works().filter_by_institution("I97018004")
    print(f"   URL: {works.url}")

    # Example 2: Filter by author (matches --author-ids in CLI)
    print("\n2. Filter works by author:")
    print("   API:  Works().filter_by_author('A2208157607')")
    print("   CLI:  pyalex works --author-ids 'A2208157607'")
    works = Works().filter_by_author("A2208157607")
    print(f"   URL: {works.url}")

    # Example 3: Filter by publication year range (matches --year in CLI)
    print("\n3. Filter works by publication year range:")
    print("   API:  Works().filter_by_publication_year(start_year=2020, end_year=2021)")
    print("   CLI:  pyalex works --year '2020:2021'")
    works = Works().filter_by_publication_year(start_year=2020, end_year=2021)
    print(f"   URL: {works.url}")

    # Example 4: Filter by publication date range (matches --date in CLI)
    print("\n4. Filter works by publication date range:")
    print(
        "   API:  Works().filter_by_publication_date(start_date='2020-01-01', end_date='2020-12-31')"
    )
    print("   CLI:  pyalex works --date '2020-01-01:2020-12-31'")
    works = Works().filter_by_publication_date(
        start_date="2020-01-01", end_date="2020-12-31"
    )
    print(f"   URL: {works.url}")

    # Example 5: Filter by work type (matches --type in CLI)
    print("\n5. Filter works by type:")
    print("   API:  Works().filter_by_type('article')")
    print("   CLI:  pyalex works --type 'article'")
    works = Works().filter_by_type("article")
    print(f"   URL: {works.url}")

    # Example 6: Filter by topic (matches --topic-ids in CLI)
    print("\n6. Filter works by topic:")
    print("   API:  Works().filter_by_topic('T10002')")
    print("   CLI:  pyalex works --topic-ids 'T10002'")
    works = Works().filter_by_topic("T10002")
    print(f"   URL: {works.url}")

    # Example 7: Filter by funder (matches --funder-ids in CLI)
    print("\n7. Filter works by funder:")
    print("   API:  Works().filter_by_funder('F4320332161')")
    print("   CLI:  pyalex works --funder-ids 'F4320332161'")
    works = Works().filter_by_funder("F4320332161")
    print(f"   URL: {works.url}")

    # Example 8: Filter by citation count
    print("\n8. Filter works by citation count:")
    print("   API:  Works().filter_by_cited_by_count(min_count=100, max_count=1000)")
    works = Works().filter_by_cited_by_count(min_count=100, max_count=1000)
    print(f"   URL: {works.url}")

    # Example 9: Filter by open access
    print("\n9. Filter works by open access status:")
    print("   API:  Works().filter_by_open_access(oa_status='gold')")
    works = Works().filter_by_open_access(oa_status="gold")
    print(f"   URL: {works.url}")

    # Example 10: Chain multiple filters (complex query)
    print("\n10. Chain multiple filters for complex queries:")
    print("    API:  Works().filter_by_institution('I97018004')")
    print("              .filter_by_publication_year(start_year=2020, end_year=2023)")
    print("              .filter_by_type('article')")
    print("              .search('machine learning')")
    print("    CLI:  pyalex works --institution-ids 'I97018004' --year '2020:2023'")
    print("                       --type 'article' --search 'machine learning'")
    works = (
        Works()
        .filter_by_institution("I97018004")
        .filter_by_publication_year(start_year=2020, end_year=2023)
        .filter_by_type("article")
        .search("machine learning")
    )
    print(f"    URL: {works.url}")


def example_authors_filters():
    """Demonstrate Authors convenience methods."""
    print("\n" + "=" * 80)
    print("AUTHORS API - Convenience Methods")
    print("=" * 80)

    # Example 1: Filter by affiliation
    print("\n1. Filter authors by affiliation:")
    print("   API:  Authors().filter_by_affiliation('I97018004')")
    authors = Authors().filter_by_affiliation("I97018004")
    print(f"   URL: {authors.url}")

    # Example 2: Filter by works count
    print("\n2. Filter authors by works count:")
    print("   API:  Authors().filter_by_works_count(min_count=50, max_count=200)")
    authors = Authors().filter_by_works_count(min_count=50, max_count=200)
    print(f"   URL: {authors.url}")

    # Example 3: Filter by h-index
    print("\n3. Filter authors by h-index:")
    print("   API:  Authors().filter_by_h_index(min_h=20)")
    authors = Authors().filter_by_h_index(min_h=20)
    print(f"   URL: {authors.url}")


def example_institutions_filters():
    """Demonstrate Institutions convenience methods."""
    print("\n" + "=" * 80)
    print("INSTITUTIONS API - Convenience Methods")
    print("=" * 80)

    # Example 1: Filter by country
    print("\n1. Filter institutions by country:")
    print("   API:  Institutions().filter_by_country('US')")
    institutions = Institutions().filter_by_country("US")
    print(f"   URL: {institutions.url}")

    # Example 2: Filter by type
    print("\n2. Filter institutions by type:")
    print("   API:  Institutions().filter_by_type('education')")
    institutions = Institutions().filter_by_type("education")
    print(f"   URL: {institutions.url}")

    # Example 3: Filter by works count
    print("\n3. Filter institutions by works count:")
    print("   API:  Institutions().filter_by_works_count(min_count=10000)")
    institutions = Institutions().filter_by_works_count(min_count=10000)
    print(f"   URL: {institutions.url}")


def example_funders_filters():
    """Demonstrate Funders convenience methods."""
    print("\n" + "=" * 80)
    print("FUNDERS API - Convenience Methods")
    print("=" * 80)

    # Example 1: Filter by country
    print("\n1. Filter funders by country:")
    print("   API:  Funders().filter_by_country('US')")
    funders = Funders().filter_by_country("US")
    print(f"   URL: {funders.url}")

    # Example 2: Filter by works count
    print("\n2. Filter funders by works count:")
    print("   API:  Funders().filter_by_works_count(min_count=1000)")
    funders = Funders().filter_by_works_count(min_count=1000)
    print(f"   URL: {funders.url}")


async def example_with_results():
    """Show actual results from API calls."""
    print("\n" + "=" * 80)
    print("REAL API RESULTS - Demonstrating API/CLI Parity")
    print("=" * 80)

    # Example 1: Get works from an institution
    print("\n1. Get recent works from Stanford:")
    print("   Code: Works().filter_by_institution('I97018004')")
    print("              .filter_by_publication_year(start_year=2023)")
    print("              .search('AI')")

    works_query = (
        Works()
        .filter_by_institution("I97018004")
        .filter_by_publication_year(start_year=2023)
        .search("AI")
    )

    results = await works_query.get(per_page=3)
    print(f"\n   Found {len(results)} results:")
    for i, work in enumerate(results, 1):
        title = work.get("title", work.get("display_name", "Unknown"))
        year = work.get("publication_year", "N/A")
        print(f"   {i}. [{year}] {title[:70]}")

    # Example 2: Combine multiple filters
    print("\n2. Complex query - Articles about quantum computing from 2020-2021:")
    print("   Code: Works().filter_by_publication_year(start_year=2020, end_year=2021)")
    print("              .filter_by_type('article')")
    print("              .search('quantum computing')")

    works_query = (
        Works()
        .filter_by_publication_year(start_year=2020, end_year=2021)
        .filter_by_type("article")
        .search("quantum computing")
    )

    results = await works_query.get(per_page=3)
    print(f"\n   Found {len(results)} results:")
    for i, work in enumerate(results, 1):
        title = work.get("title", work.get("display_name", "Unknown"))
        year = work.get("publication_year", "N/A")
        citations = work.get("cited_by_count", 0)
        print(f"   {i}. [{year}] {title[:60]} (cited: {citations})")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print(" PyAlex API/CLI Parity Demonstration")
    print(" Now both API and CLI support the same filtering capabilities!")
    print("=" * 80)

    # Show all the URL patterns
    example_works_filters()
    example_authors_filters()
    example_institutions_filters()
    example_funders_filters()

    # Show real results
    asyncio.run(example_with_results())

    print("\n" + "=" * 80)
    print(" Summary")
    print("=" * 80)
    print("\nThe API now provides convenience methods that match CLI functionality:")
    print("  ✓ Works.filter_by_institution()    matches --institution-ids")
    print("  ✓ Works.filter_by_author()         matches --author-ids")
    print("  ✓ Works.filter_by_topic()          matches --topic-ids")
    print("  ✓ Works.filter_by_funder()         matches --funder-ids")
    print("  ✓ Works.filter_by_publication_year() matches --year")
    print("  ✓ Works.filter_by_publication_date() matches --date")
    print("  ✓ Works.filter_by_type()           matches --type")
    print("  ✓ And many more...")
    print("\nBoth interfaces now provide consistent, feature-rich access to OpenAlex!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
