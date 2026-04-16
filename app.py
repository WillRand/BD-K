from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import bcrypt
from db import (
    get_connection, get_all_items, get_item_by_id, purchase_item,
    get_user_inventory, get_user_balance, add_item, update_item_stock,
    delete_item, get_all_users, get_low_stock_items
)

app = Flask(__name__)
app.secret_key = 'your-secret-key-12345'  # В реальном проекте смените!

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите в систему'

# Класс пользователя для Flask-Login
class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data['id']
        self.username = user_data['username']
        self.role = user_data['role']
        self.balance = user_data['balance']

@login_manager.user_loader
def load_user(user_id):
    conn = get_connection()
    if not conn:
        return None
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, role, balance FROM users WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return User(user_data) if user_data else None

# ============ РЕГИСТРАЦИЯ И ВХОД ============

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm = request.form['confirm_password']
        
        if password != confirm:
            flash('Пароли не совпадают', 'danger')
            return redirect(url_for('register'))
        
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        
        conn = get_connection()
        if not conn:
            flash('Ошибка подключения к БД', 'danger')
            return redirect(url_for('register'))
        
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO users (username, password_hash, role, balance)
                VALUES (%s, %s, 'user', 1000)
            ''', (username, hashed.decode()))
            conn.commit()
            flash('Регистрация успешна! Теперь войдите в систему', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            if 'Duplicate entry' in str(e):
                flash('Пользователь с таким именем уже существует', 'danger')
            else:
                flash(f'Ошибка: {e}', 'danger')
            return redirect(url_for('register'))
        finally:
            cursor.close()
            conn.close()
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_connection()
        if not conn:
            flash('Ошибка подключения к БД', 'danger')
            return redirect(url_for('login'))
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user_data and bcrypt.checkpw(password.encode(), user_data['password_hash'].encode()):
            login_user(User(user_data))
            flash(f'Добро пожаловать, {username}!', 'success')
            return redirect(url_for('catalog'))
        
        flash('Неверное имя пользователя или пароль', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('catalog'))

# ============ КАТАЛОГ ============

@app.route('/')
@app.route('/catalog')
def catalog():
    category = request.args.get('category')
    sort_by = request.args.get('sort_by', 'name')
    order = request.args.get('order', 'ASC')
    
    items = get_all_items(category=category, sort_by=sort_by, order=order)
    return render_template('catalog.html', items=items)

# ============ ПОКУПКА ============

@app.route('/buy/<int:item_id>', methods=['POST'])
@login_required
def buy(item_id):
    quantity = int(request.form.get('quantity', 1))
    
    success, message = purchase_item(current_user.id, item_id, quantity)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('catalog'))

# ============ ИНВЕНТАРЬ ============

@app.route('/inventory')
@login_required
def inventory():
    items = get_user_inventory(current_user.id)
    return render_template('inventory.html', items=items)

# ============ АДМИН-ПАНЕЛЬ ============

@app.route('/admin')
@login_required
def admin_panel():
    if current_user.role != 'admin':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('catalog'))
    
    items = get_all_items()
    users = get_all_users()
    low_stock = get_low_stock_items(5)
    
    return render_template('admin.html', items=items, users=users, low_stock=low_stock)

@app.route('/admin/add', methods=['POST'])
@login_required
def admin_add_item():
    if current_user.role != 'admin':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('catalog'))
    
    name = request.form['name']
    description = request.form['description']
    price = int(request.form['price'])
    category = request.form['category']
    stock = int(request.form['stock'])
    image_url = request.form.get('image_url', '')
    
    success, message = add_item(name, description, price, category, stock, image_url)
    flash(message, 'success' if success else 'danger')
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/update_stock/<int:item_id>', methods=['POST'])
@login_required
def admin_update_stock(item_id):
    if current_user.role != 'admin':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('catalog'))
    
    new_stock = int(request.form['stock'])
    success, message = update_item_stock(item_id, new_stock)
    flash(message, 'success' if success else 'danger')
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete/<int:item_id>', methods=['POST'])
@login_required
def admin_delete_item(item_id):
    if current_user.role != 'admin':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('catalog'))
    
    success, message = delete_item(item_id)
    flash(message, 'success' if success else 'danger')
    
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    app.run(debug=True)