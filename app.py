from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import bcrypt
from db import (
    get_connection, get_all_items, get_item_by_id, purchase_item,
    get_user_inventory, get_user_balance, add_item, update_item_stock,
    delete_item, get_all_users, get_low_stock_items,
    get_all_users_with_details, update_user_balance, get_user_inventory_admin,
    get_user_by_id_admin, admin_remove_item_from_inventory,
    get_all_items_for_admin, admin_add_item_to_inventory_no_stock_check,
    update_item_stock_admin, create_market_offer, get_active_market_offers, buy_from_market,
    cancel_market_offer, get_player_transactions, get_item_price_history,
    get_all_items_list, update_item_full, get_item_full, create_user_admin, update_user_admin,
    delete_user_admin, get_all_tables, get_table_data, get_table_schema,
    get_all_users_inventory, update_item_stock_moderator, assign_moderator_role,
    is_moderator_or_admin, get_all_users_for_moderator, get_user_inventory_readonly
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
    # Получаем параметры из URL
    category = request.args.get('category', '')
    sort_by = request.args.get('sort_by', 'name')
    order = request.args.get('order', 'ASC')
    stock_filter = request.args.get('stock_filter', 'all')
    
    # Получаем все товары
    all_items = get_all_items(category=category if category else None, 
                               sort_by=sort_by, 
                               order=order, 
                               show_out_of_stock=True)
    
    # Фильтруем по наличию (если нужно)
    if stock_filter == 'in_stock':
        items = [item for item in all_items if item['stock'] > 0]
    elif stock_filter == 'out_stock':
        items = [item for item in all_items if item['stock'] == 0]
    else:
        items = all_items
    
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
    
    new_stock = int(request.form.get('stock', 0))
    success, message = update_item_stock_admin(item_id, new_stock)
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

# ============ ПРОДАЖА ============

@app.route('/sell/<int:item_id>', methods=['POST'])
@login_required
def sell(item_id):
    quantity = int(request.form.get('quantity', 1))
    
    from db import sell_item
    success, message = sell_item(current_user.id, item_id, quantity)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('inventory'))

# ============ АДМИН: УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ============

@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('catalog'))
    
    users = get_all_users_with_details()
    return render_template('admin_users.html', users=users)

@app.route('/admin/user/<int:user_id>')
@login_required
def admin_user_detail(user_id):
    if current_user.role != 'admin':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('catalog'))
    
    user = get_user_by_id_admin(user_id)
    if not user:
        flash('Пользователь не найден', 'danger')
        return redirect(url_for('admin_users'))
    
    inventory = get_user_inventory_admin(user_id)
    all_items = get_all_items_for_admin()
    
    return render_template('admin_user_detail.html', user=user, inventory=inventory, all_items=all_items)

@app.route('/admin/user/<int:user_id>/update_balance', methods=['POST'])
@login_required
def admin_update_balance(user_id):
    if current_user.role != 'admin':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('catalog'))
    
    new_balance = int(request.form.get('new_balance', 0))
    success, message = update_user_balance(user_id, new_balance)
    flash(message, 'success' if success else 'danger')
    
    return redirect(url_for('admin_user_detail', user_id=user_id))

@app.route('/admin/user/<int:user_id>/remove_item/<int:item_id>', methods=['POST'])
@login_required
def admin_remove_item(user_id, item_id):
    if current_user.role != 'admin':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('catalog'))
    
    quantity = int(request.form.get('quantity', 1))
    success, message = admin_remove_item_from_inventory(user_id, item_id, quantity)
    flash(message, 'success' if success else 'danger')
    
    return redirect(url_for('admin_user_detail', user_id=user_id))

@app.route('/admin/user/<int:user_id>/add_item', methods=['POST'])
@login_required
def admin_add_item_to_user(user_id):
    if current_user.role != 'admin':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('catalog'))
    
    item_id = int(request.form.get('item_id'))
    quantity = int(request.form.get('quantity', 1))
    success, message = admin_add_item_to_inventory(user_id, item_id, quantity)
    flash(message, 'success' if success else 'danger')
    
    return redirect(url_for('admin_user_detail', user_id=user_id))

@app.route('/admin/user/<int:user_id>/add_item_no_stock', methods=['POST'])
@login_required
def admin_add_item_to_user_no_stock(user_id):
    if current_user.role != 'admin':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('catalog'))
    
    item_id = int(request.form.get('item_id'))
    quantity = int(request.form.get('quantity', 1))
    success, message = admin_add_item_to_inventory_no_stock_check(user_id, item_id, quantity)
    flash(message, 'success' if success else 'danger')
    
    return redirect(url_for('admin_user_detail', user_id=user_id))

# ============ РЫНОК (ТОРГОВЛЯ МЕЖДУ ИГРОКАМИ) ============

@app.route('/market')
@login_required
def market():
    item_filter = request.args.get('item_id', '')
    offers = get_active_market_offers(exclude_user_id=current_user.id, item_filter=item_filter if item_filter else None)
    all_items = get_all_items_list()
    return render_template('market.html', offers=offers, all_items=all_items)

@app.route('/market/sell', methods=['GET', 'POST'])
@login_required
def market_sell():
    if request.method == 'POST':
        item_id = int(request.form['item_id'])
        quantity = int(request.form['quantity'])
        price = int(request.form['price'])
        
        success, message = create_market_offer(current_user.id, item_id, quantity, price)
        flash(message, 'success' if success else 'danger')
        
        if success:
            return redirect(url_for('market_sell'))  # Остаёмся на той же странице
    
    # GET - показываем форму
    inventory_items = get_user_inventory(current_user.id)
    
    # Получаем активные предложения пользователя
    user_offers = get_active_market_offers(exclude_user_id=None)  # получаем все
    user_offers = [offer for offer in user_offers if offer['seller_id'] == current_user.id]
    
    return render_template('market_sell.html', inventory=inventory_items, offers=user_offers)

@app.route('/market/buy/<int:offer_id>', methods=['POST'])
@login_required
def market_buy(offer_id):
    quantity = int(request.form.get('quantity', 1))
    success, message = buy_from_market(current_user.id, offer_id, quantity)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('market'))

@app.route('/market/cancel/<int:offer_id>', methods=['POST'])
@login_required
def market_cancel(offer_id):
    success, message = cancel_market_offer(offer_id, current_user.id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('market'))

# ============ ИСТОРИЯ ТРАНЗАКЦИЙ ============

@app.route('/transactions')
@login_required
def transactions():
    limit = request.args.get('limit', 50, type=int)
    player_tx = get_player_transactions(current_user.id, limit)
    
    # Также получаем покупки в магазине из таблицы transactions
    conn = get_connection()
    shop_tx = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT 'shop_purchase' as type, transaction_date as date, quantity, price_per_unit, total_amount, i.name as item_name, 'Магазин' as other_party
            FROM transactions t
            JOIN items i ON t.item_id = i.id
            WHERE t.user_id = %s AND t.transaction_type = 'purchase'
            ORDER BY transaction_date DESC
            LIMIT %s
        ''', (current_user.id, limit))
        shop_tx = cursor.fetchall()
        cursor.close()
        conn.close()
    
    # Объединяем и сортируем
    all_tx = player_tx + shop_tx
    all_tx.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template('transactions.html', transactions=all_tx[:limit])

# ============ ГРАФИКИ ЦЕН ============

@app.route('/analytics')
@login_required
def analytics():
    items = get_all_items_list()
    return render_template('analytics.html', items=items)

@app.route('/api/price_history/<int:item_id>')
@login_required
def api_price_history(item_id):
    days = request.args.get('days', 30, type=int)
    history = get_item_price_history(item_id, days)
    return jsonify(history)


# ============ АДМИН: УПРАВЛЕНИЕ ПРЕДМЕТАМИ ============

@app.route('/admin/edit_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_item(item_id):
    if current_user.role != 'admin':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('catalog'))
    
    item = get_item_full(item_id)
    if not item:
        flash('Предмет не найден', 'danger')
        return redirect(url_for('admin_panel'))
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = int(request.form['price'])
        category = request.form['category']
        stock = int(request.form['stock'])
        image_url = request.form.get('image_url', '')
        
        success, message = update_item_full(item_id, name, description, price, category, stock, image_url)
        flash(message, 'success' if success else 'danger')
        return redirect(url_for('admin_panel'))
    
    return render_template('admin_edit_item.html', item=item)

# ============ АДМИН: УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ============

@app.route('/admin/create_user', methods=['GET', 'POST'])
@login_required
def admin_create_user():
    if current_user.role != 'admin':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('catalog'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        balance = int(request.form['balance'])
        
        success, message = create_user_admin(username, password, role, balance)
        flash(message, 'success' if success else 'danger')
        return redirect(url_for('admin_users'))
    
    return render_template('admin_create_user.html')

@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    if current_user.role != 'admin':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('catalog'))
    
    user = get_user_by_id_admin(user_id)
    if not user:
        flash('Пользователь не найден', 'danger')
        return redirect(url_for('admin_users'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        balance = int(request.form.get('balance')) if request.form.get('balance') else None
        
        success, message = update_user_admin(user_id, username, password if password else None, role, balance)
        flash(message, 'success' if success else 'danger')
        return redirect(url_for('admin_users'))
    
    return render_template('admin_edit_user.html', user=user)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if current_user.role != 'admin':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('catalog'))
    
    if user_id == current_user.id:
        flash('Нельзя удалить самого себя', 'danger')
        return redirect(url_for('admin_users'))
    
    success, message = delete_user_admin(user_id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('admin_users'))

@app.route('/admin/assign_moderator/<int:user_id>', methods=['POST'])
@login_required
def admin_assign_moderator(user_id):
    if current_user.role != 'admin':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('catalog'))
    
    success, message = assign_moderator_role(user_id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('admin_users'))

# ============ АДМИН: ВИЗУАЛЬНЫЙ ПРОСМОТР БД ============

@app.route('/admin/database')
@login_required
def admin_database():
    if current_user.role != 'admin':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('catalog'))
    
    tables = get_all_tables()
    selected_table = request.args.get('table', '')
    table_data = []
    table_columns = []
    table_schema = []
    
    if selected_table and selected_table in tables:
        table_columns, table_data = get_table_data(selected_table)
        table_schema = get_table_schema(selected_table)
    
    return render_template('admin_database.html', 
                         tables=tables, 
                         selected_table=selected_table,
                         table_columns=table_columns,
                         table_data=table_data,
                         table_schema=table_schema)

# ============ МОДЕРАТОР: ПРОСМОТР ИНВЕНТАРЕЙ ============

@app.route('/moderator/inventories')
@login_required
def moderator_inventories():
    # Только для администратора
    if current_user.role != 'admin':
        flash('Доступ запрещён. Эта страница только для администратора.', 'danger')
        return redirect(url_for('catalog'))
    
    inventories = get_all_users_inventory()
    return render_template('moderator_inventories.html', inventories=inventories)

@app.route('/moderator/stock')
@login_required
def moderator_stock():
    if current_user.role not in ['moderator', 'admin']:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('catalog'))
    
    items = get_all_items_for_admin()
    return render_template('moderator_stock.html', items=items)

@app.route('/moderator/update_stock/<int:item_id>', methods=['POST'])
@login_required
def moderator_update_stock(item_id):
    if current_user.role not in ['moderator', 'admin']:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('catalog'))
    
    new_stock = int(request.form.get('stock', 0))
    success, message = update_item_stock_moderator(item_id, new_stock)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('moderator_stock'))


# ============ МОДЕРАТОР: ПРОСМОТР ИНВЕНТАРЕЙ ============

@app.route('/moderator/users')
@login_required
def moderator_users():
    if current_user.role not in ['moderator', 'admin']:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('catalog'))
    
    users = get_all_users_for_moderator()
    return render_template('moderator_users.html', users=users)

@app.route('/moderator/user/<int:user_id>')
@login_required
def moderator_user_inventory(user_id):
    if current_user.role not in ['moderator', 'admin']:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('catalog'))
    
    user = get_user_by_id_admin(user_id)
    if not user:
        flash('Пользователь не найден', 'danger')
        return redirect(url_for('moderator_users'))
    
    inventory = get_user_inventory_readonly(user_id)
    return render_template('moderator_user_inventory.html', user=user, inventory=inventory)


# ===============================================================================

if __name__ == '__main__':
    app.run(debug=True)