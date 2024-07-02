import logging
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

logger = logging.getLogger()
logger.setLevel("INFO")


class Cookie:
    """
    Class for identifying cookie buttons and clicking on them. Searches for the buttons, by going through a list of
    possible XPATHs, which are saved in utils/keywords. Once a matching path has been found,
    the browser navigates to the button and clicks it.

    Please note that if no XPATH on the list matches the path on a specific file, then it has to be manually added to
    the file, containing saids paths.

    If no match is found, we wait 3 seconds and then proceed to scrape.
    The idea is to avoid scraping cookie-related policy text, if possible. If any text DOES manage to be scraped,
    then we have fault tolerance for this, but is still best to increase speed of scraping and exclude unwanted text.
    """
    def __init__(self, driver):
        self.pop_up_found = None    # Flag to indicate if a cookie pop-up was found.
        self.pop_up_clicked = None  # Flag to indicate if a cookie pop-up was successfully clicked.
        self.driver = driver

        # Read the XPath selectors from a file.
        with open('utils/xpaths.txt', 'r') as file:
            self.xpaths = file.read().splitlines()

    def click_accept_cookies(self):

        # Join the selectors with ' | ' to create the final XPath expression.
        xpath_selectors = ' | '.join(self.xpaths)

        try:
            # Wait for any of the elements to be visible and get the first one available.
            cookie_button = WebDriverWait(self.driver, 3).until(
                ec.visibility_of_any_elements_located((By.XPATH, xpath_selectors))
            )[0]
            self.pop_up_found = True    # Raise flag if pop-up was found.
            self.driver.execute_script("arguments[0].click();", cookie_button)
            self.pop_up_clicked = True  # Raise flag if pop-up was clicked.
            logger.info("Cookie pop-up was successfully clicked.")
            return True
        except TimeoutException:
            # If no element is found, assume no pop-up.
            logger.info("No cookie pop-up was found.")
            return False
