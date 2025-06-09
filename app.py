from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import logging
import os
import threading
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('flask_app')

# Import our modularized components
try:
    from scrape import search_product
    from golden_section import run_optimization
except ImportError as e:
    logger.error(f"Failed to import required modules: {str(e)}")
    raise SystemExit("Please ensure all required modules are available")

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Add secret key for flash messages and sessions

# Enable CORS if needed
try:
    from flask_cors import CORS
    CORS(app)
    logger.info("CORS enabled")
except ImportError:
    logger.warning("flask_cors not installed, CORS disabled")

# Global storage for background tasks
tasks = {}

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')


@app.route('/optimize', methods=['POST'])
def optimize():
    """Handle optimization request"""
    try:
        # Get form data
        product_name = request.form.get('name', '')
        product_cost = int(request.form.get('cost', 0))
        max_demand = int(request.form.get('demand', 0))
        
        if not product_name:
            flash('Please enter a product name', 'error')
            return redirect(url_for('index'))
        
        # Create a unique task ID
        task_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{product_name.replace(' ', '_')}"
        
        # Start background task
        thread = threading.Thread(
            target=run_background_task,
            args=(task_id, product_name, product_cost, max_demand)
        )
        thread.daemon = True
        thread.start()
        
        # Store task info
        tasks[task_id] = {
            'status': 'running',
            'product_name': product_name,
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'result': None
        }
        
        # Redirect to status page
        return redirect(url_for('task_status', task_id=task_id))
        
    except Exception as e:
        logger.error(f"Error in optimize route: {str(e)}")
        flash(f"An error occurred: {str(e)}", 'error')
        return redirect(url_for('index'))

@app.route('/status/<task_id>')
def task_status(task_id):
    """Show task status page"""
    if task_id not in tasks:
        flash('Task not found', 'error')
        return redirect(url_for('index'))
        
    task = tasks[task_id]
    return render_template('status.html', task=task, task_id=task_id)

@app.route('/api/status/<task_id>')
def api_task_status(task_id):
    """API endpoint for checking task status"""
    if task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    # Create a safe copy of task data that can be serialized to JSON
    task_data = {
        'status': tasks[task_id].get('status', 'unknown'),
        'product_name': tasks[task_id].get('product_name', ''),
        'start_time': tasks[task_id].get('start_time', ''),
        'error': tasks[task_id].get('error', ''),
    }
    
    # Add optional fields if they exist
    if 'product_count' in tasks[task_id]:
        task_data['product_count'] = tasks[task_id]['product_count']
        
    return jsonify(task_data)

@app.route('/results/<task_id>')
def results(task_id):
    """Show optimization results"""
    if task_id not in tasks or tasks[task_id]['status'] != 'completed':
        flash('Results not available', 'error')
        return redirect(url_for('index'))
        
    return render_template('results.html', task=tasks[task_id])

def run_background_task(task_id, product_name, product_cost, max_demand):
    """Run the optimization in a background thread"""
    try:
        # Update task status
        print(f"Tasks: {tasks}")
        tasks[task_id]['status'] = 'searching'
        
        # Search for product data
        prices, ratings, scrape_data = search_product(product_name)
        
        if not prices or not ratings:
            tasks[task_id]['status'] = 'failed'
            tasks[task_id]['error'] = 'No product data found'
            return
              # Update task status
        tasks[task_id]['status'] = 'optimizing'
        tasks[task_id]['product_count'] = len(prices)
        
        # Run optimization
        results = run_optimization(
            prices, 
            cost=product_cost, 
            max_theoretical_demand=max_demand
        )
        
        if not results:
            tasks[task_id]['status'] = 'failed'
            tasks[task_id]['error'] = 'Optimization failed'
            return
            
        # Update task with results
        tasks[task_id]['status'] = 'completed'
        tasks[task_id]['result'] = results
        tasks[task_id]['scrape_data'] = scrape_data
        tasks[task_id]['completion_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in background task: {str(e)}\n{error_details}")
        
        # Ensure the task dictionary exists and is properly updated
        if task_id in tasks:
            tasks[task_id]['status'] = 'failed'
            tasks[task_id]['error'] = str(e)
        else:
            logger.error(f"Task ID {task_id} not found in tasks dictionary")

# Run the app when executed directly
if __name__ == '__main__':
    app.run(debug=True)