#!/usr/bin/env python3
"""
Apify Actor for HTML cleaning.
This actor takes HTML content and cleans it by removing specified tags and attributes.
"""

import os
import sys
import json
from apify import Actor

# Add the shared directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from utils import clean_html


async def main():
    """
    Main actor function that processes HTML cleaning requests.
    """
    async with Actor:
        # Get input from Apify
        actor_input = await Actor.get_input() or {}
        
        # Extract HTML content from input
        html_content = actor_input.get('html')
        if not html_content:
            await Actor.fail('Missing required parameter: html')
            return
        
        # Get optional cleaning parameters (using camelCase as per input schema)
        tags_to_remove = actor_input.get('unwantedTags', [])
        attributes_to_remove = actor_input.get('unwantedAttrs', [])
        detect_article = actor_input.get('detectArticle', True)
        
        try:
            # Extract article content if requested
            if detect_article:
                from utils import extract_article_content
                html_content = extract_article_content(html_content)
            
            # Use shared utility to clean HTML
            cleaned_html = clean_html(
                html_content, 
                unwanted_tags=tags_to_remove,
                unwanted_attrs=attributes_to_remove
            )
            
            # Push result to dataset
            await Actor.push_data({
                'original_html': html_content,
                'cleaned_html': cleaned_html,
                'tags_removed': tags_to_remove,
                'attributes_removed': attributes_to_remove,
                'success': True
            })
            
            Actor.log.info('Successfully cleaned HTML content')
            
        except Exception as e:
            error_msg = f'Failed to clean HTML: {str(e)}'
            Actor.log.error(error_msg)
            
            # Push error result to dataset
            await Actor.push_data({
                'original_html': html_content,
                'cleaned_html': None,
                'success': False,
                'error': str(e)
            })
            
            await Actor.fail()


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())