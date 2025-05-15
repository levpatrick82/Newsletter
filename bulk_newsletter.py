import os
import csv
import random
import logging
import time
import urllib.parse
import tempfile
import shutil
import subprocess
import re
from contextlib import contextmanager
from datetime import datetime
from multiprocessing import Pool, cpu_count
from functools import partial
from urllib.parse import urlparse, urljoin

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
    WebDriverException
)

# --- Virtual Display Setup ---
@contextmanager
def virtual_display(width=1920, height=1080):
    """Create a virtual display using Xvfb."""
    # Since we're using headless Chrome, we don't need a virtual display
    try:
        yield
    finally:
        pass

# --- Global Configuration & Bilingual Keyword Sets ---
LOG_FILENAME = 'signup_log.txt'
CSV_FILENAME = 'csvimport.csv'
CAPTCHA_SITES_FILENAME = 'captcha_sites.txt'
FAULTY_SITES_FILENAME = 'faulty_sites.txt'
COMPANY_INFO_CSV = 'company_info.csv'

IMPRINT_KEYWORDS = [
    'imprint', 'impressum', 'legal', 'about us', 'contact', 'legal notice',
    'company info', 'über uns', 'kontakt', 'mentions légales', 'chi siamo',
    'contacto', 'about', 'contact us', 'rechtliche hinweise', 'legal information'
]

COMPANY_INFO_HEADERS = [
    'Website', 'Company Name', 'Street Address', 'ZIP', 'City', 'Country',
    'Phone', 'Email', 'CEO/Managing Director', 'Tax ID', 'Commercial Register',
    'Court of Registration', 'Legal Representatives', 'VAT ID'
]

# User Data
SIGNUP_EMAIL = "max.plugilo@example.com"
SIGNUP_NAME_FULL = "Max Plugilo"
SIGNUP_FIRST_NAME = "Max"
SIGNUP_LAST_NAME = "Plugilo"
SIGNUP_COMPANY = "Plugilo Inc."

# Bilingual Keywords (Lowercase)
EMAIL_KEYWORDS = ["email", "e-mail", "mailadresse", "your-email", "email address", "e-mail-adresse", "ihre e-mail", "adresse de messagerie"]
SUBMIT_BUTTON_KEYWORDS = ['subscribe', 'sign up', 'join', 'register', 'go', 'send', 'submit', 'anmelden', 'abonnieren', 'weiter', 'eintragen', 'absenden', 'jetzt anmelden', 's\'inscrire', 'receive', 'bestätigen', 'speichern', 'save', 'order', 'bestellen', 'jetzt registrieren']
NAVIGATION_LINK_KEYWORDS = ["newsletter", "subscribe", "subscription", "e-news", "updates", "mailing list", "stay informed", "connect", "contact", "kontakt", "anmelden", "abonnieren", "aktuelles", "informiert bleiben", "presseverteiler", "news", "community", "kontaktformular", "contact form", "bleiben sie auf dem laufenden", "e-mail liste"]
CHECKBOX_KEYWORDS = ["consent", "agree", "terms", "privacy", "policy", "datenschutz", "akzeptieren", "bestätigen", "conditions", "subscribe", "newsletter", "information", "zustimmung", "einverstanden", "datenschutzerklärung", "agb", "data protection", "i have read", "ich habe gelesen", "i accept", "ich akzeptiere", "allgemeine geschäftsbedingungen"]
UNSUBSCRIBE_CHECKBOX_KEYWORDS = ["unsubscribe", "optout", "opt-out", "abmelden", "no thanks", "don't want", "keine e-mails", "abbestellen", "nicht abonnieren"]
FIRST_NAME_KEYWORDS = ["firstname", "first_name", "fname", "vorname", "givenname", "first-name"]
LAST_NAME_KEYWORDS = ["lastname", "last_name", "lname", "nachname", "surname", "familyname", "last-name", "familienname"]
FULL_NAME_KEYWORDS = ["name", "fullname", "yourname", "your-name", "ihr name", "vollständiger name", "kontaktperson", "ansprechpartner", "full name", "name des kontakts"]
COMPANY_KEYWORDS = ["company", "organization", "organisation", "firm", "business", "firma", "unternehmen"]
SUCCESS_MESSAGE_KEYWORDS = ["thank you", "thanks", "success", "subscribed", "confirmation", "check your email", "danke", "vielen dank", "erfolgreich", "bestätigung", "angemeldet", "prüfen sie ihre e-mails", "ihre anmeldung war erfolgreich", "subscription successful", "anmeldung erfolgreich"]
COOKIE_ACCEPT_KEYWORDS = ['accept all', 'allow all', 'accept cookies', 'accept', 'agree', 'ok', 'got it', 'understand', 'verstanden', 'akzeptieren', 'alle akzeptieren', 'zustimmen', 'einverstanden', 'allow cookies', 'cookies zulassen', 'i agree', 'ich stimme zu', 'confirm', 'bestätigen']
CAPTCHA_INDICATOR_KEYWORDS = ["verify you are human", "verify you are not a bot", "captcha", " recaptcha", "security check", "sicherheitsüberprüfung", "ich bin kein roboter", "are you human", "menschliche überprüfung"]

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)

# --- Selenium WebDriver Options ---
def setup_chrome_options(process_id=None):
    chrome_options = ChromeOptions()
    
    # Create a process-specific Chrome profile directory
    current_process = os.getpid()
    profile_dir = os.path.join(tempfile.gettempdir(), f'chrome_profile_{process_id}_{current_process}_{int(time.time())}')
    
    # Ensure the directory exists and is empty
    if os.path.exists(profile_dir):
        shutil.rmtree(profile_dir)
    os.makedirs(profile_dir)
    
    # Set Chrome flags
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Add essential Chrome arguments
    arguments = [
        '--no-sandbox',
        '--headless=new',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-extensions',
        '--disable-software-rasterizer',
        '--disable-notifications',
        '--disable-default-apps',
        '--disable-popup-blocking',
        '--disable-background-networking',
        '--disable-sync',
        '--disable-translate',
        '--metrics-recording-only',
        '--mute-audio',
        '--no-first-run',
        '--no-default-browser-check',
        '--window-size=1920,1080',
        '--remote-debugging-port=0',
        f'--user-data-dir={profile_dir}'
    ]
    
    for arg in arguments:
        chrome_options.add_argument(arg)
    
    # Store directory for cleanup
    chrome_options.profile_dir = profile_dir
    
    return chrome_options

driver = None  # Global driver instance, initialized in main()

# --- Helper Functions ---
def scroll_and_wait_for_clickable(element, timeout=10):
    global driver
    try:
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center', inline: 'nearest'});", element)
        time.sleep(random.uniform(0.2, 0.4))  # Short pause for scroll
        return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(element))
    except TimeoutException:
        element_info = f"Tag='{element.tag_name if hasattr(element, 'tag_name') else 'N/A'}'"
        try:
            element_info += f", ID='{element.get_attribute('id')}'"
        except Exception:
            pass
        try:
            element_info += f", Text='{element.text[:30] if hasattr(element, 'text') else ''}'"
        except Exception:
            pass
        logging.warning(f"Timeout waiting for element to be clickable after scroll: {element_info}")
        raise
    except Exception as e_scroll:
        logging.error(f"Error in scroll_and_wait_for_clickable for {getattr(element,'tag_name','N/A')} : {e_scroll}")
        raise

def check_for_captcha(page_source):
    captcha_indicators = [
        'captcha',
        'recaptcha',
        'g-recaptcha',
        'h-captcha',
        'hcaptcha',
        'verify you are human',
        'prove you are human',
        'are you human',
        'bot check',
        'security check',
        'verification required'
    ]
    
    page_source_lower = page_source.lower()
    return any(indicator in page_source_lower for indicator in captcha_indicators)

def scroll_and_wait_for_clickable(element_to_interact, timeout=8):
    global driver
    try:
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center', inline: 'nearest'});", element_to_interact)
        time.sleep(random.uniform(0.2, 0.4)) # Short pause for scroll
        return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(element_to_interact))
    except TimeoutException:
        element_info = f"Tag='{element_to_interact.tag_name if hasattr(element_to_interact, 'tag_name') else 'N/A'}'"
        try:
            element_info += f", ID='{element_to_interact.get_attribute('id')}'"
        except Exception:
            pass
        try:
            element_info += f", Text='{element_to_interact.text[:30] if hasattr(element_to_interact, 'text') else ''}'"
        except Exception:
            pass
        logging.warning(f"Timeout waiting for element to be clickable after scroll: {element_info}")
        raise
    except Exception as e_scroll:
        logging.error(f"Error in scroll_and_wait_for_clickable for {getattr(element_to_interact,'tag_name','N/A')} : {e_scroll}")
        raise

def submit_form_with_retry(form_element_context, submit_button_element, page_url_before_submit, success_keywords_list):
    """
    Attempts to submit a form with retries and overlay handling
    
    Args:
        form_element_context: The form element containing the submit button (can be None)
        submit_button_element: The submit button element to click
        page_url_before_submit: The URL before form submission to detect successful submission
        success_keywords_list: List of keywords indicating successful submission
        
    Returns:
        bool: True if submission was successful, False otherwise
    """
    global driver
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            logging.info(f"Submit attempt {attempt + 1}")
            final_submit_button = scroll_and_wait_for_clickable(submit_button_element, 7)
            final_submit_button.click()
            logging.info(f"Clicked submit button")
            
            # Wait for possible success indicators
            time.sleep(random.uniform(2.0, 3.5))
            
            # Check for URL change
            current_url = driver.current_url
            if current_url != page_url_before_submit and \
               not any(err_kw in current_url.lower() for err_kw in ["error", "fehler", "problem"]):
                logging.info(f"URL changed after submission: {current_url}")
                return True
            
            # Check page content for success indicators
            page_text = driver.page_source.lower()
            if any(keyword in page_text for keyword in success_keywords_list):
                logging.info("Found success indicator in page content")
                return True
            
            # If we're still on the same page, we might need to handle overlays
            if attempt < max_attempts - 1:
                logging.info("Looking for and closing any overlays...")
                try:
                    # Handle overlays
                    overlay_selectors = [
                        "//button[contains(@class, 'close') or contains(@id, 'close')]",
                        "//div[contains(@class, 'modal') or contains(@class, 'overlay')]//button",
                        "//*[contains(@class, 'popup')]//button[contains(@class, 'close')]"
                    ]
                    
                    for selector in overlay_selectors:
                        try:
                            close_buttons = driver.find_elements(By.XPATH, selector)
                            for button in close_buttons:
                                if button.is_displayed():
                                    button.click()
                                    time.sleep(1)
                        except Exception as e_overlay:
                            logging.debug(f"Error handling overlay with selector {selector}: {e_overlay}")
                except Exception as e_overlay_main:
                    logging.debug(f"Error in overlay handling: {e_overlay_main}")
                
                time.sleep(random.uniform(1.0, 2.0))
                continue
                
        except ElementClickInterceptedException:
            logging.warning(f"Submit attempt {attempt + 1} failed: button click intercepted")
            if attempt < max_attempts - 1:
                time.sleep(random.uniform(1.0, 2.0))
                continue
        except Exception as e:
            logging.warning(f"Submit attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_attempts - 1:
                time.sleep(random.uniform(1.0, 2.0))
                continue
            else:
                return False
    
    logging.warning("All submit attempts failed")
    return False

def signup_to_newsletter(url_to_signup, email_str):
    global driver
    logging.info(f"\nAttempting signup for {url_to_signup}")
    try:
        # Wait for at least one input field to be present
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "input")))
        time.sleep(random.uniform(1.5, 2.5))  # Additional wait to let dynamic content load

        # Get all form-related elements
        forms = driver.find_elements(By.TAG_NAME, "form")
        inputs = driver.find_elements(By.TAG_NAME, "input")
        page_url_before_submit = driver.current_url

        # Better form validation and error reporting
        if not forms and not inputs:
            logging.error(f"No forms or inputs found on {url_to_signup}")
            return "No Form"

        email_inputs = []
        for input_element in inputs:
            try:
                input_type = input_element.get_attribute("type")
                input_name = input_element.get_attribute("name") or ""
                input_id = input_element.get_attribute("id") or ""
                input_class = input_element.get_attribute("class") or ""
                input_placeholder = input_element.get_attribute("placeholder") or ""
                
                all_attrs = f"{input_type} {input_name} {input_id} {input_class} {input_placeholder}".lower()
                
                if ((input_type == "email" or "email" in all_attrs or "mail" in all_attrs)
                    and not any(exclude in all_attrs for exclude in ["confirm", "verify", "repeat"])):
                    email_inputs.append(input_element)
            except StaleElementReferenceException:
                continue
            except Exception as e:
                logging.debug(f"Error checking input element: {e}")
                continue

        if not email_inputs:
            logging.error(f"No email input found on {url_to_signup}")
            return "No Email Input"

        # Use the first valid email input found
        email_input = email_inputs[0]
        try:
            email_input.clear()
            email_input.send_keys(email_str)
            logging.info(f"Entered email: {email_str}")
        except Exception as e_input:
            logging.error(f"Failed to input email: {e_input}")
            return "Input Error"

        # Find and click submit buttons
        submit_buttons = []
        success_keywords = ["thank", "success", "confirm", "welcome", "subscribed", "danke", "merci", "grazie", "gracias"]

        # Various submit button finding strategies
        button_search_strategies = [
            ("button", "submit"),
            ("input", "submit"),
            ("button", None),
            ("a", None)
        ]

        for tag, type_attr in button_search_strategies:
            elements = driver.find_elements(By.TAG_NAME, tag)
            for elem in elements:
                try:
                    elem_type = elem.get_attribute("type") or ""
                    elem_text = elem.text.lower()
                    elem_value = elem.get_attribute("value") or ""
                    elem_onclick = elem.get_attribute("onclick") or ""
                    elem_class = elem.get_attribute("class") or ""
                    elem_id = elem.get_attribute("id") or ""
                    
                    all_attrs = f"{elem_type} {elem_text} {elem_value} {elem_onclick} {elem_class} {elem_id}".lower()
                    
                    if type_attr and elem_type != type_attr:
                        continue
                        
                    if any(kw in all_attrs for kw in ["submit", "subscribe", "sign up", "signup", "register", "send", "join"]):
                        if elem.is_displayed() and elem.is_enabled():
                            submit_buttons.append(elem)
                except StaleElementReferenceException:
                    continue
                except Exception as e:
                    logging.debug(f"Error checking button element: {e}")
                    continue

        if not submit_buttons:
            logging.error(f"No submit button found on {url_to_signup}")
            return "No Submit"

        # Try submitting with each found button until success
        for submit_button in submit_buttons:
            if submit_form_with_retry(forms[0] if forms else None, submit_button, page_url_before_submit, success_keywords):
                logging.info(f"Successfully submitted form on {url_to_signup}")
                return "Success"

        logging.error(f"All submit attempts failed on {url_to_signup}")
        return "Submit Failed"

    except TimeoutException:
        logging.error(f"Timeout waiting for page to load: {url_to_signup}")
        return "Timeout"
    except WebDriverException as e:
        logging.error(f"WebDriver error on {url_to_signup}: {str(e)}")
        return "WebDriver Error"
    except Exception as e:
        logging.error(f"Unexpected error on {url_to_signup}: {str(e)}")
        return "Unknown Error"

def extract_main_domain(url):
    """Extract the main domain from a URL."""
    try:
        parsed = urlparse(url)
        # Get the netloc (e.g., 'www.example.com')
        domain = parsed.netloc
        # Remove 'www.' if present
        if domain.startswith('www.'):
            domain = domain[4:]
        # Return the protocol + domain
        return f"{parsed.scheme}://{domain}"
    except Exception as e:
        logging.error(f"Error extracting main domain from {url}: {e}")
        return url

def load_websites_from_csv(csv_filename):
    websites = []
    try:
        with open(csv_filename, 'r', encoding='utf-8') as csvfile:
            csv_reader = csv.reader(csvfile)
            next(csv_reader)  # Skip header row
            for row in csv_reader:
                if row and len(row) >= 1:  # Ensure there's at least one column
                    website = row[0].strip()
                    if website and website.startswith(('http://', 'https://')):
                        # Extract and use only the main domain
                        main_domain = extract_main_domain(website)
                        websites.append(main_domain)
                    else:
                        logging.warning(f"Skipping invalid URL: {website}")
    except Exception as e:
        logging.error(f"Error loading CSV file: {e}")
        raise
    
    logging.info(f"Loaded {len(websites)} websites from CSV")
    return websites

def log_result(url, result):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILENAME, 'a', encoding='utf-8') as log_file:
        log_file.write(f"{timestamp}: {url} - {result}\n")
    
    if result == "CAPTCHA":
        with open(CAPTCHA_SITES_FILENAME, 'a', encoding='utf-8') as captcha_file:
            captcha_file.write(f"{url}\n")
    elif result != "Success":
        with open(FAULTY_SITES_FILENAME, 'a', encoding='utf-8') as faulty_file:
            faulty_file.write(f"{url} - {result}\n")

def find_imprint_link(driver):
    """Find and return the URL of the imprint page."""
    try:
        # Look for imprint links
        for keyword in IMPRINT_KEYWORDS:
            elements = driver.find_elements(By.XPATH, 
                f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}') or "
                f"contains(translate(@href, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}')]")
            
            for element in elements:
                try:
                    href = element.get_attribute('href')
                    if href:
                        return href
                except:
                    continue
        
        return None
    except Exception as e:
        logging.error(f"Error finding imprint link: {e}")
        return None

def extract_company_info(driver, website):
    """Extract company information from the imprint page."""
    company_info = {
        'Website': website,
        'Company Name': '',
        'Street Address': '',
        'ZIP': '',
        'City': '',
        'Country': '',
        'Phone': '',
        'Email': '',
        'CEO/Managing Director': '',
        'Tax ID': '',
        'Commercial Register': '',
        'Court of Registration': '',
        'Legal Representatives': '',
        'VAT ID': ''
    }
    
    try:
        # Get the page text
        page_text = driver.page_source.lower()
        text_content = driver.find_element(By.TAG_NAME, 'body').text
        
        # Extract information using regular expressions and common patterns
        
        # Company Name
        company_patterns = [
            r'(?:firma|company|gesellschaft|name):\s*([^\n]+)',
            r'(?:registered company|company name):\s*([^\n]+)'
        ]
        for pattern in company_patterns:
            match = re.search(pattern, text_content, re.I)
            if match:
                company_info['Company Name'] = match.group(1).strip()
                break
        
        # Address
        address_pattern = r'(?:address|anschrift|adresse):\s*([^\n]+(?:\n[^\n]+){0,2})'
        match = re.search(address_pattern, text_content, re.I)
        if match:
            address = match.group(1).strip()
            # Try to split address into components
            address_parts = address.split(',')
            if len(address_parts) >= 1:
                company_info['Street Address'] = address_parts[0].strip()
            if len(address_parts) >= 2:
                location = address_parts[1].strip()
                # Try to extract ZIP and City
                zip_city_match = re.search(r'(\d{4,5})\s*(.+)', location)
                if zip_city_match:
                    company_info['ZIP'] = zip_city_match.group(1)
                    company_info['City'] = zip_city_match.group(2)
        
        # Phone
        phone_pattern = r'(?:phone|tel|telefon|telephone)(?::|.{0,10}?)([+\d\s\-()\/]+)'
        match = re.search(phone_pattern, text_content, re.I)
        if match:
            company_info['Phone'] = match.group(1).strip()
        
        # Email
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        match = re.search(email_pattern, text_content)
        if match:
            company_info['Email'] = match.group(0)
        
        # CEO/Managing Director
        ceo_patterns = [
            r'(?:ceo|geschäftsführer|managing director|director):\s*([^\n]+)',
            r'vertreten durch:\s*([^\n]+)'
        ]
        for pattern in ceo_patterns:
            match = re.search(pattern, text_content, re.I)
            if match:
                company_info['CEO/Managing Director'] = match.group(1).strip()
                break
        
        # Tax ID and VAT ID
        tax_patterns = [
            r'(?:tax id|steuernummer):\s*([\w\s\-\/]+)',
            r'(?:vat id|ust-idnr|umsatzsteuer-identifikationsnummer)\.?:\s*([\w\s\-\/]+)'
        ]
        for pattern in tax_patterns:
            match = re.search(pattern, text_content, re.I)
            if match:
                if 'vat' in pattern.lower():
                    company_info['VAT ID'] = match.group(1).strip()
                else:
                    company_info['Tax ID'] = match.group(1).strip()
        
        # Commercial Register
        register_pattern = r'(?:commercial register|handelsregister|registration number):\s*([^\n]+)'
        match = re.search(register_pattern, text_content, re.I)
        if match:
            company_info['Commercial Register'] = match.group(1).strip()
        
        return company_info
        
    except Exception as e:
        logging.error(f"Error extracting company info: {e}")
        return company_info

def save_company_info(company_info):
    """Save company information to CSV file."""
    file_exists = os.path.exists(COMPANY_INFO_CSV)
    
    try:
        with open(COMPANY_INFO_CSV, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=COMPANY_INFO_HEADERS)
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow(company_info)
            
    except Exception as e:
        logging.error(f"Error saving company info to CSV: {e}")

def process_website(email, website, process_id):
    """Process a single website with its own browser instance"""
    chrome_options = setup_chrome_options(process_id)
    local_driver = None
    
    try:
        driver_service = ChromeService(ChromeDriverManager().install())
        local_driver = webdriver.Chrome(service=driver_service, options=chrome_options)
        
        try:
            # First, visit the main page
            local_driver.get(website)
            time.sleep(random.uniform(2.0, 3.0))
            
            # Look for and visit the imprint page
            imprint_url = find_imprint_link(local_driver)
            if imprint_url:
                # Convert relative URL to absolute if necessary
                if not imprint_url.startswith(('http://', 'https://')):
                    imprint_url = urljoin(website, imprint_url)
                
                # Visit the imprint page
                local_driver.get(imprint_url)
                time.sleep(random.uniform(1.5, 2.5))
                
                # Extract and save company information
                company_info = extract_company_info(local_driver, website)
                save_company_info(company_info)
                
                # Go back to main page
                local_driver.get(website)
                time.sleep(random.uniform(1.5, 2.5))
            
            # Continue with newsletter signup
            if check_for_captcha(local_driver.page_source):
                logging.warning(f"[Agent {process_id}] CAPTCHA detected on {website}")
                log_result(website, "CAPTCHA")
                return
            
            # Create a context with the local driver
            global driver
            driver = local_driver
            result = signup_to_newsletter(website, email)
            log_result(website, result)
            
        except Exception as e:
            logging.error(f"[Agent {process_id}] Error processing {website}: {str(e)}")
            log_result(website, f"Error: {str(e)}")
    
    finally:
        try:
            if local_driver:
                chrome_options = local_driver.options if hasattr(local_driver, 'options') else None
                local_driver.quit()
                if chrome_options and hasattr(chrome_options, 'profile_dir'):
                    try:
                        if os.path.exists(chrome_options.profile_dir):
                            shutil.rmtree(chrome_options.profile_dir, ignore_errors=True)
                    except Exception as e:
                        logging.debug(f"[Agent {process_id}] Error cleaning up directory {chrome_options.profile_dir}: {e}")
        except Exception as e:
            logging.error(f"[Agent {process_id}] Error during cleanup: {e}")

# --- Main Execution ---
def main():
    try:
        websites_to_process = load_websites_from_csv(CSV_FILENAME)
        email = SIGNUP_EMAIL
        
        # Calculate number of processes to use (30 or less if not enough websites)
        num_processes = min(5, len(websites_to_process))  # Reduced to 5 parallel processes
        logging.info(f"Starting {num_processes} parallel processes")
        
        # Create a pool of processes
        with Pool(processes=num_processes) as pool:
            # Create a partial function with the email parameter
            process_func = partial(process_website, email)
            
            # Map websites to processes with process IDs
            website_with_ids = [(website, i+1) for i, website in enumerate(websites_to_process)]
            
            # Execute the processing in parallel
            pool.starmap(process_func, website_with_ids)
            
    except Exception as e:
        logging.error(f"Error in main execution: {e}")
        raise

if __name__ == "__main__":
    # Configure logging to handle multiple processes
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [%(process)d] - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('debug.log'),
            logging.StreamHandler()
        ]
    )
    main()