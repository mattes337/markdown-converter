#!/usr/bin/env python3
"""
Apify Actor for URL dereferencing.
This actor takes a URL and follows redirects to get the final destination URL.
"""

import os
import sys
import json
from apify import Actor

# Add the shared directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from conversion_utils import dereference_url


async def main():
    """
    Main actor function that processes URL dereferencing requests.
    """
    async with Actor:
        # Get input from Apify
        actor_input = await Actor.get_input() or {}
        
        # Extract URL from input
        url = actor_input.get('url')
        if not url:
            await Actor.fail('Missing required parameter: url')
            return
        
        try:
            # Use shared utility to dereference URL
            final_url = dereference_url(url)
            
            # Push result to dataset
            await Actor.push_data({
                'original_url': url,
                'final_url': final_url,
                'success': True
            })
            
            Actor.log.info(f'Successfully dereferenced URL: {url} -> {final_url}')
            
        except Exception as e:
            error_msg = f'Failed to dereference URL {url}: {str(e)}'
            Actor.log.error(error_msg)
            
            # Push error result to dataset
            await Actor.push_data({
                'original_url': url,
                'final_url': None,
                'success': False,
                'error': str(e)
            })
            
            await Actor.fail(error_msg)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())