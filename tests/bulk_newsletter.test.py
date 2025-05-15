import unittest
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from bulk_newsletter import extract_main_domain, check_for_captcha

class TestBulkNewsletter(unittest.TestCase):
    def test_extract_main_domain(self):
        """Test domain extraction from URLs"""
        test_cases = [
            ('https://www.example.com/page', 'https://example.com'),
            ('http://subdomain.example.com', 'http://example.com'),
            ('https://example.com', 'https://example.com'),
            ('http://www.test.co.uk/path', 'http://test.co.uk'),
        ]
        
        for input_url, expected in test_cases:
            with self.subTest(input_url=input_url):
                result = extract_main_domain(input_url)
                self.assertEqual(result, expected)

    def test_check_for_captcha(self):
        """Test CAPTCHA detection in HTML content"""
        test_cases = [
            ('<div class="g-recaptcha"></div>', True),
            ('Please verify you are human', True),
            ('Normal page content', False),
            ('Security check required', True),
            ('<div>No captcha here</div>', False),
            ('<iframe src="recaptcha.google.com"></iframe>', True),
            ('Are you human? Please verify', True),
            ('Welcome to our website', False),
        ]
        
        for html_content, expected in test_cases:
            with self.subTest(content=html_content[:30]):
                result = check_for_captcha(html_content)
                self.assertEqual(result, expected)

if __name__ == '__main__':
    unittest.main(verbosity=2)