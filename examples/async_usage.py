"""
Async Usage Examples

This script demonstrates how to use PyAlex's async methods for better performance.
"""

import asyncio
from pyalex import Works, Authors


async def example_1_basic_async():
    """Basic async query example."""
    print("Example 1: Basic Async Query")
    print("=" * 50)
    
    results = await Works().search("quantum computing").get(limit=10)


async def example_2_parallel_queries():
    """Run multiple queries in parallel."""
    print("\nExample 2: Parallel Queries")
    print("=" * 50)
    
    # Create multiple async queries
    query1 = Works().search("machine learning").get(limit=5)
    query2 = Works().search("deep learning").get(limit=5)
    query3 = Authors().search("Yann LeCun").get(limit=3)


async def example_3_large_dataset():
    """Fetch a large dataset using async pagination."""
    print("\nExample 3: Large Dataset with Async Pagination")
    print("=" * 50)
    
    results = await Works().filter(
        publication_year=2023,
        type="article"
    ).get(limit=100)


def main():
    """Run all async examples."""
    print("\n⚡ PyAlex Async Usage Examples\n")
    print("Note: Async methods provide better performance for:")
    print("  - Large datasets (>100 results)")
    print("  - Multiple parallel queries")
    print("  - High-throughput applications\n")
    
    try:
        # Run all async examples
        asyncio.run(example_1_basic_async())
        asyncio.run(example_2_parallel_queries())
        asyncio.run(example_3_large_dataset())
        
        print("\n✅ All async examples completed!")
        print("\nPerformance tips:")
        print("  - Use get() with await for datasets >100 results")
        print("  - Use asyncio.gather() for parallel queries")
        print("  - Async methods use HTTP/2 and connection pooling")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
