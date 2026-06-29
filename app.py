import os
import sqlite3
import random
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-pastry-key-2026'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_FILE_DIR'] = os.path.join(os.getcwd(), 'flask_session')
Session(app)

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pastry_shop.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'user'
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS menu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                image_url TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total REAL,
                status TEXT DEFAULT 'Новый',
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                quantity INTEGER,
                price_at_moment REAL,
                FOREIGN KEY (order_id) REFERENCES orders (id),
                FOREIGN KEY (item_id) REFERENCES menu (id)
            )
        ''')
        db.commit()

        if cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            hashed_pw = generate_password_hash("admin123")
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                           ("admin", hashed_pw, "admin"))
            db.commit()

def generate_captcha():
    if 'captcha_answer' not in session:
        a = random.randint(1, 10)
        b = random.randint(1, 10)
        session['captcha_answer'] = a + b
        session['captcha_question'] = f"{a} + {b} = ?"
    return session['captcha_question']

@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_panel'))
        else:
            return redirect(url_for('user_cabinet'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        a = random.randint(1, 10)
        b = random.randint(1, 10)
        session['captcha_answer'] = a + b
        session['captcha_question'] = f"{a} + {b} = ?"
        return render_template('login.html', captcha_question=session['captcha_question'])
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        captcha_input = request.form.get('captcha', '')
        
        stored_answer = session.get('captcha_answer')
        
        try:
            if int(captcha_input) != stored_answer:
                flash('Неправильная капча! Попробуйте снова.', 'error')
                a = random.randint(1, 10)
                b = random.randint(1, 10)
                session['captcha_answer'] = a + b
                session['captcha_question'] = f"{a} + {b} = ?"
                return render_template('login.html', captcha_question=session['captcha_question'])
        except (ValueError, TypeError):
            flash('Введите число!', 'error')
            a = random.randint(1, 10)
            b = random.randint(1, 10)
            session['captcha_answer'] = a + b
            session['captcha_question'] = f"{a} + {b} = ?"
            return render_template('login.html', captcha_question=session['captcha_question'])
        
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session.pop('captcha_answer', None)
            session.pop('captcha_question', None)
            if user['role'] == 'admin':
                return redirect(url_for('admin_panel'))
            else:
                return redirect(url_for('user_cabinet'))
        else:
            flash('Неверный логин или пароль', 'error')
            a = random.randint(1, 10)
            b = random.randint(1, 10)
            session['captcha_answer'] = a + b
            session['captcha_question'] = f"{a} + {b} = ?"
    
    return render_template('login.html', captcha_question=session.get('captcha_question', ''))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        a = random.randint(1, 10)
        b = random.randint(1, 10)
        session['captcha_answer'] = a + b
        session['captcha_question'] = f"{a} + {b} = ?"
        return render_template('register.html', captcha_question=session['captcha_question'])
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        captcha_input = request.form.get('captcha', '')
        
        stored_answer = session.get('captcha_answer')
        
        try:
            if int(captcha_input) != stored_answer:
                flash('Неправильный ответ на капчу!', 'error')
                a = random.randint(1, 10)
                b = random.randint(1, 10)
                session['captcha_answer'] = a + b
                session['captcha_question'] = f"{a} + {b} = ?"
                return render_template('register.html', captcha_question=session['captcha_question'])
        except (ValueError, TypeError):
            flash('Введите число!', 'error')
            a = random.randint(1, 10)
            b = random.randint(1, 10)
            session['captcha_answer'] = a + b
            session['captcha_question'] = f"{a} + {b} = ?"
            return render_template('register.html', captcha_question=session['captcha_question'])
        
        db = get_db()
        try:
            hashed_pw = generate_password_hash(password)
            db.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                       (username, hashed_pw, 'user'))
            db.commit()
            session.pop('captcha_answer', None)
            session.pop('captcha_question', None)
            flash('Регистрация успешна! Теперь войдите.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Пользователь с таким именем уже существует!', 'error')
            a = random.randint(1, 10)
            b = random.randint(1, 10)
            session['captcha_answer'] = a + b
            session['captcha_question'] = f"{a} + {b} = ?"
    
    return render_template('register.html', captcha_question=session.get('captcha_question', ''))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/cabinet')
def user_cabinet():
    if 'user_id' not in session or session.get('role') != 'user':
        return redirect(url_for('login'))
    return render_template('user_cabinet.html', username=session['username'])

@app.route('/menu')
def menu():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    items = db.execute("SELECT * FROM menu").fetchall()
    return render_template('menu.html', items=items)

@app.route('/add_to_cart/<int:item_id>')
def add_to_cart(item_id):
    if 'cart' not in session:
        session['cart'] = {}
    cart = session['cart']
    cart[str(item_id)] = cart.get(str(item_id), 0) + 1
    session['cart'] = cart
    flash('Товар добавлен в корзину', 'success')
    return redirect(url_for('menu'))

@app.route('/cart', methods=['GET', 'POST'])
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    cart = session.get('cart', {})
    items = []
    total = 0
    for item_id, qty in cart.items():
        item = db.execute("SELECT * FROM menu WHERE id = ?", (item_id,)).fetchone()
        if item:
            subtotal = item['price'] * qty
            total += subtotal
            items.append({'id': item['id'], 'name': item['name'], 'price': item['price'], 'qty': qty, 'subtotal': subtotal})
    
    if request.method == 'POST':
        db.execute("INSERT INTO orders (user_id, total, status) VALUES (?, ?, ?)",
                   (session['user_id'], total, 'Новый'))
        order_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        
        for item in items:
            db.execute("INSERT INTO order_items (order_id, item_id, quantity, price_at_moment) VALUES (?, ?, ?, ?)",
                       (order_id, item['id'], item['qty'], item['price']))
        db.commit()
        session['cart'] = {}
        flash(f'Заказ №{order_id} оформлен! Администратор получил уведомление.', 'success')
        return redirect(url_for('my_orders'))
        
    return render_template('cart.html', items=items, total=total)

@app.route('/my_orders')
def my_orders():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    orders = db.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY order_date DESC", (session['user_id'],)).fetchall()
    return render_template('orders.html', orders=orders)

@app.route('/admin')
def admin_panel():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    db = get_db()
    items = db.execute("SELECT * FROM menu").fetchall()
    admins = db.execute("SELECT id, username FROM users WHERE role = 'admin'").fetchall()
    orders = db.execute("SELECT orders.*, users.username FROM orders JOIN users ON orders.user_id = users.id ORDER BY orders.order_date DESC").fetchall()
    return render_template('admin_panel.html', items=items, admins=admins, orders=orders)

@app.route('/admin/add_item', methods=['POST'])
def add_item():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    name = request.form['name']
    price = float(request.form['price'])
    desc = request.form['description']
    db = get_db()
    db.execute("INSERT INTO menu (name, description, price) VALUES (?, ?, ?)", (name, desc, price))
    db.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_item/<int:item_id>')
def delete_item(item_id):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    db = get_db()
    db.execute("DELETE FROM menu WHERE id = ?", (item_id,))
    db.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/add_admin', methods=['POST'])
def add_admin():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    username = request.form['username']
    password = request.form['password']
    hashed_pw = generate_password_hash(password)
    db = get_db()
    try:
        db.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'admin')", (username, hashed_pw))
        db.commit()
        flash('Админ добавлен', 'success')
    except:
        flash('Ошибка: имя занято', 'error')
    return redirect(url_for('admin_panel'))

@app.route('/admin/update_order/<int:order_id>', methods=['POST'])
def update_order(order_id):
    if session.get('role') != 'admin': 
        return redirect(url_for('login'))
    status = request.form['status']
    db = get_db()
    db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    db.commit()
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    with app.app_context():
        init_db()
    import os
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=False, host='0.0.0.0', port=port)
