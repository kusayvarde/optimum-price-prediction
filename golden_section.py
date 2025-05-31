import numpy as np
import pandas as pd
import logging
from sklearn.linear_model import LinearRegression

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('optimization')

def get_price_range(prices):
    """
    Get minimum and maximum prices for the golden section search
    
    Args:
        prices (list): List of product prices
        
    Returns:
        tuple: (lowest_price, highest_price)
    """
    if prices:
        lowest_price = min(prices)
        highest_price = max(prices)
    else:
        lowest_price = 0
        highest_price = 1000  # Default fallback
    
    return lowest_price, highest_price

def estimate_demand_parameters(prices, ratings, max_theoretical_demand=None):
    """
    Estimate demand function parameters using linear regression
    
    Args:
        prices (list): List of product prices
        ratings (list): List of product ratings
        max_theoretical_demand (int, optional): Maximum theoretical demand at zero price
        
    Returns:
        dict: Dictionary with demand parameters and regression statistics
    """
    logger.info("Estimating demand parameters...")
    
    # Validate input data
    if not prices or not ratings:
        logger.error("Empty prices or ratings data")
        return None
        
    if len(prices) != len(ratings):
        logger.error("Prices and ratings lists have different lengths")
        return None
    
    # Create DataFrame with price and rating data
    data = pd.DataFrame({
        "price": prices,
        "rating": ratings
    })
    
    data['rating'] = data['rating'] * 100
    # Remove any rows with missing data
    data = data.dropna()
    
    if data.empty:
        logger.error("No valid data for demand estimation")
        return None
        
    # Normalize ratings to a 0-1 scale to represent demand proportion
    max_rating = data['rating'].max()
    data['demand_proportion'] = data['rating'] / max_rating

    # Estimate theoretical maximum demand (a_d) and price sensitivity (b_d)
    # Using the model: demand_proportion = 1 - (b_d/a_d) * price
    X = data[['price']]
    y = 1 - data['demand_proportion']  # Inverse of demand proportion

    try:
        # Try with intercept first for better statistical properties
        model_with_intercept = LinearRegression()
        model_with_intercept.fit(X, y)
        intercept = model_with_intercept.intercept_
        
        # If intercept is close to zero, use model without intercept
        if abs(intercept) < 0.05:
            logger.info("Intercept close to zero, using model without intercept")
            model = LinearRegression(fit_intercept=False)
        else:
            logger.info(f"Using model with intercept: {intercept:.6f}")
            model = model_with_intercept
            
        model.fit(X, y)
          # Get max_theoretical_demand from user if not provided
        if max_theoretical_demand is None:
            # Use a reasonable default if no input is available (web mode)
            max_theoretical_demand = max(100, int(len(prices) * 0.1))  # Default based on data size
            logger.info(f"Using default max theoretical demand: {max_theoretical_demand}")
            
        # Calculate a_d and b_d
        a_d = max_theoretical_demand
        
        if model.coef_[0] < 0:
            logger.warning("Negative price sensitivity detected, using absolute value")
            b_d = abs(model.coef_[0]) * max_theoretical_demand
        else:
            b_d = model.coef_[0] * max_theoretical_demand
            
        # Calculate model quality metrics
        from sklearn.metrics import r2_score
        y_pred = model.predict(X)
        r2 = r2_score(y, y_pred)
        
        logger.info(f"Estimated demand function parameters:")
        logger.info(f"a_d (Max theoretical demand): {a_d:.2f}")
        logger.info(f"b_d (Price sensitivity): {b_d:.6f}")
        logger.info(f"Model R² score: {r2:.4f}")
        
        return {
            'a_d': a_d,
            'b_d': b_d, 
            'r2': r2,
            'model': model,
            'intercept': model.intercept_ if hasattr(model, 'intercept_') else 0
        }
        
    except Exception as e:
        logger.error(f"Error in demand estimation: {str(e)}")
        return None

def get_cost():
    """Get product cost from user"""
    return int(input("Enter the product cost: "))

def talep_fonksiyonu(f, a_d, b_d):
    """
    Calculate demand at a given price
    
    Q(f) = a_d - b_d * f
    
    Args:
        f (float): Price
        a_d (float): Maximum theoretical demand at zero price
        b_d (float): Price sensitivity (demand slope)
        
    Returns:
        float: Estimated demand at price f
    """
    return max(0, a_d - b_d * f)  # Ensure demand is never negative

def kar_fonksiyonu(f, C, a_d, b_d):
    """
    Calculate profit at a given price
    
    K(f) = (f - C) * (a_d - b_d * f)
    
    Args:
        f (float): Price
        C (float): Unit cost
        a_d (float): Maximum theoretical demand at zero price
        b_d (float): Price sensitivity (demand slope)
        
    Returns:
        float: Estimated profit at price f
    """
    return (f - C) * talep_fonksiyonu(f, a_d, b_d)

def golden_section_search(func, a, b, tol=1e-3):
    """
    Golden Section Search algorithm for finding the maximum of a function
    
    Args:
        func (callable): Function to maximize
        a (float): Lower bound of search interval
        b (float): Upper bound of search interval
        tol (float): Tolerance (stopping criterion)
        
    Returns:
        tuple: (optimal_x, maximum_value, iterations)
    """
    phi = (np.sqrt(5) - 1) / 2  # Golden ratio ≈ 0.618
    iteration = 0
    a = float(a)
    b = float(b)

    # Calculate initial interior points
    x1 = b - phi * (b - a)
    x2 = a + phi * (b - a)
    f1 = func(x1)
    f2 = func(x2)

    # Iterate until interval is small enough
    while abs(b - a) > tol and iteration < 100:  # Add max iterations for safety
        iteration += 1
        if f1 > f2:
            b = x2
            x2 = x1
            f2 = f1
            x1 = b - phi * (b - a)
            f1 = func(x1)
        else:
            a = x1
            x1 = x2
            f1 = f2
            x2 = a + phi * (b - a)
            f2 = func(x2)

    # Calculate optimal price and profit
    optimal_x = (a + b) / 2
    maximum_value = func(optimal_x)
    
    return optimal_x, maximum_value, iteration


def run_optimization(prices, ratings, cost=None, max_theoretical_demand=None):
    """
    Run the complete optimization workflow
    
    Args:
        prices (list): List of product prices
        ratings (list): List of product ratings
        cost (float, optional): Product cost
        max_theoretical_demand (int, optional): Maximum theoretical demand
        
    Returns:
        dict: Results including optimal price, maximum profit, etc.
    """
    # Get price range
    lowest_price, highest_price = get_price_range(prices)
    logger.info(f"Price range: {lowest_price:.2f} - {highest_price:.2f}")
    
    # Estimate demand parameters
    params = estimate_demand_parameters(prices, ratings, max_theoretical_demand)
    if not params:
        logger.error("Failed to estimate demand parameters")
        return None
        
    a_d = params['a_d']
    b_d = params['b_d']
      # Get product cost if not provided
    if cost is None:
        # Use a reasonable default if no input is available (web mode)
        cost = min(prices) * 0.7 if prices else 10  # Default to 70% of minimum price
        logger.info(f"Using default cost: {cost:.2f}")
    
    # Define profit function for optimization
    def profit_function(price):
        return kar_fonksiyonu(price, cost, a_d, b_d)
    
    # Run golden section search
    logger.info("Running golden section search...")
    optimum_price, maximum_profit, iterations = golden_section_search(
        profit_function, lowest_price, highest_price
    )
    
    # Calculate demand at optimal price
    estimated_demand = talep_fonksiyonu(optimum_price, a_d, b_d)
    
    # Print results
    logger.info(f"Optimization complete after {iterations} iterations")
    logger.info(f"Optimum Price: {optimum_price:.2f} TL")
    logger.info(f"Maximum Profit: {maximum_profit:.2f} TL")
    logger.info(f"Estimated Demand: {estimated_demand:.2f} units")
    
    # Return results dictionary
    return {
        'optimum_price': optimum_price,
        'maximum_profit': maximum_profit,
        'estimated_demand': estimated_demand,
        'iterations': iterations,
        'demand_parameters': params,
        'price_range': (lowest_price, highest_price),
        'cost': cost
    }


# When run as a script (not imported)
if __name__ == "__main__":
    # Import data from scrape.py
    from scrape import search_product
    
    # Get product name from user
    product_name = input("Enter the product you want to search: ")
    
    # Run scraper
    prices, ratings, _ = search_product(product_name)
    
    if prices and ratings:
        # Run optimization
        results = run_optimization(prices, ratings)
        
        if results:
            # Print results
            print("\nOPTIMIZATION RESULTS")
            print("===================")
            print(f"Optimum Price: {results['optimum_price']:.2f} TL")
            print(f"Maximum Profit: {results['maximum_profit']:.2f} TL")
            print(f"Estimated Demand: {results['estimated_demand']:.2f} units")
            print(f"Total Iterations: {results['iterations']}")
    else:
        print("No data available for optimization")
