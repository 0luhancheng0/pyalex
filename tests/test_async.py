#!/usr/bin/env python3
"""
Test script for PyAlex async functionality
"""

import asyncio
import sys

# Add pyalex to the path
sys.path.insert(0, '/home/lcheng/oz318/pyalex')

from pyalex import Works

async def test_async_functionality():
    """Test the new async functionality."""
    print("Testing PyAlex async functionality...")
    
    # Test 1: Basic async get
    print("\n1. Testing basic async get with small dataset...")
    try:
        works = Works().filter(publication_year=2023, cited_by_count=">100")
        
        # Get count first
        count_result = works.get(per_page=1)
        total_count = count_result.meta.get('count', 0)
        print(f"Total count: {total_count}")
        
        if total_count <= 10000:
            print("   Using async pagination...")
            result = await works.get_async(limit=10)
            print(f"   Retrieved {len(result)} results async")
        else:
            print("   Dataset too large for async, using sync...")
            result = works.get(limit=10)
            print(f"   Retrieved {len(result)} results sync")
            
    except Exception as e:
        print(f"   Error in async test: {e}")
    
    # Test 2: from-ids simulation
    print("\n2. Testing async from-ids functionality...")
    try:
        from pyalex.cli import _async_retrieve_entities
        
        # Test with a few work IDs
        test_ids = ['W2741809807', 'W2764836926', 'W2755950973']
        
        print(f"   Testing with IDs: {test_ids}")
        results = await _async_retrieve_entities(Works, test_ids, 'Works')
        print(f"   Retrieved {len(results)} works async")
        
    except ImportError as e:
        print(f"   aiohttp not available: {e}")
        print("   This is expected if aiohttp is not installed")
    except Exception as e:
        print(f"   Error in from-ids async test: {e}")

def test_pagination_fix():
    """Test the n_max pagination fix."""
    print("\n3. Testing pagination n_max fix...")
    
    try:
        works = Works().filter(publication_year=2023)
        
        # Test page pagination with n_max
        paginator_page = works.paginate(method="page", n_max=1000)
        print(f"   Page paginator n_max: {paginator_page.n_max}")
        
        # Test cursor pagination (should ignore n_max)
        paginator_cursor = works.paginate(method="cursor", n_max=1000)
        print(f"   Cursor paginator n_max: {paginator_cursor.n_max}")
        
    except Exception as e:
        print(f"   Error in pagination test: {e}")

if __name__ == "__main__":
    print("PyAlex Async Test Suite")
    print("=" * 40)
    
    # Test sync functionality first
    test_pagination_fix()
    
    # Test async functionality
    try:
        asyncio.run(test_async_functionality())
    except Exception as e:
        print(f"Async tests failed: {e}")
    
    print("\nTest complete!")
