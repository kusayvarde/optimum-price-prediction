# Optimum Price Finder

This project is a web application for finding the optimum price of a product using optimization algorithms and web scraping.

## Features
- Web scraping to collect product price data
- Golden section search algorithm for price optimization
- Simple web interface for user interaction

## Project Structure
- `app.py`: Main Flask application
- `golden_section.py`: Contains the golden section search algorithm
- `scrape.py`: Handles web scraping for product prices
- `templates/`: HTML templates for the web interface
- `requirements.txt`: Python dependencies

## Installation
1. Clone the repository:
   ```sh
   git clone https://github.com/kusayvarde/optimum-price-prediction.git
   cd optimum-price-finder
   ```
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```

## Usage
1. Run the application:
   ```sh
   python app.py
   ```
2. Open your browser and go to `http://127.0.0.1:5000/`
3. Enter the product details and start the optimization process.

## Requirements
- Python 3.10+
- Flask
- BeautifulSoup4
- Requests

## License
MIT License
