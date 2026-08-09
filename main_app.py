from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import uuid

app = Flask(__name__)

# Configure where to save the uploaded receipts
UPLOAD_FOLDER = 'static/receipts'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Automatically creates the folder if it doesn't exist

# Connect to Render's Database URL, or use a local SQLite database for testing
database_url = os.environ.get('DATABASE_URL', 'sqlite:///orders.db')

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

def get_ph_time():
    return datetime.utcnow() + timedelta(hours=8)

# Create the Database Model for Orders
class Order(db.Model):
    __tablename__ = 'customer_orders_v3' # Updated to V3 to add the receipt column
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(100), nullable=False)
    flavor = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    payment = db.Column(db.String(50), nullable=False)
    
    delivery_option = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(255), nullable=True)
    
    # NEW: Receipt Image Column
    receipt_image = db.Column(db.String(255), nullable=True)
    
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
    order_success = False
    customer_name = ""
    payment_method = ""
    
    if request.method == 'POST':
        customer_name = request.form.get('name')
        contact = request.form.get('contact')
        flavor = request.form.get('flavor')
        quantity = request.form.get('quantity')
        payment_method = request.form.get('payment')
        delivery_option = request.form.get('delivery_option')
        
        address = request.form.get('address') if delivery_option == 'Delivery' else 'N/A'
        
        # Handle the receipt image upload
        receipt_file = request.files.get('receipt')
        receipt_filename = "N/A"
        
        if receipt_file and receipt_file.filename != '':
            # Create a unique filename so customers don't overwrite each other's receipts
            ext = receipt_file.filename.rsplit('.', 1)[1].lower() if '.' in receipt_file.filename else 'jpg'
            receipt_filename = f"receipt_{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], receipt_filename)
            receipt_file.save(filepath)
        
        new_order = Order(
            customer_name=customer_name, 
            contact=contact, 
            flavor=flavor, 
            quantity=int(quantity), 
            payment=payment_method,
            delivery_option=delivery_option,
            address=address,
            receipt_image=receipt_filename
        )
        db.session.add(new_order)
        db.session.commit()
            
        order_success = True

    return render_template('index.html', products=PRODUCTS, order_success=order_success, name=customer_name)

@app.route('/admin')
def admin():
    all_orders = Order.query.order_by(Order.order_date.desc()).all()
    return render_template('admin.html', orders=all_orders)

@app.route('/update_status/<int:order_id>', methods=['POST'])
def update_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    order.status = new_status
    db.session.commit()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)