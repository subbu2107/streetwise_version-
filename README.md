🛒 StreetWize - Vendor-Supplier Marketplace

StreetWize is a Flask-powered web app for a geo-aware vendor-supplier platform where:

- Vendors can browse and order products from nearby suppliers.
- Suppliers can list products, manage orders, and receive reviews.
- Orders and chats are handled within the system.
- Proximity is calculated using real geographic coordinates.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 Features

- 🗺️ Location-aware product sorting using Haversine formula
- 📦 Vendor & Supplier dashboards
- 🛍️ Product listing with images and quantity control
- 📩 Chat system between vendors and suppliers
- ✅ Accept/Reject Order Management
- ⭐ Review & Rating system for products and suppliers

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🧱 Project Structure

project/
│
├── static/
│   └── uploads/           # Uploaded product images
│
├── templates/             # HTML templates
│   ├── dashboard_vendor.html
│   ├── dashboard_supplier.html
│   ├── home.html
│   ├── login.html
│   ├── product_detail.html
│   ├── supplier_reviews.html
│   └── chat.html
│
├── app.py                 # Main Flask app
├── requirements.txt       # Python dependencies
├── runtime.txt            # Python version for Render
├── Procfile               # Gunicorn entry point
└── README.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🧪 Local Setup

1. Clone the repo
   git clone https://github.com/subbu2107/streetwize.git
   cd streetwize

2. Create a virtual environment
   python -m venv venv
   source venv/bin/activate        (Linux/macOS)
   venv\Scripts\activate           (Windows)

3. Install dependencies
   pip install -r requirements.txt

4. Run the Flask app
   python app.py

**Visit: https://streetwize.onrender.com**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

☁️ Deploy on Render

Files required:
- requirements.txt
- runtime.txt      →  python-3.11.9
- Procfile         →  web: gunicorn app:app

Steps:
1. Push code to GitHub.
2. Go to https://render.com.
3. Click “New Web Service”.
4. Connect your GitHub repo.
5. Set:
   Build Command: pip install -r requirements.txt
   Start Command: gunicorn app:app
6. Deploy!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 Python Dependencies

Make sure your requirements.txt includes:

Flask==2.3.3
gunicorn==21.2.0
requests
werkzeug

(Generate via: pip freeze > requirements.txt)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 Location Format for Registration

Use either of the following formats in the coordinate input:

Format 1:
12.9716° N, 77.5946° E

Format 2 (preferred):
12.9716,77.5946




