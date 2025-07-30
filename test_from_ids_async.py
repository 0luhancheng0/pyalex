#!/usr/bin/env python3
"""
Test async from-ids functionality directly
"""

import asyncio
import sys

# Add pyalex to the path
sys.path.insert(0, '/home/lcheng/oz318/pyalex')

from pyalex import Works

async def test_from_ids_async():
    """Test async retrieval of entities by ID."""
    print("Testing async from-ids functionality...")
    
    try:
        from pyalex.cli import _async_retrieve_entities
        
        # Test with a few work IDs (some valid, some invalid)
        test_ids = ['W2741809807', 'W2764836926', 'W2755950973', 'W123456789']
        
        print(f"Testing with IDs: {test_ids}")
        results = await _async_retrieve_entities(Works, test_ids, 'Works')
        print(f"Retrieved {len(results)} works async")
        
        for work in results:
            print(f"  - {work.get('display_name', 'No title')} ({work.get('id', 'No ID')})")
            
    except ImportError as e:
        print(f"aiohttp not available: {e}")
        print("This is expected if aiohttp is not installed")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_from_ids_async())
