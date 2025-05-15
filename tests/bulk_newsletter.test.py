import unittest
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))
from bulk_newsletter import extract_main_domain, check_for_captcha

class TestBulkNewsletter(unittest.TestCase):
    def test_extract_main_domain(self):
        test_cases = [
            ('https://www.example.com/page', 'https://example.com'),
            ('http://subdomain.example.com', 'http://example.com'),
            ('https://example.com', 'https://example.com'),
            ('http://www.test.co.uk/path', 'http://test.co.uk'),
        ]
        
        for input_url, expected in test_cases:
            result = extract_main_domain(input_url)
            self.assertEqual(result, expected)

    def test_check_for_captcha(self):
        test_cases = [
            ('<div class="g-recaptcha"></div>', True),
            ('Please verify you are human', True),
            ('Normal page content', False),
            ('Security check required', True),
        ]
        
        for html_content, expected in test_cases:
            result = check_for_captcha(html_content)
            self.assertEqual(result, expected)

if __name__ == '__main__':
    unittest.main()