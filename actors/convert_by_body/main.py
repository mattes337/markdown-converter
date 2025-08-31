#!/usr/bin/env python3
"""
Apify Actor for content body to Markdown conversion.
This actor takes HTML or text content and converts it to Markdown format.
"""

import os
import sys
import json
from apify import Actor

# Add the shared directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from conversion_utils import convert_body_to_markdown


async def main():
    """
    Main actor function that processes content body to Markdown conversion requests.
    """
    async with Actor:
        # Get input from Apify
        actor_input = await Actor.get_input() or {}
        
        # Extract content from input
        content = actor_input.get('content')
        if not content:
            await Actor.fail()
            return
        
        # Get optional parameters
        content_type = actor_input.get('content_type', 'text/html')
        tags_to_remove = actor_input.get('tags_to_remove', [])
        attributes_to_remove = actor_input.get('attributes_to_remove', [])
        
        try:
            # Use shared utility to convert content to Markdown
            markdown_content = convert_body_to_markdown(
                content,
                content_type=content_type,
                unwanted_tags=tags_to_remove,
                unwanted_attrs=attributes_to_remove
            )
            
            # Push result to dataset
            await Actor.push_data({
                'original_content': content,
                'content_type': content_type,
                'markdown': markdown_content,
                'tags_removed': tags_to_remove,
                'attributes_removed': attributes_to_remove,
                'success': True
            })
            
            Actor.log.info('Successfully converted content to Markdown')
            
        except Exception as e:
            error_msg = f'Failed to convert content to Markdown: {str(e)}'
            Actor.log.error(error_msg)
            
            # Push error result to dataset
            await Actor.push_data({
                'original_content': content,
                'content_type': content_type,
                'markdown': None,
                'success': False,
                'error': str(e)
            })
            
            await Actor.fail()


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())