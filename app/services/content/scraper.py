"""Web scraper for real estate data using Selenium."""

from dataclasses import dataclass

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from app.config import settings


@dataclass
class ScrapedProperty:
    """Scraped property data."""

    name: str
    address: str
    price: str | None = None
    area: str | None = None
    description: str | None = None
    features: list[str] | None = None
    images: list[str] | None = None


class RealEstateScraper:
    """Scraper for real estate websites."""

    def __init__(self):
        self.driver: webdriver.Chrome | None = None
        self.timeout = settings.selenium_timeout

    def _get_driver(self) -> webdriver.Chrome:
        """Create and return Chrome WebDriver."""
        options = Options()
        if settings.selenium_headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    def __enter__(self) -> "RealEstateScraper":
        """Context manager entry."""
        self.driver = self._get_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        if self.driver:
            self.driver.quit()

    async def scrape_naver_real_estate(self, location: str) -> list[ScrapedProperty]:
        """Scrape Naver Real Estate listings."""
        properties = []

        with self as scraper:
            driver = scraper.driver
            if not driver:
                return properties

            try:
                # Navigate to Naver Real Estate
                url = f"https://land.naver.com/search/search.naver?query={location}"
                driver.get(url)

                # Wait for listings to load
                WebDriverWait(driver, self.timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".search_result"))
                )

                # Find property listings
                listings = driver.find_elements(By.CSS_SELECTOR, ".search_item")

                for listing in listings[:10]:  # Limit to 10 results
                    try:
                        name = listing.find_element(By.CSS_SELECTOR, ".name").text
                        address = listing.find_element(By.CSS_SELECTOR, ".address").text

                        price_elem = listing.find_elements(By.CSS_SELECTOR, ".price")
                        price = price_elem[0].text if price_elem else None

                        properties.append(
                            ScrapedProperty(
                                name=name,
                                address=address,
                                price=price,
                            )
                        )
                    except Exception:
                        continue

            except Exception as e:
                print(f"Scraping error: {e}")

        return properties

    async def scrape_zigbang(self, location: str) -> list[ScrapedProperty]:
        """Scrape Zigbang listings."""
        properties = []

        with self as scraper:
            driver = scraper.driver
            if not driver:
                return properties

            try:
                url = f"https://www.zigbang.com/home/search?keyword={location}"
                driver.get(url)

                WebDriverWait(driver, self.timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid]"))
                )

                # Extract listings
                listings = driver.find_elements(By.CSS_SELECTOR, "[data-testid='item']")

                for listing in listings[:10]:
                    try:
                        name = listing.find_element(By.CSS_SELECTOR, "[data-testid='title']").text
                        price = listing.find_element(By.CSS_SELECTOR, "[data-testid='price']").text

                        properties.append(
                            ScrapedProperty(
                                name=name,
                                address=location,
                                price=price,
                            )
                        )
                    except Exception:
                        continue

            except Exception as e:
                print(f"Zigbang scraping error: {e}")

        return properties

    async def get_neighborhood_info(self, location: str) -> dict:
        """Get neighborhood information for a location."""
        info = {
            "location": location,
            "amenities": [],
            "transportation": [],
            "schools": [],
            "restaurants": [],
        }

        with self as scraper:
            driver = scraper.driver
            if not driver:
                return info

            try:
                # Search for neighborhood info on Naver Maps
                url = f"https://map.naver.com/?q={location}"
                driver.get(url)

                WebDriverWait(driver, self.timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#info"))
                )

                # Extract nearby places
                categories = ["편의점", "지하철", "학교", "음식점"]
                for category in categories:
                    search_input = driver.find_element(By.CSS_SELECTOR, "#search.keyword")
                    search_input.clear()
                    search_input.send_keys(f"{location} {category}")
                    search_input.submit()

                    # Wait and extract results
                    # (simplified - actual implementation would be more robust)

            except Exception as e:
                print(f"Neighborhood info error: {e}")

        return info
