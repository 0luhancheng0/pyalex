#!/usr/bin/env python3
"""
Test async pagination functionality
"""

import asyncio
import sys

# Add pyalex to the path
sys.path.insert(0, '/home/lcheng/oz318/pyalex')

from pyalex import Works

async def test_async_pagination():
    """Test async pagination."""
    print("Testing async pagination...")
    
    try:
        # Test with a filter that should return a smaller dataset
        query = Works().filter(publication_year=2024, cited_by_count='>1000')
        
        # Get count first
        count_result = query.get(per_page=1)
        total_count = count_result.meta.get('count', 0)
        print(f"Total count: {total_count}")
        
        if total_count <= 10000:
            print("Using async pagination...")
            results = await query.get_async(limit=5)
            print(f"Retrieved {len(results)} results async")
            if results:
                print(f"First result: {results[0].get('display_name', 'No title')}")
        else:
            print("Dataset too large for async, using sync...")
            results = query.get(limit=5)
            print(f"Retrieved {len(results)} results sync")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_async_pagination())
