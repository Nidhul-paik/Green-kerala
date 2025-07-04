from flask import Flask, render_template, session, redirect, url_for, request, jsonify, flash, get_flashed_messages
from translations import translations
import psycopg2
from dbconnection import get_db_connection
from werkzeug.security import generate_password_hash,check_password_hash
import time, random
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import razorpay
import re



load_dotenv()


app = Flask(__name__)
app.secret_key = 'harithamooniyur'


#--------RAZORPAY SETTINGS--------

RAZORPAY_KEY_ID = os.getenv('KEY_ID')
RAZORPAY_KEY_SECRET = os.getenv('KEY_SECRET')
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

app.config['UPLOAD_FOLDER'] = 'static/product_images'

# Home route
@app.route('/')
def home():
    user = session.get('user')
    if user:
        return render_template('index.html', user=user, show_login=False)
    else:
        return render_template('index.html', user=None, show_login=True)

@app.route('/login',methods=['POST'])
def login():
    try:
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            db_password = user[6]
            if check_password_hash(db_password, password):
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['user'] = user[2]
                role = user[9]  # Assuming role column

                return jsonify({'status': 'success', 'role': role})
            else:
                return jsonify({'status': 'error', 'message': 'Incorrect password'})
        else:
            return jsonify({'status': 'error', 'message': 'Email not registered'})

    except Exception as e:
        print("Login error:", e)
        return jsonify({'status': 'error', 'message': 'Server error. Try again'})

    
@app.route('/adminpannel')
def admin_panel():
    if session.get('user') and session.get('user_id') and session.get('username'):
        conn = get_db_connection() # Use the modified function
        cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            SELECT complaints.*, users.username
            FROM complaints
            LEFT JOIN users ON complaints.user_id = users.id
            ORDER BY complaints.complaint_date;
        """)
        complaints = cur.fetchall()
       

        # Fetch waste data
        conn = get_db_connection()
        
        return render_template("adminpannel.html", complaints=complaints,greenkerala="Green Kerala")

    else:
        return redirect('/')


@app.route('/collectors')
def collectors():
    # Fetch collectors (if you have this table and logic)
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM collectors")
        collectors = cur.fetchall()
        return render_template('collectorsshow.html',collectors=collectors,)

@app.route('/delete_collector/<int:id>', methods=['POST'])
def delete_collector(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM collectors WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Collector deleted successfully", "success")
    return redirect(url_for('collectors'))

@app.route('/edit_collector/<int:id>', methods=['POST'])
def edit_collector(id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    name = request.form['name']
    email = request.form['email']
    mob = request.form['mob']

  
    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
    if cur.fetchone():
        flash("This collector is already a user", "info")
        
    cur.execute("UPDATE collectors SET name = %s, email = %s, mob = %s WHERE id = %s",
                (name, email, mob, id))
    conn.commit()
    cur.close()
    conn.close()
    flash("Collector updated successfully", "success")
    return redirect(url_for('collectors'))

@app.route('/Signup', methods=['POST'])
def signup():
    data = request.form

    # reading values from signup form
    username = data['username']
    email = data['email']
    mob = data['mob']
    address = data['address']
    wardno = data['wardno']
    password = data['pass']
    cpass = data['cpass']
    latitude = data['latitude']
    longitude = data['longitude']
    role = 'user'

    errors = {}

    # Check if email already exists
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
    if cur.fetchone():
        errors['email'] = "Email already exists"
    cur.close()
    conn.close()

    # Check password match
    if password != cpass:
        errors['pass'] = "Passwords do not match"
        errors['cpass'] = "Passwords do not match"

     # ✅ Phone number validation (10 digits, all numbers)
    if not re.fullmatch(r'[6-9]\d{9}', mob):
        errors['mob'] = "Invalid mobile number (must be 10 digits and start with 6-9)"

    # ✅ Password strength validation
    if len(password) < 6:
        errors['pass'] = "Password must be at least 6 characters long"
    elif not re.search(r'[A-Z]', password):
        errors['pass'] = "Password must include at least one uppercase letter"
    elif not re.search(r'[a-z]', password):
        errors['pass'] = "Password must include at least one lowercase letter"
    elif not re.search(r'[0-9]', password):
        errors['pass'] = "Password must include at least one digit"
    elif not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors['pass'] = "Password must include at least one special character"    

    if errors:
        return jsonify({'status': 'error', 'errors': errors})

    # Hash the password
    hashed_password = generate_password_hash(password)

    # Generate OTP
    otp = str(random.randint(100000, 999999))
    session['otp'] = otp
    session['otp_time'] = time.time()

    # Store user data in session
    session['user_data'] = {
        'username': username,
        'email': email,
        'mob': mob,
        'address': address,
        'wardno': wardno,
        'password': hashed_password,
        'latitude': latitude,
        'longitude': longitude,
        'role' : role,
    }

    # Send OTP
    sent = send_otp_email(email, otp)
    if sent:
        return jsonify({'status': 'ok'})
    else:
        return jsonify({'status': 'error', 'errors': {'email': 'Failed to send OTP'}})

  
 #otp verification 
@app.route('/verify_otp', methods=['POST'])
def verify_otp():

    entered_otp = request.form['otp']
    stored_otp = session.get('otp')
    otp_time = session.get('otp_time')

    if not stored_otp or not otp_time:
        return jsonify({'status': 'error', 'message': 'Session expired. Please register again.'})

    # Check timeout (300 seconds = 5 minutes)
    if time.time() - otp_time > 300:
        session.pop('otp', None)
        session.pop('otp_time', None)
        return jsonify({'status': 'error', 'message': 'OTP expired. Please request a new one.'})

    if entered_otp == stored_otp:
        # Save user_data from session to database
        user_data = session.pop('user_data', {})
        save_user_to_db(user_data)
        session.pop('otp', None)
        session.pop('otp_time', None)
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': 'Invalid OTP. Try again.'})



@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

# user profile page
@app.route('/profile')
def profile():
    user_id = session.get('user_id')

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

  
    user = session.get('username')
    users = session.get('user')

    flag = False
    cur.execute("SELECT * FROM collectors WHERE email = %s",(users,))
    if cur.fetchone():
        flag = True

    #complaints registratiion
    cur.execute("SELECT * FROM complaints WHERE user_id = %s ORDER BY complaint_date DESC", (user_id,))
    complaints = cur.fetchall()

    

    return render_template("userprofile.html",user=user,flag = flag)


@app.route("/edituser")
def edituser():
    user_id = session.get('user_id')

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

  
    user = session.get('username')

    #user details
    cur.execute("SELECT * FROM users WHERE id = %s ", (user_id,))
    users = cur.fetchone()

    cur.close()
    conn.close()
    return render_template('edituser.html',users=users)

#----- address update-----------
@app.route('/update_user', methods=['POST'])
def update_user():
    user_id = session.get('user_id')
    address = request.form['address']
    wardno = request.form['wardno']
    phone = request.form['phone']
    name = request.form['name']

   

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET username = %s, mob = %s, address = %s, wardno = %s WHERE id = %s", (name, phone, address, wardno, user_id))
    conn.commit()
    cur.close()
    conn.close()

    flash("Details updated successfully!", "success")
    return redirect(url_for('edituser'))




# waste collection regitration page
@app.route('/wasteregistration')
def wasteregistration():
    user = session.get('user')
    if user:
        return render_template('wasteregistration.html' ,user =user,show_login=False )
    else:
        return render_template('wasteregistration.html',user=None,show_login=True)

# waste collection booking
@app.route('/bookwaste', methods=['POST'])
def bookwaste():
    try:
        user = session.get('user')
        user_id = session.get('user_id')
        if not user:
            return render_template('wasteregistration.html' ,user=None,show_login=True)
        else:
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO wastecollection (user_id, date, status)
                VALUES (%s, %s, %s)
            """, (user_id, current_date, 'Pending'))

            conn.commit()
            cur.close()
            conn.close()

            return jsonify({'status': 'success', 'message': 'Waste collection booked successfully'})
    except Exception as e:
        print("Booking Error:", e)
        return jsonify({'status': 'error', 'message': 'Server error'})


#complaint registration page
@app.route('/complaintregisterationpage')
def complaintregisterationpage():
    if session.get('user'):
        return render_template('complaint.html')

@app.route('/submit_complaint', methods=['POST'])
def submit_complaint():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect('/')

        waste_type = request.form['waste_type']
        location = request.form['location']
        description = request.form['description']
        file = request.files['media']
        media_path = None

        if file and file.filename != '':
            filename = secure_filename(file.filename)
            media_path = os.path.join('static/uploads', filename)
            file.save(media_path)

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO complaints (user_id, complaint_date, waste_type, location, media, description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, datetime.now(), waste_type, location, media_path, description))

        conn.commit()
        cur.close()
        conn.close()

        return redirect('/complaintregisterationpage')  # or show success message
    except Exception as e:
        print("Complaint error:", e)
        return "Server error", 500


#----green store-----
@app.route('/greenstore')
def greenstore():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE type = 'Bags';")
    bags = cur.fetchall()
    cur.execute("SELECT * FROM products WHERE type = 'Plants';")
    plants = cur.fetchall()
    cur.execute("SELECT * FROM products WHERE type = 'Seeds';")
    seeds = cur.fetchall()

    # Get wishlist product ids for current user
    wishlist_ids = []
    if session.get('user_id'):
        cur.execute("SELECT product_id FROM wishlist WHERE user_id = %s", (session['user_id'],))
        wishlist_ids = [row[0] for row in cur.fetchall()]

    cur.close()
    conn.close()
    return render_template('store.html',bags=bags,seeds=seeds,plants=plants,wishlist_ids=wishlist_ids)    




#-----  collectors adding page---
@app.route('/collectorsadding')
def collectorsadding():
    return render_template('add_collector.html')

#--add collectors---
@app.route('/add_collector', methods=['GET', 'POST'])
def add_collector():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        mob = request.form['mob']
        password = request.form['pass']
       
        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO collectors (name, email, mob, password) VALUES (%s, %s, %s, %s)",
                        (name, email, mob, password))
            conn.commit()
            flash("Collector added successfully", "success")
        except Exception as e:
            conn.rollback()
            flash("Error adding collector: " + str(e), "danger")
        finally:
            cur.close()
            conn.close()
        return redirect('/add_collector')

    return render_template('add_collector.html')



@app.route('/storepanel')
def storepanel():
    return render_template('storepanel.html')


@app.route('/addproductpage')
def addproductpage():
    return render_template('addproduct.html')

# #----product adding---
# app.config['UPLOAD_FOLDER'] = 'static/uploads'
# #---- store panel----
# @app.route('/storepanel', methods=['GET','POST'])
# def storepanel():
#     conn = get_db_connection()
#     cur = conn.cursor()

    
#     if request.method == 'POST':
#         p_name = request.form['p_name']
#         price = request.form['price']
#         p_type = request.form['type']
#         image = request.files.get('image')

#         if image and image.filename != '':
#             filename = secure_filename(image.filename)
#             image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#             image.save(image_path)

#             cur.execute("""
#                 INSERT INTO products (p_name, price, image, type)
#                 VALUES (%s, %s, %s, %s)
#             """, (p_name, price, filename, p_type))
#             conn.commit()

#             flash("Product added successfully!", "success")
#         else:
#             flash("Image not selected or upload failed", "danger")

#         cur.close()
#         conn.close()
#         return redirect(url_for('storepanel'))

#     cur.execute("SELECT * FROM products")
#     products = cur.fetchall()
#     cur.close()
#     conn.close()
#     return render_template("storepanel.html", products=products)


@app.route('/addproduct',methods = ['GET','POST'])
def addproduct():
    if request.method == 'POST':
        image = request.files.get('img')
        price = request.form['price']
        name = request.form['p_name']
        p_type = request.form['type'].strip().capitalize()



        if image and image.filename !='':
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'],filename)
            image.save(image_path)

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO products (p_name, price, image, type)
                VALUES (%s, %s, %s, %s)
            """, (name, price, filename, p_type))

            conn.commit()
            cur.close()
            conn.close()

            return render_template('addproduct.html')
    return render_template('storepanel.html')



@app.route('/backtostore')
def backtostore():
    return redirect(url_for('storepanel'))



@app.route('/showproduct')
def showproduct():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM products
        ORDER BY 
            CASE 
                WHEN type = 'Plants' THEN 1
                WHEN type = 'Seeds' THEN 2
                WHEN type = 'Bags' THEN 3
                ELSE 4
            END
    """
    )
    products = cur.fetchall()
    
    cur.close()
    conn.close()

    return render_template('showproduct.html',products=products)



@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update_product(id):
    # Example logic (you can expand this)
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        p_name = request.form['name']
        price = request.form['price']
      
        p_type = request.form['p_type'].strip().capitalize()
       

        image = request.files.get('img')

        if image and image.filename != '':
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)

            cur.execute(
                "UPDATE products SET p_name=%s, price=%s, type=%s, image=%s WHERE id=%s",
                (p_name, price, p_type, filename, id)
            )
        else:
            # No new image uploaded, keep existing image
            cur.execute(
                "UPDATE products SET p_name=%s, price=%s, type=%s WHERE id=%s",
                (p_name, price, p_type, id)
            )

       

        conn.commit()
        cur.close()
        conn.close()
        flash('Product updated successfully', 'success')
        return redirect(url_for('showproduct'))

   
    return redirect(url_for('showproduct'))


@app.route('/delete/<int:id>', methods=['POST'])
def delete_product(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    flash('Product deleted successfully', 'success')
    return redirect(url_for('showproduct'))



#----add to wishlist-----
@app.route('/addtowishlist/<int:id>',methods=['POST'])
def addtowishlist(id):

    try:
        userid = session.get('user_id')
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("INSERT INTO wishlist (user_id, product_id, added_date) VALUES (%s, %s, %s)", (userid, id, current_date))
        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for('greenstore'))
    except Exception as e:
        print("database error:",e)
        raise


#----remove from wishlist-----
@app.route('/removefromwishlist/<int:id>', methods=['POST'])
def removefromwishlist(id):
    try:
        userid = session.get('user_id')

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute("DELETE FROM wishlist WHERE user_id = %s AND product_id = %s", (userid, id))
        conn.commit()

        cur.close()
        conn.close()

        return redirect(url_for('greenstore'))
    except Exception as e:
        print("Error removing from wishlist:", e)
        raise

#-------add to cart ------
@app.route('/addtocart/<int:id>', methods=['POST'])
def addtocart(id):
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash("Please login to add items to cart", "warning")
            return redirect(url_for('login'))

        quantity = int(request.form.get('quantity', 1))
        added_date = datetime.now()

        conn = get_db_connection()
        cur = conn.cursor()

        # Check if already in cart
        cur.execute("SELECT id FROM cart WHERE user_id = %s AND product_id = %s", (user_id, id))
        existing = cur.fetchone()

        if existing:
            # Update quantity
            cur.execute("UPDATE cart SET quantity = quantity + %s WHERE id = %s", (quantity, existing[0]))
        else:
            # Insert into cart
            cur.execute("INSERT INTO cart (user_id, product_id, quantity, added_date) VALUES (%s, %s, %s, %s)",
                        (user_id, id, quantity, added_date))

        conn.commit()
        cur.close()
        conn.close()

        flash("Product added to cart!", "success")
        return redirect(url_for('greenstore'))
    except Exception as e:
        print("Cart error:", e)
        flash("Error adding to cart", "danger")
        return redirect(url_for('greenstore'))


#----- Buy now route and page------
@app.route('/buy_now/<int:id>', methods=['GET'])
def buy_now(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE id = %s", (id,))
    product = cur.fetchone()
    cur.close()
    conn.close()

    amount = int(product[2]) * 100  # price in paise
    razorpay_order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1
    })

    return render_template("checkout.html", product=product, order=razorpay_order, key_id=os.getenv("KEY_ID"))



#----- handle order placement-----
@app.route('/place_order/<int:id>', methods=['POST'])
def place_order(id):
    user_id = session.get('user_id')
    data = request.get_json()
    mob = data['mob']
    address = data['address']
    quantity = int(data['quantity'])

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT price FROM products WHERE id = %s", (id,))
    product = cur.fetchone()
    price = float(product[0]) * quantity

    cur.execute("""
        INSERT INTO orders (user_id, product_id, order_address, quantity, price, mob, status, order_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (user_id, id, address, quantity, price, mob, 'paid', datetime.now()))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "Order placed"}), 200




@app.route('/editcomplaint')
def editcomplaint():
    user_id = session.get('user_id')
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("SELECT * FROM complaints WHERE user_id = %s ORDER BY complaint_date DESC", (user_id,))
    complaints = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("usercomplaint.html", complaints=complaints)


@app.route('/removecmplnt/<int:id>', methods=['POST'])
def removecmplnt(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM complaints WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Complaint withdrawn successfully", "success")
    return redirect(url_for('editcomplaint'))



@app.route('/userwaste')
def userwaste():
   
    user_id = session.get('user_id')
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("SELECT * FROM wastecollection WHERE user_id = %s ORDER BY date DESC", (user_id,))
    wastecollection = cur.fetchall()
    cur.close()
    conn.close()
  

    return render_template("wastecollectionbooking.html", wastecollection=wastecollection)


@app.route('/removewastebooking/<int:id>',methods=['POST','GET'])
def removewastebooking(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM wastecollection WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("booking withdrawn successfully", "success")
    return redirect(url_for('userwaste'))



@app.route('/userorder')
def userorder():
    user_id = session.get('user_id')
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    #wishlist
    cur.execute('''SELECT p.p_name, p.price,w.id FROM wishlist w 
                   JOIN products p ON w.product_id = p.id 
                   WHERE w.user_id = %s''', (user_id,))
    wishlist = cur.fetchall()

    #cart
    cur.execute('''SELECT p.p_name, p.price, c.quantity,c.id FROM cart c 
                   JOIN products p ON c.product_id = p.id 
                   WHERE c.user_id = %s''', (user_id,))
    cart = cur.fetchall()

    #orders
    # cur.execute("SELECT * FROM orders WHERE user_id = %s ORDER BY order_date DESC", (user_id,))
    cur.execute("""
    SELECT 
        o.order_id AS order_id,
        o.quantity,
        o.order_date,
        o.exp_date,
        o.price,
        o.status,
        p.id,
        p.p_name,
        p.image
    FROM 
        orders o
    JOIN 
        products p ON o.product_id = p.id
    WHERE 
        o.user_id = %s AND o.status != 'canceled'
    ORDER BY 
        o.order_date DESC
""", (user_id,))
    orders = cur.fetchall()

    cur.close()
    conn.close()
    return render_template('userorder.html',wishlist=wishlist,orders=orders,cart=cart)


@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    user_id = session.get('user_id')
    sta = 'canceled'
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status = %s  WHERE order_id = %s AND user_id = %s", (sta, order_id, user_id))
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('userorder'))


@app.route('/addcart/<int:id>', methods=['POST'])
def addcart(id):
    try:
        user_id = session.get('user_id')
        quantity = int(request.form.get('quantity', 1))
        added_date = datetime.now()

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # 1. Get product_id from wishlist row using id
        cur.execute("SELECT product_id FROM wishlist WHERE id = %s AND user_id = %s", (id, user_id))
        row = cur.fetchone()

        if not row:
            flash("Product not found in wishlist", "danger")
            return redirect(url_for('userorder'))

        product_id = row['product_id']

        # 2. Check if product already in cart
        cur.execute("SELECT id FROM cart WHERE user_id = %s AND product_id = %s", (user_id, product_id))
        existing = cur.fetchone()

        if existing:
            # Update quantity
            cur.execute("UPDATE cart SET quantity = quantity + %s WHERE id = %s", (quantity, existing['id']))
        else:
            # Insert into cart
            cur.execute("""
                INSERT INTO cart (user_id, product_id, quantity, added_date)
                VALUES (%s, %s, %s, %s)
            """, (user_id, product_id, quantity, added_date))

        # 3. Delete from wishlist using the wishlist row ID
        cur.execute("DELETE FROM wishlist WHERE id = %s AND user_id = %s", (id, user_id))

        conn.commit()
        cur.close()
        conn.close()

        flash("Product added to cart!", "success")
        return redirect(url_for('userorder'))

    except Exception as e:
        print("Cart error:", e)
        flash("Error adding to cart", "danger")
        return redirect(url_for('userorder'))




@app.route('/removecart/<int:id>',methods=['POST'])
def removecart(id):
    try:
        user_id = session.get('user_id')
        
        conn = get_db_connection()
        cur = conn.cursor()

        # Delete only if the item belongs to this user
        cur.execute("DELETE FROM cart WHERE id = %s AND user_id = %s", (id, user_id))
        conn.commit()

        cur.close()
        conn.close()

        flash("Item removed from cart", "success")
    except Exception as e:
        print("Remove cart error:", e)
        flash("Error removing item", "danger")

    return redirect(url_for('userorder'))



@app.route('/update_qty/<int:id>',methods=['POST'])
def update_qty(id):
    qty = request.form['quantity']
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""UPDATE cart SET quantity=%s WHERE id = %s
    """,(qty,id)
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('userorder'))


@app.route('/removewishlist/<int:id>', methods=['POST'])
def removewishlist(id):
    try:
        userid = session.get('user_id')

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute("DELETE FROM wishlist WHERE user_id = %s AND product_id = %s", (userid, id))
        conn.commit()

        cur.close()
        conn.close()

        return redirect(url_for('greenstore'))
    except Exception as e:
        print("Error removing from wishlist:", e)
        raise




@app.route('/create_order', methods=['POST'])
def create_order():
    user_id = session.get('user_id')
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute('''SELECT p.p_name, p.price, c.quantity, p.id 
                   FROM cart c JOIN products p ON c.product_id = p.id 
                   WHERE c.user_id = %s''', (user_id,))
    items = cur.fetchall()

    if not items:
        flash("Cart is empty", "warning")
        return redirect(url_for('userorder'))

    total_amount = sum(item['price'] * item['quantity'] for item in items)

    order_data = {
        'amount': int(total_amount * 100),  # in paise
        'currency': 'INR',
        'payment_capture': 1
    }

    payment_order = client.order.create(data=order_data)

    # Get Razorpay Key ID from env
    key_id = os.getenv('KEY_ID')

    return render_template("payment.html", 
                           order=payment_order, 
                           items=items, 
                           total=total_amount,
                           key_id=key_id)



@app.route('/payment_success', methods=['POST'])
def payment_success():
    user_id = session.get('user_id')

    data = request.get_json()
    mob = data['mob']
    address = data['address']

    # Save order to database
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute('''SELECT product_id, quantity 
                   FROM cart WHERE user_id = %s''', (user_id,))
    cart_items = cur.fetchall()

    for item in cart_items:
        product_id = item['product_id']
        quantity = item['quantity']
        order_date = datetime.now()
        status = 'paid'

        # Fetch product price
        cur.execute("SELECT price FROM products WHERE id = %s", (product_id,))
        price = cur.fetchone()['price']

        # Insert into orders
        cur.execute("""INSERT INTO orders (user_id, product_id, order_address, quantity, price, order_date, status, mob) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (user_id, product_id, address, quantity, price, order_date, status, mob))

    # Clear cart after order
    cur.execute("DELETE FROM cart WHERE user_id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()

    flash("Payment successful and order placed!", "success")
    return jsonify({"message": "Order placed"}), 200



@app.route('/adminwaste')
def adminwaste():
     # Fetch complaints
    conn = get_db_connection()
    cur = conn.cursor()    
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('''SELECT
        wastecollection.id AS booking_id,
        users.username,
        users.email,
        users.mob,
        users.address,
        users.wardno,
        wastecollection.date,
        wastecollection.status
    FROM
        wastecollection
    LEFT JOIN
        users ON wastecollection.user_id = users.id;
    ''')
    waste = cur.fetchall()
    return render_template('adminwaste.html',waste=waste)


@app.route('/addtotask/<int:id>', methods=['POST'])
def addtotask(id):
    user_id = session.get('user_id')

    # Connect to DB
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT user_id FROM wastecollection WHERE id = %s",(id,))
    data = cur.fetchone()
    # Insert into task table
    cur.execute("""
        INSERT INTO task (wastecollection_id, user_id)
        VALUES (%s, %s)
    """, (id, data))

    # Update status of wastecollection
    cur.execute("""
        UPDATE wastecollection
        SET status = %s
        WHERE id = %s
    """, ('pending', id))

    # Commit and close
    conn.commit()
    cur.close()
    conn.close()

    
    return redirect(url_for('adminwaste'))



#-------Back_to_admin_panel------
@app.route('/backtoadmin')
def backtoadmin():
    return redirect(url_for('admin_panel'))


#------ Admin_user_page-----
@app.route('/users')
def users():
    conn = get_db_connection()
    cur = conn.cursor()
    type = 'user'
    # Fetch users
    cur.execute("SELECT * FROM users WHERE type = %s",(type,))
    users = cur.fetchall()

    return render_template('users.html',users = users)



#------ admin_delete_user-------

@app.route('/removeuser/<int:id>', methods=['POST'])
def removeuser(id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM users WHERE id = %s", (id,))
    conn.commit() 
    cur.close()
    conn.close()

    return redirect(url_for('users'))  


#------collector's works-----
@app.route('/works')
def works():
    conn = get_db_connection()
   
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor) # Use DictCursor for readable access

    cur.execute("""
        SELECT 
            a.id AS task_id,
            a.wastecollection_id,
            a.user_id AS task_user_id,
            
            b.id AS waste_id,
            b.user_id AS waste_user_id,
            
            c.id AS user_id,
            c.username,
            c.wardno,
            c.mob,
            c.address,
            c.latitude,
            c.longitude
        FROM 
            task a
        JOIN 
            wastecollection b ON a.wastecollection_id = b.id AND a.user_id = b.user_id
        JOIN 
            users c ON c.id = b.user_id
     """)


    flag = False
    works = cur.fetchall()
    if works:
        flag = True
    cur.close()
    conn.close()

    return render_template('works.html', works=works,flag = flag)


#----- collector task done ---------
@app.route('/taskdone/<int:id>',methods=['POST'])
def taskdone(id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("DELETE  FROM task WHERE wastecollection_id=%s",(id,))
    conn.commit()

    cur.execute("UPDATE wastecollection SET status = 'done' WHERE id = %s",(id,))
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('works'))


#-----admin orders page------
@app.route('/orders')
def orders():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    data = 'done'
    cur.execute("""
    SELECT * FROM orders
    LEFT JOIN products ON orders.product_id = products.id  WHERE status != %s
    """,(data,))
    orders = cur.fetchall()

    return render_template('orders.html',orders=orders)


#----order done------
@app.route('/doneorder/<int:id>',methods=['POST'])
def doneorder(id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    data = 'done'
    cur.execute("UPDATE orders SET status = %s WHERE order_id = %s ",(data,id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('orders'))


#------order_history_search----
@app.route('/order_history', methods=['GET', 'POST'])
def order_history():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    search_query = request.form.get('search', '').strip()
    
    if search_query:
        cur.execute("""
            SELECT o.*, p.p_name AS product_name
            FROM orders o
            LEFT JOIN products p ON o.product_id = p.id
            WHERE LOWER(p.p_name) LIKE LOWER(%s)
            ORDER BY o.order_date DESC
        """, ('%' + search_query + '%',))
    else:
        cur.execute("""
            SELECT o.*, p.p_name AS product_name
            FROM orders o
            LEFT JOIN products p ON o.product_id = p.id
            ORDER BY o.order_date DESC
        """)
    
    orders = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("order_history.html", orders=orders, search=search_query)


#----forgot_password_page------
@app.route('/forgot_password')
def forgot_password():
    return render_template("forgot_password.html")



#----forgot_pass_otp_sending----
@app.route('/forgot_pass_otp_send',methods=['POST'])
def forgot_pass_otp_send():
    # Generate OTP
    otp = str(random.randint(100000, 999999))
    session['otp'] = otp
    session['otp_time'] = time.time()

    email = request.form['email']
    sent = send_otp_email(email, otp)
    return render_template('pass_otp_verify.html')


@app.route('/pass_verify_otp', methods=['POST'])
def pass_verify_otp():
    entered_otp = request.form['otp']
    stored_otp = session.get('otp')
    otp_time = session.get('otp_time')

    if not stored_otp or not otp_time:
        return render_template('Pass_otp_verify.html', error='Session expired. Please register again.')

    if time.time() - otp_time > 300:
        session.pop('otp', None)
        session.pop('otp_time', None)
        return render_template('pass_otp_verify.html', error='OTP expired. Please request a new one.')

    if entered_otp == stored_otp:
        
        session.pop('otp', None)
        session.pop('otp_time', None)
        return render_template('update_password.html')
    else:
        return render_template('pass_otp_verify.html', error='Invalid OTP. Try again.')


#-----update_password----
@app.route('/update_password', methods=['GET', 'POST'])
def update_password():
    if request.method == 'POST':
        user_id = session.get('user_id')
        new_pass = request.form['new_password']
        confirm_pass = request.form['confirm_password']

        if new_pass != confirm_pass:
            return render_template('update_password.html', error="Passwords do not match")

        hashed_password = generate_password_hash(new_pass)

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET pass = %s WHERE id = %s", (hashed_password, user_id))
        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for('home'))  # or show success message

    return render_template('update_password.html')


#-----save user data to database------
def save_user_to_db(user_data):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (username, email, mob, address, wardno, pass, latitude, longitude,type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_data['username'],
            user_data['email'],
            user_data['mob'],
            user_data['address'],
            user_data['wardno'],
            user_data['password'],
            user_data['latitude'],
            user_data['longitude'],
            user_data['role']
        ))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("Database Error:", e)
        raise


#--------- email sending function ---------

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

load_dotenv()  # Load from .env file

EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')


def send_otp_email(recipient_email, otp_code):
   
    
    EMAIL_USER = os.getenv('EMAIL_USER')
    EMAIL_PASS = os.getenv('EMAIL_PASS')

    sender_email = EMAIL_USER
    app_password = EMAIL_PASS
    subject = "Your OTP Code"
    body = f"Your OTP verification code is: {otp_code}"

    # Create message
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = recipient_email
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    try:
        # Connect to Gmail SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, recipient_email, message.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False


# Set default language
@app.before_request
def set_default_language():
    if 'lang' not in session:
        session['lang'] = 'en'

# Inject translation dict into all templates
@app.context_processor
def inject_translations():
    lang = session.get('lang', 'en')
    return {'text': translations[lang]}

# Route to change language
@app.route('/set_language/<lang>')
def set_language(lang):
    if lang in translations:
        session['lang'] = lang
    return redirect(request.referrer or url_for('home'))



if __name__ == '__main__':
    app.run(debug=True)
