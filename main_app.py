from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# Connect to Render's Database URL, or use a local SQLite database for testing
database_url = os.environ.get('DATABASE_URL', 'sqlite:///orders.db')

# Fix for SQLAlchemy URI format requirements
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Create the Database Model for Orders
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(100), nullable=False)
    flavor = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    payment = db.Column(db.String(50), nullable=False)

# Product Data
PRODUCTS = [
    {
        "id": "classic",
        "name": "Classic Choco Chip",
        "price": 85,
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
        "price": 90,
        "image": "biscoff cookie.jpg",
        "desc": "Soft-baked, buttery, and packed with Biscoff."
    },
    {
        "id": "smores",
        "name": "Midnight S'mores",
        "price": 95,
        "image": "midnight s'mores.jpg",
        "desc": "Deep chocolate flavor with a molten marshmallow center."
    }
]

# Create the database tables
with app.app_context():
    db.create_all()

@app.route('/', methods=['GET', 'POST'])
def home():
    order_success = False
    customer_name = ""
    
    if request.method == 'POST':
        # Capture form data
        customer_name = request.form.get('name')
        contact = request.form.get('contact')
        flavor = request.form.get('flavor')
        quantity = request.form.get('quantity')
        payment = request.form.get('payment')
        
        # Save order directly to the database
        new_order = Order(
            customer_name=customer_name, 
            contact=contact, 
            flavor=flavor, 
            quantity=int(quantity), 
            payment=payment
        )
        db.session.add(new_order)
        db.session.commit()
            
        order_success = True

    return render_template('index.html', products=PRODUCTS, order_success=order_success, name=customer_name)

@app.route('/admin')
def admin():
    # Fetch all orders from the database
    all_orders = Order.query.all()
    return render_template('admin.html', orders=all_orders)
    
if __name__ == '__main__':
    app.run(debug=True)
