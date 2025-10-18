"""
Basic PyAlex Usage Examples

This script demonstrates fundamental PyAlex operations:
- Simple queries
- Basic filtering
- Retrieving results
"""

from pyalex import Works, Authors, Institutions

def example_1_simple_work_search():
    """Search for works by keyword."""
    print("=" * 60)
    print("Example 1: Simple Work Search")
    print("=" * 60)
    
    # Search for works about "machine learning"
    results = Works().search("machine learning").get(limit=5)
    
    print(f"Found {len(results)} works:")
    for work in results:
        print(f"  - {work['title']}")
        print(f"    DOI: {work.get('doi', 'N/A')}")
        print(f"    Year: {work.get('publication_year', 'N/A')}")
        print()


def example_2_filter_by_year():
    """Filter works by publication year."""
    print("=" * 60)
    print("Example 2: Filter by Publication Year")
    print("=" * 60)
    
    # Get works from 2023
    results = Works().filter(publication_year=2023).get(limit=5)
    
    print(f"Found {len(results)} works from 2023:")
    for work in results:
        print(f"  - {work['title']}")
        print(f"    Citations: {work.get('cited_by_count', 0)}")
        print()


def example_3_author_lookup():
    """Look up an author by name."""
    print("=" * 60)
    print("Example 3: Author Lookup")
    print("=" * 60)
    
    # Search for authors
    results = Authors().search("Geoffrey Hinton").get(limit=3)
    
    print(f"Found {len(results)} authors:")
    for author in results:
        print(f"  - {author['display_name']}")
        print(f"    Works count: {author.get('works_count', 0)}")
        print(f"    Citations: {author.get('cited_by_count', 0)}")
        print(f"    OpenAlex ID: {author['id']}")
        print()


def example_4_institution_search():
    """Search for institutions."""
    print("=" * 60)
    print("Example 4: Institution Search")
    print("=" * 60)
    
    # Search for universities
    results = Institutions().search("MIT").get(limit=3)
    
    print(f"Found {len(results)} institutions:")
    for inst in results:
        print(f"  - {inst['display_name']}")
        print(f"    Country: {inst.get('country_code', 'N/A')}")
        print(f"    Works count: {inst.get('works_count', 0)}")
        print()


def example_5_get_by_id():
    """Retrieve a specific work by OpenAlex ID."""
    print("=" * 60)
    print("Example 5: Get Work by ID")
    print("=" * 60)
    
    # Get a specific work (example ID)
    # Note: Replace with a real OpenAlex ID
    work_id = "https://openalex.org/W2741809807"
    
    try:
        work = Works()[work_id]
        print(f"Title: {work['title']}")
        print(f"Year: {work.get('publication_year', 'N/A')}")
        print(f"Type: {work.get('type', 'N/A')}")
        print(f"Citations: {work.get('cited_by_count', 0)}")
    except Exception as e:
        print(f"Error retrieving work: {e}")
        print("(This example requires a valid OpenAlex work ID)")


def main():
    """Run all examples."""
    print("\n🚀 PyAlex Basic Usage Examples\n")
    
    try:
        example_1_simple_work_search()
        example_2_filter_by_year()
        example_3_author_lookup()
        example_4_institution_search()
        example_5_get_by_id()
        
        print("\n✅ All examples completed!")
        print("\nNext steps:")
        print("  - Try advanced_filtering.py for complex queries")
        print("  - See pagination_examples.py for handling large datasets")
        print("  - Check async_usage.py for high-performance async queries")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have:")
        print("  1. Installed PyAlex: pip install -e ..")
        print("  2. Set OPENALEX_EMAIL in .env file")
        print("  3. Internet connection to OpenAlex API")


if __name__ == "__main__":
    main()
