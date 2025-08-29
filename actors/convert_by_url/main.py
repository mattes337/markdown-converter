#!/usr/bin/env python3
"""
Apify Actor for URL to Markdown conversion.
This actor takes a URL and converts its content to Markdown format.
"""

import os
import sys
import json
from apify import Actor

# Add the shared directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from conversion_utils import convert_url_to_markdown


async def main():
    """
    Main actor function that processes URL to Markdown conversion requests.
    """
    async with Actor:
        # Get input from Apify
        actor_input = await Actor.get_input() or {}
        
        # Extract URL from input
        url = actor_input.get('url')
        if not url:
            await Actor.fail()
            return
        
        # Get optional parameters
        tags_to_remove = actor_input.get('tags_to_remove', [])
        attributes_to_remove = actor_input.get('attributes_to_remove', [])
        
        try:
            # Use shared utility to convert URL to Markdown
            markdown_content = convert_url_to_markdown(
                url,
                unwanted_tags=tags_to_remove,
                unwanted_attrs=attributes_to_remove
            )
            
            # Push result to dataset
            await Actor.push_data({
                'url': url,
                'markdown': markdown_content,
                'tags_removed': tags_to_remove,
                'attributes_removed': attributes_to_remove,
                'success': True
            })
            
            Actor.log.info(f'Successfully converted URL to Markdown: {url}')
            
        except Exception as e:
            error_msg = f'Failed to convert URL {url} to Markdown: {str(e)}'
            Actor.log.error(error_msg)
            
            # Push error result to dataset
            await Actor.push_data({
                'url': url,
                'markdown': None,
                'success': False,
                'error': str(e)
            })
            
            await Actor.fail()


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())