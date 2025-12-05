"""Parser module for extracting Cloudflare tunnel URLs from stdout."""

import re
from typing import Optional


class URLParser:
    """Parser for extracting Cloudflare tunnel URLs from cloudflared output."""
    
    # Regex pattern for Cloudflare Quick Tunnel URLs
    URL_PATTERN = re.compile(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com')
    
    def __init__(self):
        """Initialize the URL parser."""
        self.current_url: Optional[str] = None
    
    def extract_url(self, line: str) -> Optional[str]:
        """
        Extract URL from a single line of output.
        
        Args:
            line: A line of text from cloudflared stdout
            
        Returns:
            The extracted URL if found, None otherwise
        """
        if not line:
            return None
            
        match = self.URL_PATTERN.search(line)
        return match.group(0) if match else None
    
    def is_new_url(self, url: str) -> bool:
        """
        Check if the URL is different from the current URL.
        
        Args:
            url: The URL to check
            
        Returns:
            True if this is a new URL, False otherwise
        """
        if url != self.current_url:
            self.current_url = url
            return True
        return False
    
    def reset(self):
        """Reset the parser state."""
        self.current_url = None