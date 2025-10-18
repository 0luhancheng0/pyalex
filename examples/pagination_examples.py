"""
Pagination Examples

This script demonstrates different pagination strategies in PyAlex.
"""

import asyncio
from pyalex import Works, Authors


def example_1_basic_pagination():
    """Basic pagination with per_page and page."""
    print("=" * 60)
    print("Example 1: Basic Pagination")
    print("=" * 60)
    
    # Get first page
    page1 = Works().search("machine learning").paginate(per_page=25, page=1)
    print(f"Page 1: {len(page1)} results")
    
    # Get second page
    page2 = Works().search("machine learning").paginate(per_page=25, page=2)
    print(f"Page 2: {len(page2)} results")
    
    # Get third page
    page3 = Works().search("machine learning").paginate(per_page=25, page=3)
    print(f"Page 3: {len(page3)} results")
    print()


def example_2_cursor_pagination():
    """Cursor-based pagination for large datasets."""
    print("=" * 60)
    print("Example 2: Cursor Pagination")
    print("=" * 60)
    
    # Cursor pagination is more efficient for large datasets
    query = Works().search("artificial intelligence").filter(
        publication_year=2023
    )
    
    # Use cursor pagination (recommended for >10,000 results)
    cursor = query.paginate(per_page=100, cursor="*")
    
    count = 0
    for page in cursor:
        count += len(page)
        print(f"Fetched {count} results so far...")
        if count >= 500:  # Stop after 500 for demo
            break
    
    print(f"Total fetched: {count} results")
    print()


def example_3_slice_notation():
    """Use Python slice notation for pagination."""
    print("=" * 60)
    print("Example 3: Slice Notation")
    print("=" * 60)
    
    # PyAlex supports slice notation!
    query = Works().search("deep learning")
    
    # Get results 0-50
    first_50 = query[0:50]
    print(f"First 50 results: {len(first_50)} works")
    
    # Get results 50-100
    next_50 = query[50:100]
    print(f"Next 50 results: {len(next_50)} works")
    
    # Get results 100-150
    another_50 = query[100:150]
    print(f"Results 100-150: {len(another_50)} works")
    print()


def example_4_iterate_all():
    """Iterate through all results automatically."""
    print("=" * 60)
    print("Example 4: Iterate All Results")
    print("=" * 60)
    
    # Use iter() to automatically paginate through all results
    query = Works().search("neural networks").filter(
        publication_year=2023
    )
    
    count = 0
    for work in query:
        count += 1
        if count % 100 == 0:
            print(f"Processed {count} works...")
        if count >= 300:  # Stop after 300 for demo
            break
    
    print(f"Total processed: {count} works")
    print()


async def example_5_async_pagination():
    """Use async methods for faster pagination."""
    print("\nExample 5: Async Pagination")
    print("=" * 50)
    
    query = Works().filter(publication_year=2023, type="article")
    
    # Async pagination is faster for large datasets
    results = await query.get(limit=200)


def example_6_page_metadata():
    """Access pagination metadata."""
    print("=" * 60)
    print("Example 6: Pagination Metadata")
    print("=" * 60)
    
    # Get metadata about pagination
    query = Works().search("transformer architecture")
    
    # First page
    page = query.paginate(per_page=25, page=1)
    
    # Access metadata (if available)
    print(f"Results on this page: {len(page)}")
    
    # Get meta information from query using slice notation (which wraps async with asyncio.run)
    meta = query[:1][0] if query.count() > 0 else None
    if meta:
        print(f"First result title: {meta.get('title', 'N/A')[:60]}...")
    print()


def main():
    """Run all pagination examples."""
    print("\n📄 PyAlex Pagination Examples\n")
    print("Pagination strategies available:")
    print("  1. Basic pagination (per_page + page)")
    print("  2. Cursor pagination (for large datasets)")
    print("  3. Slice notation (Pythonic)")
    print("  4. Iteration (automatic pagination)")
    print("  5. Async pagination (best performance)")
    print()
    
    try:
        # Run examples
        example_1_basic_pagination()
        example_2_cursor_pagination()
        example_3_slice_notation()
        example_4_iterate_all()
        
        # Async example
        asyncio.run(example_5_async_pagination())
        
        example_6_page_metadata()
        
        print("\n✅ All pagination examples completed!")
        print("\nBest practices:")
        print("  - Use cursor pagination for >10,000 results")
        print("  - Use async for datasets >100 results")
        print("  - Use slice notation for readable code")
        print("  - Use iteration for processing all results")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
