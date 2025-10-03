import requests
from bs4 import BeautifulSoup, Tag
from typing import Any, Optional, List, TypedDict
import re
import asyncio
import aiohttp

class CompetitorApp(TypedDict):
    """Details of a competitor app."""
    appname: str
    appurl: str

class CompetitorAppKeywords(TypedDict):
    """Keywords of a competitor app."""
    appname: str
    keywords: List[str]

class AppDetails(TypedDict):
    """A dictionary containing the scraped app details."""
    appid: str
    appurl: str
    appname: str
    appsubtitle: str
    rating: str
    size: str
    category: str
    iphone_screenshots: List[str]
    description: str
    keywords: List[str]
    competitor_apps: List[CompetitorApp]
    competitor_apps_keywords: List[CompetitorAppKeywords]


class AppStoreScraper:
    """
    A class to scrape details of an iOS app from the Apple App Store.
    """

    def __init__(self, app_url: str, country_code: str = "us"):
        """
        Initializes the scraper with the app URL and country code.

        Args:
            app_url (str): The URL of the app on the Apple App Store.
            country_code (str): The two-character country code for the store.
        """
        self.app_url = app_url
        self.country_code = country_code.lower()
        self.url_to_scrape = self._prepare_url()

        self._stop_keywords = {
            "ios apps", "app", "appstore", "app store", "iphone", "ipad",
            "ipod touch", "itouch", "itunes", "apple"
        }

    def _get_keywords_from_soup(self, soup: BeautifulSoup) -> List[str]:
        """Extracts and filters keywords from a BeautifulSoup object."""
        keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
        keywords: List[str] = []
        if isinstance(keywords_tag, Tag):
            content = keywords_tag.get('content')
            if isinstance(content, str):
                # Split, strip whitespace, and filter out stop keywords
                all_keywords = [k.strip().lower() for k in content.split(',')]
                keywords = [
                    k for k in all_keywords if k not in self._stop_keywords
                    and k not in (self.app_name.lower(), self.app_subtitle.lower())
                ]
        return keywords

    def _prepare_url(self) -> str:
        """Prepares the URL with the correct country code."""
        # Use regex to substitute the country code, which is more robust
        # It will replace /us/ or /gb/ etc., or add it if it's missing.
        if re.search(r"\/[a-z]{2}\/", self.app_url):
            return re.sub(r"\/[a-z]{2}\/", f"/{self.country_code}/", self.app_url)
        else:
            return self.app_url.replace("apps.apple.com/", f"apps.apple.com/{self.country_code}/")

    async def _fetch_competitor_keywords(self, session: aiohttp.ClientSession, competitor: CompetitorApp, headers: dict) -> Optional[CompetitorAppKeywords]:
        """Asynchronously fetches and parses keywords for a single competitor."""
        try:
            async with session.get(competitor["appurl"], headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                html = await response.text()
                comp_soup = BeautifulSoup(html, 'html.parser')
                comp_keywords = self._get_keywords_from_soup(comp_soup)
                return {
                    "appname": competitor["appname"],
                    "keywords": comp_keywords
                }
        except Exception as e:
            print(f"Could not scrape competitor {competitor['appname']} concurrently: {e}")
            return None

    async def _scrape_competitors_concurrently(self, competitors: List[CompetitorApp], headers: dict) -> List[CompetitorAppKeywords]:
        """Orchestrates the concurrent scraping of competitor apps."""
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_competitor_keywords(session, comp, headers) for comp in competitors[:3]]
            results = await asyncio.gather(*tasks)
            return [res for res in results if res] # Filter out None results from failed scrapes

    def scrape(self) -> Optional[AppDetails]:
        """
        Scrapes the app store page and extracts details.

        Returns:
            Optional[AppDetails]: A dictionary containing app details if successful,
                                      otherwise None.
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
            }
            response = requests.get(self.url_to_scrape, headers=headers, timeout=10)
            response.raise_for_status()  # Raise an exception for bad status codes

            soup = BeautifulSoup(response.text, 'html.parser')
 
            app_name_tag = soup.find('h1', class_='product-header__title')
            self.app_name = app_name_tag.get_text(strip=True).split('\n')[0] if app_name_tag else "Not Found"

            app_subtitle_tag = soup.find('h2', class_='product-header__subtitle')
            self.app_subtitle = app_subtitle_tag.get_text(strip=True) if app_subtitle_tag else "Not Found"

            rating_tag = soup.find('span', class_='we-customer-ratings__averages__display')
            rating = rating_tag.get_text(strip=True) if rating_tag else "Not Found"

            # Find all picture tags for iPhone screenshots
            iphone_screenshot_pictures = soup.find_all('picture', class_='we-artwork--screenshot-platform-iphone')
            iphone_screenshots: List[str] = []
            for picture in iphone_screenshot_pictures:
                if isinstance(picture, Tag):
                    # Use attrs={'type': ...} to correctly find the source tag
                    source_tag = picture.find('source', attrs={'type': 'image/webp'})
                    if isinstance(source_tag, Tag):
                        srcset_val = source_tag.get('srcset')
                        if isinstance(srcset_val, str):
                            # Get the highest resolution image from srcset (usually the last one)
                            highest_res_url = srcset_val.split(',')[-1].strip().split(' ')[0]
                            iphone_screenshots.append(highest_res_url)

            # Find Size
            size = "Not Found"
            size_dt = soup.find('dt', string='Size')
            if size_dt:
                size_dd = size_dt.find_next_sibling('dd')
                if size_dd:
                    size = size_dd.get_text(strip=True)

            # Find Category
            category = "Not Found"
            category_dt = soup.find('dt', string='Category')
            if category_dt:
                category_dd = category_dt.find_next_sibling('dd')
                if category_dd:
                    category = category_dd.get_text(strip=True)

            description_tag = soup.find('div', class_='section__description')
            description = description_tag.get_text(strip=True) if description_tag else "Not Found"

            keywords = self._get_keywords_from_soup(soup)

            # Find "You Might Also Like" section and extract competitor apps
            competitor_apps: List[CompetitorApp] = []
            you_might_also_like_header = soup.find('h2', string=re.compile(r'You Might Also Like'))
            if you_might_also_like_header:
                # Find the parent section of the header
                parent_section = you_might_also_like_header.find_parent('section')
                if isinstance(parent_section, Tag):
                    # Find all competitor app lockups within that section
                    competitor_lockups = parent_section.find_all('a', class_='we-lockup')
                    for lockup in competitor_lockups:
                        if isinstance(lockup, Tag):
                            name_tag = lockup.select_one('.we-lockup__title p')
                            competitor_name = name_tag.get_text(strip=True) if name_tag else "Not Found"
                            competitor_url_val = lockup.get('href')
                            if competitor_name != "Not Found" and isinstance(competitor_url_val, str):
                                competitor_url = competitor_url_val
                                competitor_apps.append({"appname": competitor_name, "appurl": competitor_url})

            # Scrape keywords for the top 3 competitor apps
            # Asynchronously scrape competitor keywords for better performance
            competitor_apps_keywords = asyncio.run(self._scrape_competitors_concurrently(competitor_apps, headers))
            appid_match = re.search(r'id(\d+)', self.url_to_scrape)
            appid = appid_match.group(1) if appid_match else "unknown_id"

            return {
                "appid": appid,
                "appurl": self.url_to_scrape,
                "appname": self.app_name,
                "appsubtitle": self.app_subtitle,
                "rating": rating,
                "size": size,
                "category": category,
                "iphone_screenshots": iphone_screenshots,
                "description": description,
                "keywords": keywords,
                "competitor_apps": competitor_apps,
                "competitor_apps_keywords": competitor_apps_keywords
            }

        except requests.exceptions.RequestException as e:
            print(f"Error fetching URL {self.url_to_scrape}: {e}")
            return None
        except Exception as e:
            print(f"An error occurred during scraping: {e}")
            return None