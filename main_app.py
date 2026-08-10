from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from functools import wraps
import os
import csv
import io

app = Flask(__name__)

# Secret key for sessions
app.secret_key = os.environ.get('SECRET_KEY', 'baked-and-beyond-secret-key-2026')

# Connect to Render's Database URL, or use a local SQLite database for testing
database_url = os.environ.get('DATABASE_URL', 'sqlite:///orders.db')

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Admin credentials
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'buildingg512'

def get_ph_time():
    return datetime.utcnow() + timedelta(hours=8)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Create the Database Model for Orders
class Order(db.Model):
    __tablename__ = 'customer_orders_v5' # V5 upgrades to a shopping cart system
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(100), nullable=False)
    
    # NEW: Replaced single flavor/quantity with a full cart string and total cost
    order_details = db.Column(db.Text, nullable=False)
    total_cost = db.Column(db.Integer, nullable=False)
    
    payment = db.Column(db.String(50), nullable=False)
    delivery_option = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(255), nullable=True)
    reference_number = db.Column(db.String(100), nullable=True)
    
    status = db.Column(db.String(50), default="Pending")
    order_date = db.Column(db.DateTime, default=get_ph_time)

PRODUCTS = [
    {
        "id": "classic",
        "name": "Classic Choco Chip",
        "price": 90,
        "image": "classic choco chip.jpg",
        "desc": "Simple, classic, and irresistible."
    },
    {
        "id": "double",
        "name": "Double Choco Cookie",
        "price": 90,
        "image": "double choco cookie.jpg",
        "desc": "Made with rich cocoa and premium chocolate chips."
    },
    {
        "id": "biscoff",
        "name": "Biscoff Cookie",
        "price": 95,
        "image": "biscoff cookie.jpg",
        "desc": "Soft-baked, buttery, and packed with Biscoff."
    },
    {
        "id": "smores",
        "name": "Midnight S'mores",
        "price": 95,
        "image": "midnight s'mores.jpg",
        "desc": "Deep chocolate flavor with a molten marshmallow center."
    },
    {
        "id": "promo",
        "name": "Promo: Get All Four",
        "price": 359,
        "original_price": 370,
        "image": "promo for one.jpg",
        "desc": "Get all four and save 11 pesos!"
    }
]

with app.app_context():
    db.create_all()

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        customer_name = request.form.get('name')
        contact = request.form.get('contact')
        
        # Capture the hidden cart details
        order_details = request.form.get('order_details')
        total_cost = request.form.get('total_cost')
        
        payment_method = request.form.get('payment')
        delivery_option = request.form.get('delivery_option')
        address = request.form.get('address') if delivery_option == 'Delivery' else 'N/A'
        reference_number = request.form.get('reference_number', 'N/A')
        
        new_order = Order(
            customer_name=customer_name, 
            contact=contact, 
            order_details=order_details, 
            total_cost=int(total_cost), 
            payment=payment_method,
            delivery_option=delivery_option,
            address=address,
            reference_number=reference_number
        )
        db.session.add(new_order)
        db.session.commit()
        
        # PRG pattern: redirect after POST to prevent duplicate orders on refresh
        return redirect(url_for('home', order_id=new_order.id, name=customer_name))

    # GET request: check if we just came from a successful order submission
    order_id = request.args.get('order_id')
    customer_name = request.args.get('name', '')
    order_success = order_id is not None
    last_order_id = int(order_id) if order_id else None

    return render_template('index.html', products=PRODUCTS, order_success=order_success, name=customer_name, last_order_id=last_order_id)

@app.route('/track', methods=['GET', 'POST'])
def track():
    orders = []
    searched = False
    query = ""
    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        searched = True
        if query:
            orders = Order.query.filter(
                (Order.customer_name.ilike(f'%{query}%')) |
                (Order.contact.ilike(f'%{query}%'))
            ).order_by(Order.order_date.desc()).limit(10).all()
    return render_template('track.html', orders=orders, searched=searched, query=query)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            error = 'Incorrect username or password. Please try again.'
    return render_template('login.html', error=error)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
@login_required
def admin():
    all_orders = Order.query.order_by(Order.order_date.desc()).all()
    return render_template('admin.html', orders=all_orders)

@app.route('/update_status/<int:order_id>', methods=['POST'])
@login_required
def update_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    order.status = new_status
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/export-csv')
@login_required
def export_csv():
    """Download all orders as a CSV backup file."""
    all_orders = Order.query.order_by(Order.order_date.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        'ID', 'Date & Time (PH)', 'Customer Name', 'Contact',
        'Delivery Option', 'Address', 'Order Details',
        'Total (PHP)', 'Payment', 'Reference Number', 'Status'
    ])

    # Data rows
    for o in all_orders:
        writer.writerow([
            o.id,
            o.order_date.strftime('%Y-%m-%d %H:%M'),
            o.customer_name,
            o.contact,
            o.delivery_option,
            o.address or 'N/A',
            o.order_details,
            o.total_cost,
            o.payment,
            o.reference_number or 'N/A',
            o.status
        ])

    output.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f'baked_and_beyond_orders_{timestamp}.csv'

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

if __name__ == '__main__':
    app.run(debug=True)