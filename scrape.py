import cloudscraper
from bs4 import BeautifulSoup
import time
import numpy as np
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('product_scraper')

# Constants
BASE_URL = "https://www.n11.com/arama?q="
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
}
MAX_PAGES = 25
REQUEST_DELAY = 3  # seconds between requests

# Initialize scraper
scraper = cloudscraper.create_scraper()  # handles Cloudflare

def get_search_url(product_name, sort_by="REVIEWS", page=1):
    """
    Generate a search URL for N11.com
    
    Args:
        product_name (str): Product to search for
        sort_by (str): Sorting method (REVIEWS, PRICE_LOW, etc)
        page (int): Page number
        
    Returns:
        str: Formatted search URL
    """
    query = product_name.replace(" ", "+")
    return f"{BASE_URL}{query}&srt={sort_by}&pg={page}"
    
def search_product(product_name=None):
    """
    Main function to search for a product
    
    Args:
        product_name (str, optional): Product to search for. If None, will prompt user.
        
    Returns:
        tuple: (prices, ratings) lists with product data
    """
    # Get product name from input if not provided
    if product_name is None:
        product_name = input("Enter the product you want to search: ")
        
    # Generate initial search URL
    url = get_search_url(product_name)    # Get first page
    logger.info(f"Searching for '{product_name}' on N11.com")
    pro = []
    page = 1
    
    try:
        # Get first page
        response = scraper.get(url, headers=DEFAULT_HEADERS)
        time.sleep(REQUEST_DELAY)
        
        # Parse initial page
        soup = BeautifulSoup(response.text, "html.parser")
        pro = soup.find_all(class_="pro")
        
        # Paginate through results
        page = 2
        while not soup.find(class_="noResultHolders"):
            logger.info(f"Fetching page {page}...")
            next_url = get_search_url(product_name, page=page)
            
            try:
                response = scraper.get(next_url, headers=DEFAULT_HEADERS)
                time.sleep(REQUEST_DELAY)
                
                soup = BeautifulSoup(response.text, "html.parser")
                new_products = soup.find_all(class_="pro")
                
                # If no new products found, break
                if not new_products:
                    logger.info("No more products found")
                    break
                    
                pro += new_products
                page += 1
                
                # Safety limit
                if page > MAX_PAGES:
                    logger.warning(f"Reached maximum page limit ({MAX_PAGES})")
                    break
            except Exception as e:
                logger.error(f"Error fetching page {page}: {str(e)}")
                break
                
        logger.info(f"Successfully fetched {page-1} pages with {len(pro)} products")
        
        # Extract ratings and prices with error handling
        logger.info("Extracting product data...")
        ratings = []
        prices = []
        
        for product in pro:
            try:
                # Extract rating
                rating_element = product.find(class_="ratingText")
                if rating_element and rating_element.text:
                    rating_text = rating_element.text.strip()
                    rating = float(rating_text.replace("(", "").replace(")", "").replace(",", ""))
                    ratings.append(rating)
                else:
                    ratings.append(0)
                    
                # Extract price
                price_element = product.find("ins")
                if price_element and price_element.text:
                    price_text = price_element.text.strip()
                    price = float(price_text.replace(" TL", "").replace(".", "").replace(",", "."))
                    prices.append(price)
            except Exception as e:
                logger.warning(f"Error extracting product data: {str(e)}")
        
        # Calculate mean rating for missing values
        valid_ratings = [r for r in ratings if r > 0]
        mean_rating = np.mean(valid_ratings) if valid_ratings else 0
        logger.info(f"Mean rating: {mean_rating:.2f}")
        
        # Replace missing ratings with mean
        people_rate = [rating if rating > 0 else mean_rating for rating in ratings]
        
        # Log summary
        logger.info(f"Number of ratings found: {len(ratings)}")
        logger.info(f"Number of prices found: {len(prices)}")
        
        # Create data dictionary for easier access
        data = {
            'prices': prices,
            'ratings': people_rate,
            'page_count': page-1,
            'product_count': len(pro),
            'mean_rating': mean_rating
        }
        
        return prices, people_rate, data        
    except Exception as e:
        logger.error(f"Error during product search: {str(e)}")
        return [], [], {'prices': [], 'ratings': [], 'page_count': 0, 'product_count': 0, 'mean_rating': 0}


def print_results(prices, ratings):
    """Print the results of a product search"""
    print(f"Number of ratings found: {len(ratings)}")
    print(f"Number of prices found: {len(prices)}")
    
    if prices and ratings:
        print(f"Mean rating: {np.mean([r for r in ratings if r > 0]):.2f}")
        print("\nSample of product data:")
        for price, rating in list(zip(prices, ratings))[:10]:  # Print first 10 items
            print(f"Price: {price}, Rating: {rating}")
        
        if len(prices) > 10:
            print("... (showing first 10 items only)")
    else:
        print("No product data found")


# When run as a script (not imported)
if __name__ == "__main__":
    product_name = input("Enter the product you want to search: ")
    prices, people_rate, data = search_product(product_name)
    print_results(prices, people_rate)
