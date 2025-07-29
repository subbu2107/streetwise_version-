from flask import Flask, render_template, request, redirect, session
import sqlite3, os, requests, math
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'secret'
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# -------- FIXED: Use absolute path for database --------
# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'app.db')

def get_db_connection():
    """Helper function to get database connection with consistent path"""
    return sqlite3.connect(DATABASE_PATH)

# -------- DB Setup --------
def init_db():
    conn = get_db_connection()  # Use the helper function
    c = conn.cursor()
    
    # Check if tables already exist to avoid recreating
    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
    existing_tables = [row[0] for row in c.fetchall()]
    
    print(f"Database location: {DATABASE_PATH}")
    print(f"Existing tables: {existing_tables}")
    
    # Only create tables if they don't exist
    if 'vendors' not in existing_tables:
        c.execute('''CREATE TABLE vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            password TEXT,
            street TEXT,
            city TEXT,
            state TEXT,
            location TEXT)''')
        print("Created vendors table")
    
    if 'suppliers' not in existing_tables:
        c.execute('''CREATE TABLE suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            password TEXT,
            street TEXT,
            city TEXT,
            state TEXT,
            location TEXT)''')
        print("Created suppliers table")
    
    if 'products' not in existing_tables:
        c.execute('''CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier TEXT,
            name TEXT,
            description TEXT,
            price REAL,
            quantity INTEGER,
            image TEXT)''')
        print("Created products table")
    
    if 'messages' not in existing_tables:
        c.execute('''CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            receiver TEXT,
            product_id INTEGER,
            message TEXT,
            timestamp TEXT)''')
        print("Created messages table")
    
    if 'orders' not in existing_tables:
        c.execute('''CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor TEXT,
            supplier TEXT,
            product_id INTEGER,
            quantity INTEGER,
            status TEXT)''')
        print("Created orders table")
    
    if 'reviews' not in existing_tables:
        c.execute('''CREATE TABLE reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            reviewer TEXT,
            rating INTEGER,
            review_text TEXT)''')
        print("Created reviews table")
    
    if 'supplier_reviews' not in existing_tables:
        c.execute('''CREATE TABLE supplier_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_name TEXT,
            reviewer TEXT,
            rating INTEGER,
            review_text TEXT)''')
        print("Created supplier_reviews table")
    
    conn.commit()
    conn.close()

# -------- Utilities --------
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(float, (lat1, lon1, lat2, lon2))
    dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    F = R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return F*(1+0.30)

def convert_coords(coord_str):
    try:
        lat_str, lon_str = coord_str.strip().split(',')

        def parse(coord):
            coord = coord.strip()
            value = float(coord[:-2].strip('° '))
            direction = coord[-1].upper()
            if direction in ['S', 'W']:
                value = -value
            return value

        lat = parse(lat_str)
        lon = parse(lon_str)
        return f"{lat},{lon}"
    except:
        return coord_str  # fallback to original if parse fails

# -------- Routes --------
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name, password, role = request.form['name'], request.form['password'], request.form['role']
        table = 'vendors' if role == 'vendor' else 'suppliers'
        conn = get_db_connection()  # Use helper function
        c = conn.cursor()
        c.execute(f"SELECT * FROM {table} WHERE name=? AND password=?", (name, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['name'], session['role'] = name, role
            return redirect(f'/dashboard/{role}')
        else:
            # Redirect to homepage if invalid
            return redirect('/')
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.form
    name, password, role = data['name'], data['password'], data['role']
    street, city, state = data['street'], data['city'], data['state']
    coords = data.get('coordinates', '')
    location = convert_coords(coords) if ',' in coords else ""
    table = 'vendors' if role == 'vendor' else 'suppliers'
    conn = get_db_connection()  # Use helper function
    c = conn.cursor()
    c.execute(f"SELECT * FROM {table} WHERE name=?", (name,))
    if c.fetchone():
        return render_template('login.html', error="Username already exists")
    c.execute(f"INSERT INTO {table} (name, password, street, city, state, location) VALUES (?, ?, ?, ?, ?, ?)",
              (name, password, street, city, state, location))
    conn.commit()
    conn.close()
    session['name'], session['role'] = name, role
    return redirect(f'/dashboard/{role}')

@app.route('/dashboard/vendor')
def dashboard_vendor():
    if session.get('role') != 'vendor':
        return redirect('/')

    conn = get_db_connection()  # Use helper function
    c = conn.cursor()

    # Get vendor location
    c.execute("SELECT location FROM vendors WHERE name=?", (session['name'],))
    vendor_loc = c.fetchone()[0]
    vlat, vlon = vendor_loc.split(',') if vendor_loc else (None, None)

    # Get all products (with optional search)
    query = request.args.get('search', '')
    if query:
        c.execute("SELECT * FROM products WHERE name LIKE ?", (f'%{query}%',))
    else:
        c.execute("SELECT * FROM products")
    products = c.fetchall()

    # Get all reviews
    c.execute("SELECT product_id, rating FROM reviews")
    all_reviews = c.fetchall()

    # Prepare enriched product list with distance
    enriched = []
    for p in products:
        pid, supplier, name, desc, price, qty, image = p
        c.execute("SELECT location FROM suppliers WHERE name=?", (supplier,))
        loc = c.fetchone()
        dist = None
        if loc and vlat and vlon:
            slat, slon = loc[0].split(',')
            dist = round(haversine_distance(vlat, vlon, slat, slon), 2)
        enriched.append((pid, supplier, name, desc, price, qty, image, dist))

    # Sort by proximity
    enriched.sort(key=lambda x: x[7] if x[7] is not None else float('inf'))

    # Get orders for this vendor
    c.execute("""
        SELECT o.id, o.product_id, o.quantity, o.status, p.name 
        FROM orders o 
        JOIN products p ON o.product_id = p.id 
        WHERE o.vendor=?
    """, (session['name'],))
    my_orders = c.fetchall()

    conn.close()

    return render_template('dashboard_vendor.html',
                           name=session['name'],
                           products=enriched,
                           my_orders=my_orders,
                           reviews=all_reviews)

@app.route('/dashboard/supplier', methods=['GET', 'POST'])
def dashboard_supplier():
    if session.get('role') != 'supplier':
        return redirect('/')

    conn = get_db_connection()  # Use helper function
    c = conn.cursor()
    
    # Handle new product POST
    if request.method == 'POST' and 'product_name' in request.form:
        try:
            pname = request.form['product_name']
            desc = request.form.get('description', '')
            price = float(request.form['price'])
            qty = int(request.form['quantity'])
            image = request.files['image']
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            c.execute("INSERT INTO products (supplier, name, description, price, quantity, image) VALUES (?, ?, ?, ?, ?, ?)",
                      (session['name'], pname, desc, price, qty, filename))
            conn.commit()
        except Exception as e:
            print("Error while adding product:", e)

    # Load products by this supplier
    c.execute("SELECT * FROM products WHERE supplier=?", (session['name'],))
    products = c.fetchall()

    # Load pending orders
    c.execute("SELECT * FROM orders WHERE supplier=? AND status='pending'", (session['name'],))
    pending_orders_raw = c.fetchall()
    pending = []
    for o in pending_orders_raw:
        try:
            pid_name = c.execute("SELECT name FROM products WHERE id=?", (o[3],)).fetchone()
            pname = pid_name[0] if pid_name else "Unknown"
            pending.append((o[0], o[1], o[3], o[4], pname))
        except Exception as e:
            print("Pending order load error:", e)

    # Load completed orders
    c.execute("SELECT * FROM orders WHERE supplier=? AND status='accepted'", (session['name'],))
    completed = c.fetchall()

    # Chat list
    c.execute("SELECT DISTINCT sender, product_id FROM messages WHERE receiver=?", (session['name'],))
    chats = c.fetchall()
    chat_lookup = {}
    for sender, pid in chats:
        pname = c.execute("SELECT name FROM products WHERE id=?", (pid,)).fetchone()
        if pname:
            chat_lookup[(sender, pid)] = pname[0]
            
    # Compute average rating for all products by this supplier
    avg_rating = None
    if products:
        product_ids = [str(p[0]) for p in products]
        placeholders = ','.join(['?'] * len(product_ids))
        c.execute(f"SELECT rating FROM reviews WHERE product_id IN ({placeholders})", product_ids)
        ratings = [r[0] for r in c.fetchall()]
        if ratings:
            avg_rating = round(sum(ratings) / len(ratings), 1)

    conn.close()

    return render_template('dashboard_supplier.html',
                            name=session['name'],
                            products=products,
                            pending_orders=pending,
                            completed_orders=completed,
                            chat_lookup=chat_lookup,
                            avg_rating=avg_rating)

@app.route('/order/<int:product_id>', methods=['POST'])
def place_order(product_id):
    if session.get('role') != 'vendor':
        return redirect('/')
    qty = int(request.form['quantity'])
    conn = get_db_connection()  # Use helper function
    c = conn.cursor()
    c.execute("SELECT supplier, quantity FROM products WHERE id=?", (product_id,))
    row = c.fetchone()
    if not row or qty > row[1]:
        conn.close()
        return "Invalid order"
    c.execute("INSERT INTO orders (vendor, supplier, product_id, quantity, status) VALUES (?, ?, ?, ?, 'pending')",
              (session['name'], row[0], product_id, qty))
    conn.commit()
    conn.close()
    return redirect('/dashboard/vendor')

@app.route('/accept_order/<int:order_id>', methods=['POST'])
def accept_order(order_id):
    conn = get_db_connection()  # Use helper function
    c = conn.cursor()
    c.execute("SELECT product_id, quantity FROM orders WHERE id=?", (order_id,))
    pid, qty = c.fetchone()
    c.execute("SELECT quantity FROM products WHERE id=?", (pid,))
    cur_qty = c.fetchone()[0]
    if qty > cur_qty:
        return "Not enough stock"
    if qty == cur_qty:
        c.execute("DELETE FROM products WHERE id=?", (pid,))
    else:
        c.execute("UPDATE products SET quantity=? WHERE id=?", (cur_qty - qty, pid))
    c.execute("UPDATE orders SET status='accepted' WHERE id=?", (order_id,))
    conn.commit()
    conn.close()
    return redirect('/dashboard/supplier')

@app.route('/reject_order/<int:order_id>', methods=['POST'])
def reject_order(order_id):
    conn = get_db_connection()  # Use helper function
    c = conn.cursor()
    c.execute("UPDATE orders SET status='rejected' WHERE id=?", (order_id,))
    conn.commit()
    conn.close()
    return redirect('/dashboard/supplier')

@app.route('/chat/<user>/<int:product_id>', methods=['GET', 'POST'])
def chat(user, product_id):
    if 'name' not in session:
        return redirect('/')
    conn = get_db_connection()  # Use helper function
    c = conn.cursor()
    if request.method == 'POST':
        msg = request.form['message']
        c.execute("INSERT INTO messages (sender, receiver, product_id, message, timestamp) VALUES (?, ?, ?, ?, ?)",
                  (session['name'], user, product_id, msg, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
    c.execute("SELECT sender, message, timestamp FROM messages WHERE product_id=? AND ((sender=? AND receiver=?) OR (sender=? AND receiver=?)) ORDER BY id",
              (product_id, session['name'], user, user, session['name']))
    messages = c.fetchall()
    pname = c.execute("SELECT name FROM products WHERE id=?", (product_id,)).fetchone()
    conn.close()
    return render_template("chat.html", messages=messages, user=user, product_name=pname[0] if pname else "Unknown")

@app.route('/product/<int:product_id>', methods=['GET', 'POST'])
def product_detail(product_id):
    if 'name' not in session:
        return redirect('/')

    conn = get_db_connection()  # Use helper function
    c = conn.cursor()

    # Fetch product
    c.execute("SELECT * FROM products WHERE id=?", (product_id,))
    product = c.fetchone()
    if not product:
        conn.close()
        return "Product not found", 404

    # Distance calculation
    distance = None
    try:
        if session['role'] == 'vendor':
            c.execute("SELECT location FROM vendors WHERE name=?", (session['name'],))
            vloc = c.fetchone()
            c.execute("SELECT location FROM suppliers WHERE name=?", (product[1],))
            sloc = c.fetchone()

            if vloc and sloc:
                vlat, vlon = vloc[0].split(',')
                slat, slon = sloc[0].split(',')
                distance = round(haversine_distance(vlat, vlon, slat, slon), 2)
    except Exception as e:
        print("Distance error:", e)

    # Submit a review
    if request.method == 'POST':
        try:
            rating = int(request.form['rating'])
            review = request.form['review']
            c.execute("INSERT INTO reviews (product_id, reviewer, rating, review_text) VALUES (?, ?, ?, ?)",
                      (product_id, session['name'], rating, review))
            conn.commit()
        except Exception as e:
            print("Review submit error:", e)

    # Fetch reviews and average rating
    c.execute("SELECT reviewer, rating, review_text FROM reviews WHERE product_id=?", (product_id,))
    reviews = c.fetchall()

    avg_rating = None
    if reviews:
        total = sum([r[1] for r in reviews])
        avg_rating = round(total / len(reviews), 1)

    conn.close()
    return render_template("product_detail.html", product=product, reviews=reviews, distance=distance, avg_rating=avg_rating)

@app.route('/supplier_reviews/<supplier_name>', methods=['GET', 'POST'])
def supplier_reviews(supplier_name):
    if 'name' not in session or session['role'] != 'vendor':
        return redirect('/')
    conn = get_db_connection()  # Use helper function
    c = conn.cursor()
    if request.method == 'POST':
        rating = int(request.form['rating'])
        review = request.form['review']
        c.execute("INSERT INTO supplier_reviews (supplier_name, reviewer, rating, review_text) VALUES (?, ?, ?, ?)",
                  (supplier_name, session['name'], rating, review))
        conn.commit()
    c.execute("SELECT reviewer, rating, review_text FROM supplier_reviews WHERE supplier_name=?", (supplier_name,))
    reviews = c.fetchall()
    conn.close()
    return render_template("supplier_reviews.html", supplier_name=supplier_name, reviews=reviews)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# -------- Database Status Route (for debugging) --------
@app.route('/db_status')
def db_status():
    """Debug route to check database status"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get table info
    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in c.fetchall()]
    
    # Count records in each table
    counts = {}
    for table in tables:
        c.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = c.fetchone()[0]
    
    conn.close()
    
    return {
        "database_path": DATABASE_PATH,
        "database_exists": os.path.exists(DATABASE_PATH),
        "tables": tables,
        "record_counts": counts
    }

# Initialize database when app starts
init_db()

if __name__ == '__main__':
    app.run(debug=True)
