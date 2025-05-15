import unittest
from unittest.mock import patch, MagicMock
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bulk_newsletter import process_website, extract_main_domain, check_for_captcha

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

    @patch('selenium.webdriver.Chrome')
    def test_process_website(self, mock_chrome):
        # Mock driver setup
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # Mock successful newsletter signup
        mock_driver.page_source = 'Normal page content'
        mock_driver.find_elements.return_value = [
            MagicMock(
                get_attribute=lambda x: 'email' if x == 'type' else '',
                is_displayed=lambda: True,
                is_enabled=lambda: True
            )
        ]
        
        result = process_website('test@example.com', 'https://example.com', 1)
        self.assertEqual(result, 'Success')
        
        # Mock CAPTCHA detection
        mock_driver.page_source = '<div class="g-recaptcha"></div>'
        result = process_website('test@example.com', 'https://example.com', 1)
        self.assertEqual(result, 'CAPTCHA')

if __name__ == '__main__':
    unittest.main()