# ♻️ Green Keralam Web Application

A complete waste management and green initiative support system built with **Flask**, **PostgreSQL**, and **Bootstrap 4**, tailored for Haritha Karma Sena users and the public to ensure clean surroundings, complaint tracking, and green store services.

---

## 🚀 Features

### 🔐 Authentication
- OTP-based **Sign Up** with Email Verification
- Secure **Login** with Role-based Redirection (Admin/User)
- **Forgot Password** with OTP Verification and Password Reset

### 📍 User Module
- Sign up with geolocation (Leaflet Map) and OTP Verification
- Raise complaints (waste, sanitation, etc.)
- Track complaint status
- Access Green Store for eco-friendly products

### 🛒 Green Store
- View eco-products
- Request orders
- Order history and search

### 🧹 Haritha Karma Sena (Admin) Features
- View and manage user complaints
- Manage green store orders
- Assign or track Ward-based complaints
- Visualize user locations on map

---


## 📸 Demo

### 🏠 Home Page
![Home Page](static/images/homepage.jpeg "Home Page")

### 💳 Payment Integration
![Payment](static/images/payment_integration.jpeg "Payment Gateway")

### 👤 User Dashboard
![User Panel](static/images/userpanel.jpeg "User Dashboard")

### 🛍️ Green Store
![Store](static/images/store.jpeg "Eco Product Store")




## 💻 Technologies Used

| Tech            | Purpose                           |
|-----------------|-----------------------------------|
| Flask (Python)  | Backend Web Framework             |
| PostgreSQL      | Database                          |
| Bootstrap 4     | Responsive Frontend               |
| Leaflet.js      | Map Integration (Location Picker) |
| JavaScript      | Form Validation, UI Interactions  |
| Jinja2          | Template Rendering                |

---


## 📁 Project Structure

```
Green-kerala/
│
├── app.py
├── templates/
│   ├── login.html
│   ├── signup.html
│   ├── otp_verify.html
│   ├── orders.html
│   └── ...
│
├── static/
│   ├── css/
│   ├── js/
│   ├── image/
│
├── database/
│   └── schema.sql
├── requirements.txt
└── README.md


```



## 🛠 Setup Instructions

### 1. Clone the repository
```
git clone https://github.com/Nidhul-paik/Green-kerala.git
cd Green-kerala
```
### 🧪 2. Set up virtual environment 

```
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
```

### 📦 3. Install dependencies

```
pip install -r requirements.txt
```

### ▶️ 4. Configure .env

Create a .env file:

```
EMAIL_USER=your_email
EMAIL_PASS=your_email_app_pass
DB_PASSWORD=postgresql_db_password
KEY_ID=your_razorpay_key_id
KEY_SECRET=your_razorpay_secret_key
LINK=https://dashboard.razorpay.com/
```


### 5. Run the app

```
python app.py
```

### 📦 Database Schema
You can find the PostgreSQL schema (without data) in:
```
database/green_kerala_schema.sql
```
