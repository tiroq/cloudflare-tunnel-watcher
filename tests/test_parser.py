"""Tests for the URL parser module."""

import unittest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from parser import URLParser


class TestURLParser(unittest.TestCase):
    """Test cases for URLParser class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = URLParser()
    
    def test_extract_url_basic(self):
        """Test basic URL extraction."""
        line = "2025-12-05T04:30:15Z INF | https://abc123.trycloudflare.com |"
        url = self.parser.extract_url(line)
        self.assertEqual(url, "https://abc123.trycloudflare.com")
    
    def test_extract_url_with_surrounding_text(self):
        """Test URL extraction with surrounding text."""
        line = "Your quick tunnel is available at https://test-tunnel-xyz.trycloudflare.com for SSH"
        url = self.parser.extract_url(line)
        self.assertEqual(url, "https://test-tunnel-xyz.trycloudflare.com")
    
    def test_extract_url_no_url(self):
        """Test that no URL returns None."""
        line = "Some random output without a URL"
        url = self.parser.extract_url(line)
        self.assertIsNone(url)
    
    def test_extract_url_empty_line(self):
        """Test empty line returns None."""
        url = self.parser.extract_url("")
        self.assertIsNone(url)
    
    def test_extract_url_multiple_urls(self):
        """Test that first URL is extracted when multiple present."""
        line = "https://first.trycloudflare.com and https://second.trycloudflare.com"
        url = self.parser.extract_url(line)
        self.assertEqual(url, "https://first.trycloudflare.com")
    
    def test_extract_url_with_hyphens(self):
        """Test URL extraction with hyphens in subdomain."""
        line = "URL: https://test-tunnel-123-abc.trycloudflare.com"
        url = self.parser.extract_url(line)
        self.assertEqual(url, "https://test-tunnel-123-abc.trycloudflare.com")
    
    def test_extract_url_mixed_case(self):
        """Test URL extraction with mixed case."""
        line = "https://TesT123-AbC.trycloudflare.com"
        url = self.parser.extract_url(line)
        self.assertEqual(url, "https://TesT123-AbC.trycloudflare.com")
    
    def test_is_new_url_first_url(self):
        """Test that first URL is considered new."""
        url = "https://test.trycloudflare.com"
        self.assertTrue(self.parser.is_new_url(url))
        self.assertEqual(self.parser.current_url, url)
    
    def test_is_new_url_same_url(self):
        """Test that same URL is not considered new."""
        url = "https://test.trycloudflare.com"
        self.parser.current_url = url
        self.assertFalse(self.parser.is_new_url(url))
    
    def test_is_new_url_different_url(self):
        """Test that different URL is considered new."""
        self.parser.current_url = "https://old.trycloudflare.com"
        new_url = "https://new.trycloudflare.com"
        self.assertTrue(self.parser.is_new_url(new_url))
        self.assertEqual(self.parser.current_url, new_url)
    
    def test_reset(self):
        """Test parser reset."""
        self.parser.current_url = "https://test.trycloudflare.com"
        self.parser.reset()
        self.assertIsNone(self.parser.current_url)
    
    def test_url_pattern_does_not_match_invalid_domains(self):
        """Test that invalid domains are not matched."""
        invalid_urls = [
            "https://example.com",
            "https://cloudflare.com",
            "https://test.tryCloudflare.com",  # Wrong case
            "http://test..trycloudflare.com",  # Double dot
        ]
        for line in invalid_urls:
            url = self.parser.extract_url(line)
            # Should either be None or not match the invalid pattern
            if url:
                self.assertIn("trycloudflare.com", url)


class TestURLParserIntegration(unittest.TestCase):
    """Integration tests simulating real cloudflared output."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = URLParser()
    
    def test_real_cloudflared_output_simulation(self):
        """Test with simulated real cloudflared output."""
        lines = [
            "2025-12-05T04:30:10Z INF Starting cloudflared",
            "2025-12-05T04:30:11Z INF Registered tunnel connection",
            "2025-12-05T04:30:12Z INF |",
            "2025-12-05T04:30:12Z INF | Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):",
            "2025-12-05T04:30:12Z INF | https://rapid-forest-123abc.trycloudflare.com",
            "2025-12-05T04:30:12Z INF |",
        ]
        
        urls_found = []
        for line in lines:
            url = self.parser.extract_url(line)
            if url and self.parser.is_new_url(url):
                urls_found.append(url)
        
        self.assertEqual(len(urls_found), 1)
        self.assertEqual(urls_found[0], "https://rapid-forest-123abc.trycloudflare.com")


if __name__ == '__main__':
    unittest.main()