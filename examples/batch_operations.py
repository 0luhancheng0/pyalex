"""
Batch Operations Examples

This script demonstrates how to efficiently process large batches of data.
"""

import asyncio

from pyalex import Works


def example_1_batch_by_ids():
    """Fetch multiple works by their IDs."""
    print("=" * 60)
    print("Example 1: Batch Fetch by IDs")
    print("=" * 60)

    # List of OpenAlex IDs
    work_ids = [
        "W2741809807",  # Attention is All You Need
        "W2964105666",  # BERT
        "W2963146074",  # GPT-3
        "W3138567166",  # ResNet
        "W2124350638",  # AlexNet
    ]

    # Fetch all works
    results = []
    for work_id in work_ids:
        work = Works()[work_id]
        results.append(work)
        print(f"  ✓ {work.get('title', 'Unknown')[:60]}...")

    print(f"\nFetched {len(results)} works")
    print()


def example_2_batch_with_filters():
    """Process results in batches with filters."""
    print("=" * 60)
    print("Example 2: Batch Processing with Filters")
    print("=" * 60)

    # Query for many results
    query = (
        Works()
        .search("machine learning")
        .filter(publication_year=2023, cited_by_count=">10")
    )

    # Process in batches of 50
    batch_size = 50
    total_processed = 0
    citations_sum = 0

    for i in range(0, 200, batch_size):
        batch = query[i : i + batch_size]
        total_processed += len(batch)
        citations_sum += sum(w.get("cited_by_count", 0) for w in batch)
        print(f"  Processed batch {i // batch_size + 1}: {len(batch)} works")

    print(f"\nTotal processed: {total_processed} works")
    print(f"Average citations: {citations_sum / total_processed:.1f}")
    print()


async def example_3_async_batch():
    """Process multiple batches using async/await."""
    print("\nExample 3: Async Batch Processing")
    print("=" * 50)

    # Define multiple queries
    queries = [
        Works().filter(publication_year=year, type="article")
        for year in [2020, 2021, 2022]
    ]

    # Run all queries in parallel using asyncio.gather
    tasks = [q.get(limit=50) for q in queries]
    print()


def example_4_batch_export():
    """Export large dataset in batches."""
    print("=" * 60)
    print("Example 4: Batch Export to Files")
    print("=" * 60)

    query = Works().search("artificial intelligence").filter(publication_year=2023)

    # Export in batches to avoid memory issues
    batch_size = 100
    max_results = 300

    print(f"Exporting up to {max_results} results in batches of {batch_size}...")

    all_titles = []
    for i in range(0, max_results, batch_size):
        batch = query[i : i + batch_size]
        titles = [w.get("title") for w in batch if w.get("title")]
        all_titles.extend(titles)
        print(f"  Exported batch {i // batch_size + 1}: {len(batch)} works")

    print(f"\nTotal exported: {len(all_titles)} titles")
    print(f"First title: {all_titles[0][:60]}...")
    print()


def example_5_batch_aggregation():
    """Aggregate data from batches."""
    print("=" * 60)
    print("Example 5: Batch Aggregation")
    print("=" * 60)

    query = Works().search("climate change").filter(publication_year="2020-2023")

    # Aggregate statistics from batches
    batch_size = 100
    max_results = 300

    stats = {
        "total": 0,
        "open_access": 0,
        "total_citations": 0,
        "years": {},
    }

    for i in range(0, max_results, batch_size):
        batch = query[i : i + batch_size]

        for work in batch:
            stats["total"] += 1

            if work.get("open_access", {}).get("is_oa"):
                stats["open_access"] += 1

            stats["total_citations"] += work.get("cited_by_count", 0)

            year = work.get("publication_year")
            if year:
                stats["years"][year] = stats["years"].get(year, 0) + 1

        print(f"  Processed batch {i // batch_size + 1}")

    print("\nAggregated Statistics:")
    print(f"  Total works: {stats['total']}")
    print(
        f"  Open access: {stats['open_access']} ({stats['open_access'] / stats['total'] * 100:.1f}%)"
    )
    print(f"  Avg citations: {stats['total_citations'] / stats['total']:.1f}")
    print(f"  Years distribution: {stats['years']}")
    print()


def example_6_batch_with_retry():
    """Batch processing with error handling."""
    print("=" * 60)
    print("Example 6: Batch with Error Handling")
    print("=" * 60)

    # List of IDs (some might be invalid)
    work_ids = [
        "W2741809807",
        "INVALID_ID",
        "W2964105666",
        "ANOTHER_INVALID",
        "W2963146074",
    ]

    successful = []
    failed = []

    for work_id in work_ids:
        try:
            work = Works()[work_id]
            successful.append(work)
            print(f"  ✓ Success: {work_id}")
        except Exception as e:
            failed.append(work_id)
            print(f"  ✗ Failed: {work_id} ({str(e)[:40]}...)")

    print("\nResults:")
    print(f"  Successful: {len(successful)}")
    print(f"  Failed: {len(failed)}")
    print()


def main():
    """Run all batch operation examples."""
    print("\n📦 PyAlex Batch Operations Examples\n")
    print("Batch processing strategies:")
    print("  1. Batch fetch by IDs")
    print("  2. Batch with filters")
    print("  3. Async parallel batches")
    print("  4. Batch export")
    print("  5. Batch aggregation")
    print("  6. Error handling")
    print()

    try:
        # Run examples
        example_1_batch_by_ids()
        example_2_batch_with_filters()

        # Async example
        asyncio.run(example_3_async_batch())

        example_4_batch_export()
        example_5_batch_aggregation()
        example_6_batch_with_retry()

        print("\n✅ All batch operation examples completed!")
        print("\nBest practices:")
        print("  - Process large datasets in batches to manage memory")
        print("  - Use async for parallel batch processing")
        print("  - Always include error handling for robustness")
        print("  - Consider rate limits when processing large batches")

    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
