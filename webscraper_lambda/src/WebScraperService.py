import re
import logging
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import Remote, ChromeOptions
from selenium.webdriver.chromium.remote_connection import ChromiumRemoteConnection
from tempfile import mkdtemp

from starlette.exceptions import HTTPException

from CookieClicker import Cookie

# Setting up logging.
logger = logging.getLogger()
logger.setLevel("INFO")


# TODO: Cost monitoring is not functioning, ask Bright Data to elaborate on how to monitor costs.
#  Docs: https://docs.brightdata.com/general/usage-monitoring/bandwidth#how-to-get-bandwidth-and-total-cost-for-a-zone
def monitor_bandwith_and_costs() -> None:
    import requests
    headers = {"Authorization": "812cb69c-80ca-46cd-b626-c6f3c9aa87f6"}
    r = requests.get('https://api.brightdata.com/zone/cost?zone=scraping_browser1', headers=headers)
    logger.info(r.content)


class WebScraper:
    """
    Class for handling web driver and scraping text from a given URL.
    """
    def __init__(self, proxy: bool, monitor: bool, url: str):

        self.use_proxy = proxy
        self.monitor_bandwith_an_costs = monitor
        self.url = url

        options = webdriver.ChromeOptions()
        service = webdriver.ChromeService('/opt/chromedriver')

        options.binary_location = '/opt/chrome/chrome'                      # Define path for chrome binaries.
        options.add_argument('--disable-javascript')                        # Disabling Javascript.
        options.add_argument('--disable-extensions')                        # Disabling extenisons.
        options.add_argument('--single-process')                            # Make chrome run on single a process.
        options.add_argument('--disable-dev-shm-usage')                     # Disabling shm partition.
        options.add_argument('--disable-dev-tools')                         # Disabling development tools.
        options.add_argument('--no-zygote')                                 # Disabling Zygote, so no zombie processes.
        options.add_argument('--no-sandbox')                                # Disabling sandbox.
        options.add_argument('--disable-gpu')                               # Disabling GPU.
        options.add_argument('--log-level=3')                               # Define log-level.
        options.add_argument(f'user-data-dir={mkdtemp()}')                  # Define user-data to tmp folder.
        options.add_argument(f'--data-path={mkdtemp()}')                    # Define data-path to tmp folder.
        options.add_argument(f'--disk-cache-dir={mkdtemp()}')               # Define disk cache to tmp folder.
        options.page_load_strategy = 'normal'                               # Define loading strategy.
        options.add_argument('--headless=new')                              # Enabling headless mode.

        if self.use_proxy:
            logger.info("Proxy is enabled! Browsing with Bright Data's proxies.")

            auth = 'brd-customer-hl_9d0fdce4-zone-scraping_browser1:ro3wfgi2a2fg'
            sbr_webdriver = f'https://{auth}@brd.superproxy.io:9515'
            sbr_connection = ChromiumRemoteConnection(sbr_webdriver, 'goog', 'chrome')
            prefs = {"profile.managed_default_content_settings.images": 2}  # Disable images.
            options.add_experimental_option("prefs", prefs)  # Add preferences.

            self.driver = Remote(sbr_connection, options=ChromeOptions())
        else:
            logger.info("Proxy is disabled. Proceeding without proxies.")
            self.driver = webdriver.Chrome(options=options, service=service)  # Instantiating driver.

        self.cookie = Cookie(self.driver)                                   # Instantiating CookieClicker. Delicious!

        with open('utils/keywords.txt', 'r') as file:
            self.keywords = file.read().splitlines()

    def extract_text(self) -> str:
        """
        Method for extracting text from a given URL. Returns the title and text of the page as strings.
        :return: Title and text of the page.
        """

        self.driver.get(self.url)

        flag1 = time.perf_counter()

        logger.info("Established connection to " + self.url)

        # Wait for the page to load.
        self.driver.implicitly_wait(5)

        # Click on cookie pop-up, if any is present. Returns False if no cookie pop-ups is found. True otherwise.
        self.cookie.click_accept_cookies()

        logger.info("Cookies done, brewing soup.")
        soup = BeautifulSoup(self.driver.page_source, "html.parser")  # mmmmm... good soup.

        # Regex pattern. Iterate over keywords and escape any matches.
        keywords_pattern = re.compile('|'.join(map(re.escape, self.keywords)), re.IGNORECASE)

        # Load all 'p' tags into 'items' variable.
        items = soup.find_all('p')
        title = soup.title.get_text()

        # Variable that will contain the text reveleant text from our page.
        page_text = ""

        # TODO: Filter out any cases of too many whitespaces or formatting keys, such as \t or \n.
        #  Appears when scraping e.g https://podimo.com/dk and https://www.telenor.dk
        # Filter out any cookie related text and save it to page_text
        for item in items:
            item_text = item.get_text()
            if not keywords_pattern.search(item_text):  # Check if the paragraph does not contain any of the keywords.
                page_text += f" {item_text}"            # Append text to saved text.

        request_reject = ['request rejected', 'just a moment...', 'access denied', 'et øjeblik']

        logger.info(f"Page content is: {title + page_text}")

        logger.info("Checking for any access issues.")

        """Sometimes, the website will reject our request, but still send a statuscode of 200. So we end up scraping
        a page with an error message. We check for these messages and retry with a proxy if any are found."""
        if any(error_message in title.lower() + ' ' + page_text.lower() for error_message in request_reject):
            if not self.use_proxy:
                logger.info("Scraping was rejected. Retrying with proxy.")
                self.use_proxy = True
                self.driver.quit()
                return WebScraper(proxy=True, url=self.url, monitor=False).extract_text()
            elif self.use_proxy:
                logger.info("blyat")
                raise HTTPException(403, f"Access to {self.url} is blocked.")
        logger.info("Access granted. Scraping complete.")

        self.driver.quit()

        flag2 = time.perf_counter()
        if self.monitor_bandwith_an_costs:
            monitor_bandwith_and_costs()

        logger.info(f"Page content is: {title + page_text}")
        logger.info(self.url + f" was scraped in {flag2 - flag1:.2f} seconds.")      # Log performance.
        logger.debug(title + "\n" + page_text + "\n")

        return title + page_text
