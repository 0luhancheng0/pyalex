#!/usr/bin/env python3
"""
Test script to verify rich progress bar functionality in async operations.
"""

import asyncio
import sys
import os

# Add the pyalex package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

import pyalex


async def test_async_with_rich_progress():
    """Test async functionality with rich progress bars."""
    print("Testing async functionality with rich progress bars...")
    
    # Test with a small query that should use async
    authors_query = pyalex.Authors().search("machine learning").filter(
        cited_by_count=">100"
    )
    
    print("\n1. Testing Authors async query (should use async with progress bar)...")
    try:
        # This should trigger async with progress bar since it's likely <= 10,000 results
        results = await authors_query.get_async(limit=50)
        print(f"   ✓ Successfully retrieved {len(results)} authors asynchronously")
        print(f"   ✓ First author: {results[0].display_name if results else 'No results'}")
    except Exception as e:
        print(f"   ✗ Error in async authors query: {e}")
    
    print("\n2. Testing Works async query with user limit (should use async)...")
    try:
        # Test the refined logic: even if total count > 10,000, 
        # if user limit <= 10,000, should still use async
        works_query = pyalex.Works().search("artificial intelligence").filter(
            publication_year=2023,
            cited_by_count=">5"
        )
        
        results = await works_query.get_async(limit=100)  # User limit <= 10,000
        print(f"   ✓ Successfully retrieved {len(results)} works asynchronously")
        print(f"   ✓ First work: {results[0].title[:50] if results else 'No results'}...")
    except Exception as e:
        print(f"   ✗ Error in async works query: {e}")
    
    print("\n3. Testing fallback to sync for large queries...")
    try:
        # This should fall back to sync pagination
        large_query = pyalex.Works().search("science")
        
        # Use the sync method for comparison
        results = large_query.get(limit=10)  # Small limit to keep test fast
        print(f"   ✓ Successfully retrieved {len(results)} works via sync method")
    except Exception as e:
        print(f"   ✗ Error in sync fallback: {e}")


def test_sync_with_rich_progress():
    """Test sync pagination with rich progress bars."""
    print("\n4. Testing sync pagination with rich progress bars...")
    
    try:
        # Test the updated CLI sync pagination function
        from pyalex.cli import _sync_paginate_with_progress
        
        # Create a small query for testing
        query = pyalex.Authors().search("einstein").filter(works_count=">10")
        
        print("   Running sync pagination with progress...")
        results = _sync_paginate_with_progress(query, "authors")
        print(f"   ✓ Successfully retrieved {len(results) if results else 0} authors with progress")
        
    except Exception as e:
        print(f"   ✗ Error in sync progress test: {e}")


def test_dependency_availability():
    """Test if required dependencies are available."""
    print("\n5. Testing dependency availability...")
    
    try:
        import aiohttp
        print("   ✓ aiohttp is available for async functionality")
    except ImportError:
        print("   ⚠ aiohttp not available - async will fall back to sync")
    
    try:
        import rich
        print("   ✓ rich is available for progress bars")
    except ImportError:
        print("   ⚠ rich not available - will fall back to basic logging")
    
    try:
        # Test importing the async session module
        from pyalex.client.async_session import async_batch_requests_with_progress
        print("   ✓ async_batch_requests_with_progress is importable")
    except ImportError as e:
        print(f"   ✗ Error importing async functions: {e}")


async def main():
    """Main test function."""
    print("=" * 60)
    print("PyAlex Rich Progress Bar Test")
    print("=" * 60)
    
    # Test dependency availability first
    test_dependency_availability()
    
    # Test async functionality
    await test_async_with_rich_progress()
    
    # Test sync functionality
    test_sync_with_rich_progress()
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
