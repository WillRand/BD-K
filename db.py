import mysql.connector
from mysql.connector import Error
import random

# Настройки подключения к БД
config = {
    'user': 'shop_user',     
    'password': '1234',  
    'host': 'localhost',
    'database': 'game_shop',
    'autocommit': True
}

def get_connection():
    """Создаёт и возвращает подключение к базе данных"""
    try:
        conn = mysql.connector.connect(**config)
        return conn
    except Error as e:
        print(f"Ошибка подключения к MySQL: {e}")
        return None

def init_db():
    """Создаёт таблицы, если их нет"""
    conn = get_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    # Таблица для статистики игровых действий
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_stats (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            action_type VARCHAR(50) NOT NULL,  -- 'wheel', 'hunt', 'chest'
            result VARCHAR(50),                 -- 'win', 'lose'
            reward_type VARCHAR(50),            -- 'coins', 'item'
            reward_value INT,                   -- количество монет или ID предмета
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(50) DEFAULT 'user',
            balance INT DEFAULT 1000,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица предметов магазина (с учётом количества на складе)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            price INT NOT NULL CHECK (price >= 0),
            category VARCHAR(50),
            rarity VARCHAR(50) DEFAULT 'common',
            level_required INT DEFAULT 1,
            slot VARCHAR(50) DEFAULT 'other',
            durability INT DEFAULT 100,
            bonus_stats TEXT,
            stock INT NOT NULL DEFAULT 0 CHECK (stock >= 0),
            image_url VARCHAR(500),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица инвентаря игрока (с количеством каждого предмета)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            item_id INT NOT NULL,
            quantity INT NOT NULL DEFAULT 1 CHECK (quantity > 0),
            purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
            UNIQUE KEY unique_user_item (user_id, item_id)
        )
    ''')
    
    # Таблица для истории покупок/продаж 
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            item_id INT NOT NULL,
            quantity INT NOT NULL,
            transaction_type ENUM('purchase', 'sale', 'admin_grant', 'admin_remove') NOT NULL,
            price_per_unit INT NOT NULL,
            total_amount INT NOT NULL,
            transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
        )
    ''')

    # Таблица для предложений игроков (рынок)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_offers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            seller_id INT NOT NULL,
            item_id INT NOT NULL,
            quantity INT NOT NULL CHECK (quantity > 0),
            price_per_unit INT NOT NULL CHECK (price_per_unit >= 0),
            status ENUM('active', 'sold', 'cancelled') DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sold_at TIMESTAMP NULL,
            FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS player_transactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            offer_id INT NOT NULL,
            item_id INT NOT NULL,
            quantity INT NOT NULL,
            price_per_unit INT NOT NULL,
            total_amount INT NOT NULL,
            transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (offer_id) REFERENCES market_offers(id) ON DELETE CASCADE,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
        )
    ''')
    
    # Таблица участников сделок
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transaction_participants (
            id INT AUTO_INCREMENT PRIMARY KEY,
            transaction_id INT NOT NULL,
            user_id INT NOT NULL,
            role ENUM('buyer', 'seller') NOT NULL,
            FOREIGN KEY (transaction_id) REFERENCES player_transactions(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE KEY unique_participant (transaction_id, user_id)
        )
    ''')

    # Таблица для предложений игроков (рынок)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_offers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            seller_id INT NOT NULL,
            item_id INT NOT NULL,
            quantity INT NOT NULL CHECK (quantity > 0),
            price_per_unit INT NOT NULL CHECK (price_per_unit >= 0),
            status ENUM('active', 'sold', 'cancelled') DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sold_at TIMESTAMP NULL,
            FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
        )
    ''')

    # Таблица для сделок между игроками
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS player_transactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            offer_id INT NOT NULL,
            buyer_id INT NOT NULL,
            seller_id INT NOT NULL,
            item_id INT NOT NULL,
            quantity INT NOT NULL,
            price_per_unit INT NOT NULL,
            total_amount INT NOT NULL,
            transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (offer_id) REFERENCES market_offers(id) ON DELETE CASCADE,
            FOREIGN KEY (buyer_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
        )
    ''')
    
    cursor.close()
    conn.close()
    print("Таблицы успешно созданы!")

def add_test_items():
    """Добавляет тестовые предметы в магазин"""
    conn = get_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM items")
    count = cursor.fetchone()[0]
    
    if count == 0:
        items = [
            ("Меч огня", "Наносит 50-70 урона", 500, "weapon", "epic", 10, "weapon", 100, '{"strength": 8, "fire_damage": 15}', 10, "/static/images/sword.png"),
            ("Железный щит", "Блокирует 30% урона", 300, "armor", "rare", 5, "body", 120, '{"defense": 25}', 15, "/static/images/shield.png"),
            ("Зелье здоровья", "Восстанавливает 50 HP", 100, "potion", "common", 1, "other", 1, '{"heal": 50}', 50, "/static/images/potion.png"),
            ("Плащ невидимости", "Скрывает на 10 секунд", 800, "cosmetic", "legendary", 20, "body", 50, '{"stealth": 30, "speed": 10}', 5, "/static/images/cloak.png"),
            ("Магический посох", "Увеличивает магический урон", 650, "weapon", "epic", 12, "weapon", 90, '{"intelligence": 12, "mana": 50}', 8, "/static/images/staff.png"),
            ("Кожаная броня", "Защита +15", 250, "armor", "common", 3, "body", 80, '{"defense": 15, "agility": 3}', 20, "/static/images/leather.png"),
        ]
        
        cursor.executemany('''
            INSERT INTO items (name, description, price, category, rarity, level_required, slot, durability, bonus_stats, stock, image_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', items)
        print(f"Добавлено {len(items)} тестовых предметов")
    
    cursor.close()
    conn.close()

def add_test_user():
    """Добавляет тестового пользователя (если нет)"""
    import bcrypt
    conn = get_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    # Проверяем, есть ли пользователь
    cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'test_player'")
    count = cursor.fetchone()[0]
    
    if count == 0:
        password_hash = bcrypt.hashpw("test123".encode(), bcrypt.gensalt())
        cursor.execute('''
            INSERT INTO users (username, password_hash, role, balance)
            VALUES (%s, %s, %s, %s)
        ''', ('test_player', password_hash.decode(), 'user', 2000))
        print("Добавлен тестовый пользователь: test_player / test123")
    
    cursor.close()
    conn.close()

# ============ ФУНКЦИИ ДЛЯ РАБОТЫ С МАГАЗИНОМ ============

def get_all_items(category=None, sort_by=None, order='ASC', show_out_of_stock=True):
    """
    Получить все товары.
    show_out_of_stock: если True - показывает все, если False - только в наличии
    """
    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM items"
    params = []
    conditions = []
    
    if category and category != '':
        conditions.append("category = %s")
        params.append(category)
    
    if not show_out_of_stock:
        conditions.append("stock > 0")
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    if sort_by in ['price', 'name', 'created_at']:
        query += f" ORDER BY {sort_by} {order}"
    
    cursor.execute(query, params)
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return items

def get_item_by_id(item_id):
    """Получить предмет по ID"""
    conn = get_connection()
    if not conn:
        return None
    
    cursor = conn.cursor(dictionary=True)  # <-- ВАЖНО: dictionary=True
    cursor.execute("SELECT * FROM items WHERE id = %s", (item_id,))
    item = cursor.fetchone()
    cursor.close()
    conn.close()
    return item

def purchase_item(user_id, item_id, quantity=1):
    """
    Покупка предмета игроком.
    Возвращает: (success, message)
    """
    if quantity <= 0:
        return False, "Количество должно быть положительным"
    
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения к БД"
    
    cursor = conn.cursor(dictionary=True)  # <-- ВАЖНО: dictionary=True
    
    try:
        # 1. Получаем информацию о предмете
        cursor.execute("SELECT id, name, price, stock FROM items WHERE id = %s", (item_id,))
        item = cursor.fetchone()
        
        if not item:
            return False, "Предмет не найден"
            
        if item['stock'] == 0:
            return False, "Товар временно отсутствует (ожидается поставка)"

        if item['stock'] < quantity:
            return False, f"Недостаточно товара. В наличии: {item['stock']}"
        
        # 2. Получаем баланс пользователя
        cursor.execute("SELECT balance FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return False, "Пользователь не найден"
        
        total_cost = item['price'] * quantity
        if user['balance'] < total_cost:
            return False, f"Недостаточно средств. Нужно: {total_cost}, у вас: {user['balance']}"
        
        # 3. Обновляем баланс пользователя
        cursor.execute("UPDATE users SET balance = balance - %s WHERE id = %s", (total_cost, user_id))
        
        # 4. Обновляем количество товара на складе
        cursor.execute("UPDATE items SET stock = stock - %s WHERE id = %s", (quantity, item_id))
        
        # 5. Обновляем инвентарь пользователя
        cursor.execute('''
            INSERT INTO inventory (user_id, item_id, quantity)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE quantity = quantity + %s
        ''', (user_id, item_id, quantity, quantity))
        
        # 6. Записываем транзакцию
        cursor.execute('''
            INSERT INTO transactions (user_id, item_id, transaction_type, quantity, price_per_unit, total_amount)
            VALUES (%s, %s, 'purchase', %s, %s, %s)
        ''', (user_id, item_id, quantity, item['price'], total_cost))
        
        conn.commit()
        return True, f"Вы купили {quantity} шт. '{item['name']}' за {total_cost} монет"
        
    except Error as e:
        conn.rollback()
        return False, f"Ошибка: {e}"
    finally:
        cursor.close()
        conn.close()
        
def sell_item(user_id, item_id, quantity=1):
    """
    Продажа предмета обратно в магазин.
    Возвращает: (success, message)
    """
    if quantity <= 0:
        return False, "Количество должно быть положительным"
    
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения к БД"
    
    cursor = conn.cursor(dictionary=True)  # <-- ВАЖНО: dictionary=True
    
    try:
        # 1. Проверяем, есть ли предмет в инвентаре пользователя
        cursor.execute('''
            SELECT quantity FROM inventory 
            WHERE user_id = %s AND item_id = %s
        ''', (user_id, item_id))
        inv_item = cursor.fetchone()
        
        if not inv_item or inv_item['quantity'] < quantity:
            return False, f"У вас нет такого предмета в нужном количестве"
        
        # 2. Получаем цену предмета (продажа за 50% от цены покупки)
        cursor.execute("SELECT id, name, price FROM items WHERE id = %s", (item_id,))
        item = cursor.fetchone()
        
        if not item:
            return False, "Предмет не найден"
        
        sell_price = item['price'] // 2  # Продажа за половину цены
        total_refund = sell_price * quantity
        
        # 3. Обновляем баланс пользователя
        cursor.execute("UPDATE users SET balance = balance + %s WHERE id = %s", (total_refund, user_id))
        
        # 4. Возвращаем товар на склад
        cursor.execute("UPDATE items SET stock = stock + %s WHERE id = %s", (quantity, item_id))
        
        # 5. Обновляем инвентарь
        if inv_item['quantity'] == quantity:
            cursor.execute("DELETE FROM inventory WHERE user_id = %s AND item_id = %s", (user_id, item_id))
        else:
            cursor.execute('''
                UPDATE inventory SET quantity = quantity - %s 
                WHERE user_id = %s AND item_id = %s
            ''', (quantity, user_id, item_id))
        
        # 6. Записываем транзакцию
        cursor.execute('''
            INSERT INTO transactions (user_id, item_id, transaction_type, quantity, price_per_unit, total_amount)
            VALUES (%s, %s, 'sale', %s, %s, %s)
        ''', (user_id, item_id, quantity, sell_price, total_refund))
        
        conn.commit()
        return True, f"Вы продали {quantity} шт. '{item['name']}' за {total_refund} монет"
        
    except Error as e:
        conn.rollback()
        return False, f"Ошибка: {e}"
    finally:
        cursor.close()
        conn.close()

def get_user_inventory(user_id):
    """Получить инвентарь пользователя с количеством"""
    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)  # <-- ВАЖНО: dictionary=True
    cursor.execute('''
        SELECT i.*, inv.quantity, inv.purchased_at
        FROM inventory inv
        JOIN items i ON inv.item_id = i.id
        WHERE inv.user_id = %s
        ORDER BY inv.purchased_at DESC
    ''', (user_id,))
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return items
    
def get_user_balance(user_id):
    """Получить баланс пользователя"""
    conn = get_connection()
    if not conn:
        return 0
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT balance FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user['balance'] if user else 0

# ============ АДМИН-ФУНКЦИИ ============

def add_item(name, description, price, category, stock, image_url):
    """Добавить новый предмет в магазин"""
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения"
    
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO items (name, description, price, category, stock, image_url)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (name, description, price, category, stock, image_url))
        conn.commit()
        return True, "Предмет добавлен"
    except Error as e:
        return False, f"Ошибка: {e}"
    finally:
        cursor.close()
        conn.close()

def update_item_stock(item_id, new_stock):
    """Изменить количество товара на складе (админ)"""
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения"
    
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE items SET stock = %s WHERE id = %s", (new_stock, item_id))
        conn.commit()
        return True, "Количество обновлено"
    except Error as e:
        return False, f"Ошибка: {e}"
    finally:
        cursor.close()
        conn.close()

def update_item_price(item_id, new_price):
    """Изменить цену предмета (админ)"""
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения"
    
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE items SET price = %s WHERE id = %s", (new_price, item_id))
        conn.commit()
        return True, "Цена обновлена"
    except Error as e:
        return False, f"Ошибка: {e}"
    finally:
        cursor.close()
        conn.close()

def delete_item(item_id):
    """Удалить предмет из магазина (админ)"""
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения"
    
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM items WHERE id = %s", (item_id,))
        conn.commit()
        return True, "Предмет удалён"
    except Error as e:
        return False, f"Ошибка: {e}"
    finally:
        cursor.close()
        conn.close()

def get_all_users():
    """Получить всех пользователей (для админа)"""
    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, role, balance, created_at FROM users")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return users

def get_low_stock_items(threshold=5):
    """Получить товары с малым остатком (для админа)"""
    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM items WHERE stock <= %s AND stock > 0", (threshold,))
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return items


# ============ АДМИН-ФУНКЦИИ ДЛЯ УПРАВЛЕНИЯ ПОЛЬЗОВАТЕЛЯМИ ============

def get_all_users_with_details():
    """Получить всех пользователей с деталями (для админа)"""
    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT id, username, role, balance, created_at 
        FROM users 
        ORDER BY id
    ''')
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return users

def update_user_balance(user_id, new_balance):
    """Изменить баланс пользователя (админ)"""
    if new_balance < 0:
        return False, "Баланс не может быть отрицательным"
    
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения"
    
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET balance = %s WHERE id = %s", (new_balance, user_id))
        conn.commit()
        return True, f"Баланс пользователя обновлён на {new_balance} монет"
    except Error as e:
        return False, f"Ошибка: {e}"
    finally:
        cursor.close()
        conn.close()

def get_user_inventory_admin(user_id):
    """Получить инвентарь конкретного пользователя (для админа)"""
    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT i.id, i.name, i.description, i.price, i.category, inv.quantity, inv.purchased_at
        FROM inventory inv
        JOIN items i ON inv.item_id = i.id
        WHERE inv.user_id = %s
        ORDER BY inv.purchased_at DESC
    ''', (user_id,))
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return items

def get_user_by_id_admin(user_id):
    """Получить информацию о пользователе по ID (для админа)"""
    conn = get_connection()
    if not conn:
        return None
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, role, balance, created_at FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def admin_remove_item_from_inventory(user_id, item_id, quantity=1):
    """Удалить предмет из инвентаря пользователя (админ)"""
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения"
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Проверяем наличие предмета
        cursor.execute('''
            SELECT quantity FROM inventory 
            WHERE user_id = %s AND item_id = %s
        ''', (user_id, item_id))
        inv_item = cursor.fetchone()
        
        if not inv_item:
            return False, "У пользователя нет такого предмета"
        
        if inv_item['quantity'] <= quantity:
            # Удаляем полностью
            cursor.execute('''
                DELETE FROM inventory WHERE user_id = %s AND item_id = %s
            ''', (user_id, item_id))
        else:
            # Уменьшаем количество
            cursor.execute('''
                UPDATE inventory SET quantity = quantity - %s 
                WHERE user_id = %s AND item_id = %s
            ''', (quantity, user_id, item_id))
        
        # Возвращаем товар на склад
        cursor.execute('''
            UPDATE items SET stock = stock + %s WHERE id = %s
        ''', (quantity, item_id))
        
        conn.commit()
        return True, f"Предмет удалён из инвентаря пользователя"
    except Error as e:
        conn.rollback()
        return False, f"Ошибка: {e}"
    finally:
        cursor.close()
        conn.close()

def admin_add_item_to_inventory(user_id, item_id, quantity=1):
    """Добавить предмет в инвентарь пользователя (админ)"""
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения"
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Проверяем, есть ли предмет на складе
        cursor.execute("SELECT stock, name FROM items WHERE id = %s", (item_id,))
        item = cursor.fetchone()
        
        if not item:
            return False, "Предмет не найден"
        
        if item['stock'] < quantity:
            return False, f"Недостаточно товара на складе. В наличии: {item['stock']}"
        
        # Добавляем в инвентарь
        cursor.execute('''
            INSERT INTO inventory (user_id, item_id, quantity)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE quantity = quantity + %s
        ''', (user_id, item_id, quantity, quantity))
        
        # Уменьшаем склад
        cursor.execute('''
            UPDATE items SET stock = stock - %s WHERE id = %s
        ''', (quantity, item_id))
        
        conn.commit()
        return True, f"Предмет '{item['name']}' добавлен пользователю"
    except Error as e:
        conn.rollback()
        return False, f"Ошибка: {e}"
    finally:
        cursor.close()
        conn.close()

def get_all_items_for_admin():
    """Получить все предметы для админ-панели (включая все, без фильтров)"""
    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT *, CASE WHEN stock = 0 THEN 'out' WHEN stock <= 5 THEN 'low' ELSE 'ok' END as stock_status FROM items ORDER BY id")
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return items


def admin_add_item_to_inventory_no_stock_check(user_id, item_id, quantity=1):
    """
    Добавить предмет в инвентарь пользователя (БЕЗ проверки склада).
    Используется админом.
    """
    if quantity <= 0:
        return False, "Количество должно быть положительным"
    
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения"
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Получаем информацию о предмете (даже если stock = 0)
        cursor.execute("SELECT id, name, price FROM items WHERE id = %s", (item_id,))
        item = cursor.fetchone()
        
        if not item:
            return False, "Предмет не найден"
        
        # Добавляем в инвентарь
        cursor.execute('''
            INSERT INTO inventory (user_id, item_id, quantity)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE quantity = quantity + %s
        ''', (user_id, item_id, quantity, quantity))
        
        # НЕ уменьшаем склад! (это главное отличие)
        
        # Записываем транзакцию (особый тип для админ-выдачи)
        cursor.execute('''
             INSERT INTO transactions (user_id, item_id, transaction_type, quantity, price_per_unit, total_amount)
            VALUES (%s, %s, 'admin_grant', %s, %s, %s)
        ''', (user_id, item_id, quantity, 0, 0))
        
        conn.commit()
        return True, f"Предмет '{item['name']}' (x{quantity}) выдан пользователю (независимо от склада)"
    except Error as e:
        conn.rollback()
        return False, f"Ошибка: {e}"
    finally:
        cursor.close()
        conn.close()

def update_item_stock_admin(item_id, new_stock):
    """Изменить количество товара на складе (админ)"""
    if new_stock < 0:
        return False, "Количество не может быть отрицательным"
    
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения"
    
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE items SET stock = %s WHERE id = %s", (new_stock, item_id))
        conn.commit()
        
        if new_stock == 0:
            return True, "Товар помечен как 'Ожидается поставка'"
        else:
            return True, f"Количество обновлено: {new_stock} шт."
    except Error as e:
        return False, f"Ошибка: {e}"
    finally:
        cursor.close()
        conn.close()

# ============ РЫНОК (ТОРГОВЛЯ МЕЖДУ ИГРОКАМИ) ============

def create_market_offer(seller_id, item_id, quantity, price_per_unit):
    """Выставить предмет на продажу"""
    if quantity <= 0 or price_per_unit < 0:
        return False, "Некорректные данные"
    
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения"
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Проверяем, есть ли у продавца такой предмет в инвентаре
        cursor.execute('''
            SELECT quantity FROM inventory 
            WHERE user_id = %s AND item_id = %s
        ''', (seller_id, item_id))
        inv = cursor.fetchone()
        
        if not inv or inv['quantity'] < quantity:
            return False, "У вас нет столько предметов"
        
        # Уменьшаем инвентарь продавца
        if inv['quantity'] == quantity:
            cursor.execute("DELETE FROM inventory WHERE user_id = %s AND item_id = %s", (seller_id, item_id))
        else:
            cursor.execute('''
                UPDATE inventory SET quantity = quantity - %s 
                WHERE user_id = %s AND item_id = %s
            ''', (quantity, seller_id, item_id))
        
        # Создаём предложение
        cursor.execute('''
            INSERT INTO market_offers (seller_id, item_id, quantity, price_per_unit)
            VALUES (%s, %s, %s, %s)
        ''', (seller_id, item_id, quantity, price_per_unit))
        
        conn.commit()
        return True, "Предмет выставлен на продажу"
    except Error as e:
        conn.rollback()
        return False, f"Ошибка: {e}"
    finally:
        cursor.close()
        conn.close()

def get_active_market_offers(exclude_user_id=None, item_filter=None):
    """Получить активные предложения на рынке"""
    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    query = '''
        SELECT mo.*, i.name, i.description, i.category, u.username as seller_name
        FROM market_offers mo
        JOIN items i ON mo.item_id = i.id
        JOIN users u ON mo.seller_id = u.id
        WHERE mo.status = 'active'
    '''
    params = []
    
    if exclude_user_id:
        query += " AND mo.seller_id != %s"
        params.append(exclude_user_id)
    
    if item_filter:
        query += " AND mo.item_id = %s"
        params.append(item_filter)
    
    query += " ORDER BY mo.price_per_unit ASC, mo.created_at ASC"
    
    cursor.execute(query, params)
    offers = cursor.fetchall()
    cursor.close()
    conn.close()
    return offers

def buy_from_market(buyer_id, offer_id, quantity):
    """Купить предмет с рынка (P2P-сделка) - обновлённая версия"""
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения"
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Получаем информацию о предложении
        cursor.execute('''
            SELECT mo.*, i.name, u.balance as seller_balance
            FROM market_offers mo
            JOIN items i ON mo.item_id = i.id
            JOIN users u ON mo.seller_id = u.id
            WHERE mo.id = %s AND mo.status = 'active'
        ''', (offer_id,))
        offer = cursor.fetchone()
        
        if not offer:
            return False, "Предложение уже неактивно"
        
        if quantity > offer['quantity']:
            return False, f"Доступно только {offer['quantity']} шт."
        
        total_cost = offer['price_per_unit'] * quantity
        
        # Проверяем баланс покупателя
        cursor.execute("SELECT balance FROM users WHERE id = %s", (buyer_id,))
        buyer = cursor.fetchone()
        
        if buyer['balance'] < total_cost:
            return False, f"Недостаточно средств. Нужно: {total_cost}"
        
        # Проверяем, что покупатель не продавец
        if buyer_id == offer['seller_id']:
            return False, "Нельзя приобрести свой же товар"
        
        # Переводим деньги
        cursor.execute("UPDATE users SET balance = balance - %s WHERE id = %s", (total_cost, buyer_id))
        cursor.execute("UPDATE users SET balance = balance + %s WHERE id = %s", (total_cost, offer['seller_id']))
        
        # Обновляем или закрываем предложение
        if quantity == offer['quantity']:
            cursor.execute("UPDATE market_offers SET status = 'sold', sold_at = NOW() WHERE id = %s", (offer_id,))
        else:
            cursor.execute("UPDATE market_offers SET quantity = quantity - %s WHERE id = %s", (quantity, offer_id))
        
        # Добавляем предмет покупателю в инвентарь
        cursor.execute('''
            INSERT INTO inventory (user_id, item_id, quantity)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE quantity = quantity + %s
        ''', (buyer_id, offer['item_id'], quantity, quantity))
        
        # ============ НОВАЯ ЧАСТЬ: запись сделки ============
        # 1. Создаём запись о сделке
        cursor.execute('''
            INSERT INTO player_transactions (offer_id, item_id, quantity, price_per_unit, total_amount)
            VALUES (%s, %s, %s, %s, %s)
        ''', (offer_id, offer['item_id'], quantity, offer['price_per_unit'], total_cost))
        
        transaction_id = cursor.lastrowid
        
        # 2. Добавляем участников (покупатель и продавец)
        cursor.execute('''
            INSERT INTO transaction_participants (transaction_id, user_id, role)
            VALUES (%s, %s, 'buyer'), (%s, %s, 'seller')
        ''', (transaction_id, buyer_id, transaction_id, offer['seller_id']))
        # ===================================================
        
        conn.commit()
        return True, f"Приобретено {quantity} шт. '{offer['name']}' за {total_cost} монет"
        
    except Error as e:
        conn.rollback()
        return False, f"Ошибка: {e}"
    finally:
        cursor.close()
        conn.close()

def cancel_market_offer(offer_id, user_id):
    """Отменить своё предложение и вернуть предмет"""
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения"
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute('''
            SELECT * FROM market_offers 
            WHERE id = %s AND seller_id = %s AND status = 'active'
        ''', (offer_id, user_id))
        offer = cursor.fetchone()
        
        if not offer:
            return False, "Предложение не найдено или уже закрыто"
        
        # Возвращаем предмет в инвентарь
        cursor.execute('''
            INSERT INTO inventory (user_id, item_id, quantity)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE quantity = quantity + %s
        ''', (user_id, offer['item_id'], offer['quantity'], offer['quantity']))
        
        # Закрываем предложение
        cursor.execute("UPDATE market_offers SET status = 'cancelled' WHERE id = %s", (offer_id,))
        
        conn.commit()
        return True, "Предложение отменено, предметы возвращены"
    except Error as e:
        conn.rollback()
        return False, f"Ошибка: {e}"
    finally:
        cursor.close()
        conn.close()

def get_player_transactions(user_id, limit=50):
    """
    Получить историю сделок пользователя (покупки и продажи).
    Использует новую схему с таблицей transaction_participants.
    """
    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT 
            pt.transaction_date as date,
            pt.quantity,
            pt.price_per_unit,
            pt.total_amount,
            i.name as item_name,
            CASE 
                WHEN tp.role = 'buyer' THEN 'purchase'
                ELSE 'sale'
            END as type,
            (
                SELECT u.username 
                FROM transaction_participants tp2
                JOIN users u ON tp2.user_id = u.id
                WHERE tp2.transaction_id = pt.id AND tp2.user_id != %s
                LIMIT 1
            ) as other_party
        FROM player_transactions pt
        JOIN transaction_participants tp ON tp.transaction_id = pt.id
        JOIN items i ON pt.item_id = i.id
        WHERE tp.user_id = %s
        ORDER BY pt.transaction_date DESC
        LIMIT %s
    ''', (user_id, user_id, limit))
    
    transactions = cursor.fetchall()
    cursor.close()
    conn.close()
    return transactions

def get_transaction_details(transaction_id):
    """
    Получить полную информацию о сделке по её ID.
    Возвращает словарь с данными сделки и информацией об участниках.
    """
    conn = get_connection()
    if not conn:
        return None
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT 
            pt.id,
            pt.offer_id,
            pt.item_id,
            i.name as item_name,
            pt.quantity,
            pt.price_per_unit,
            pt.total_amount,
            pt.transaction_date,
            MAX(CASE WHEN tp.role = 'buyer' THEN tp.user_id END) as buyer_id,
            MAX(CASE WHEN tp.role = 'buyer' THEN u_buyer.username END) as buyer_name,
            MAX(CASE WHEN tp.role = 'seller' THEN tp.user_id END) as seller_id,
            MAX(CASE WHEN tp.role = 'seller' THEN u_seller.username END) as seller_name
        FROM player_transactions pt
        JOIN items i ON pt.item_id = i.id
        JOIN transaction_participants tp ON tp.transaction_id = pt.id
        LEFT JOIN users u_buyer ON (tp.user_id = u_buyer.id AND tp.role = 'buyer')
        LEFT JOIN users u_seller ON (tp.user_id = u_seller.id AND tp.role = 'seller')
        WHERE pt.id = %s
        GROUP BY pt.id
    ''', (transaction_id,))
    
    transaction = cursor.fetchone()
    cursor.close()
    conn.close()
    return transaction

def get_item_price_history(item_id, days=30):
    """Получить историю цен на предмет (для графика)"""
    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT 
            DATE(transaction_date) as date,
            AVG(price_per_unit) as avg_price,
            MIN(price_per_unit) as min_price,
            MAX(price_per_unit) as max_price,
            SUM(quantity) as total_sold
        FROM player_transactions
        WHERE item_id = %s 
        AND transaction_date >= DATE_SUB(NOW(), INTERVAL %s DAY)
        GROUP BY DATE(transaction_date)
        ORDER BY date ASC
    ''', (item_id, days))
    history = cursor.fetchall()
    cursor.close()
    conn.close()
    return history

def get_all_items_list():
    """Получить список всех предметов для выбора в фильтрах"""
    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name, category FROM items ORDER BY name")
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return items


# ============ УПРАВЛЕНИЕ ПРЕДМЕТАМИ (РАСШИРЕННОЕ) ============

def update_item_full(item_id, name, description, price, category, stock, image_url):
    """Полное обновление предмета (админ)"""
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения"
    
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE items 
            SET name = %s, description = %s, price = %s, category = %s, stock = %s, image_url = %s
            WHERE id = %s
        ''', (name, description, price, category, stock, image_url, item_id))
        conn.commit()
        return True, "Предмет обновлён"
    except Error as e:
        return False, f"Ошибка: {e}"
    finally:
        cursor.close()
        conn.close()

def get_item_full(item_id):
    """Получить полную информацию о предмете"""
    conn = get_connection()
    if not conn:
        return None
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM items WHERE id = %s", (item_id,))
    item = cursor.fetchone()
    cursor.close()
    conn.close()
    return item

# ============ УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ (РАСШИРЕННОЕ) ============

def create_user_admin(username, password, role='user', balance=1000):
    """Создать пользователя (админ)"""
    import bcrypt
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения"
    
    cursor = conn.cursor()
    try:
        # Проверяем, существует ли пользователь
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return False, "Пользователь уже существует"
        
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        cursor.execute('''
            INSERT INTO users (username, password_hash, role, balance)
            VALUES (%s, %s, %s, %s)
        ''', (username, hashed.decode(), role, balance))
        conn.commit()
        return True, f"Пользователь '{username}' создан"
    except Error as e:
        return False, f"Ошибка: {e}"
    finally:
        cursor.close()
        conn.close()

def update_user_admin(user_id, username=None, password=None, role=None, balance=None):
    """Обновить данные пользователя (админ)"""
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения"
    
    cursor = conn.cursor()
    try:
        updates = []
        params = []
        
        if username:
            updates.append("username = %s")
            params.append(username)
        if password:
            import bcrypt
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
            updates.append("password_hash = %s")
            params.append(hashed.decode())
        if role:
            updates.append("role = %s")
            params.append(role)
        if balance is not None:
            updates.append("balance = %s")
            params.append(balance)
        
        if not updates:
            return False, "Нет данных для обновления"
        
        params.append(user_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = %s"
        cursor.execute(query, params)
        conn.commit()
        return True, "Пользователь обновлён"
    except Error as e:
        return False, f"Ошибка: {e}"
    finally:
        cursor.close()
        conn.close()

def delete_user_admin(user_id):
    """Удалить пользователя (админ)"""
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения"
    
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        return True, "Пользователь удалён"
    except Error as e:
        return False, f"Ошибка: {e}"
    finally:
        cursor.close()
        conn.close()

# ============ ВИЗУАЛЬНЫЙ ПРОСМОТР БД ============

def get_all_tables():
    """Получить список всех таблиц в БД"""
    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return tables

def get_table_data(table_name):
    """Получить данные из таблицы"""
    conn = get_connection()
    if not conn:
        return [], []
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(f"SELECT * FROM {table_name}")
        data = cursor.fetchall()
        # Получаем названия колонок
        columns = list(data[0].keys()) if data else []
        return columns, data
    except Error as e:
        return [], []
    finally:
        cursor.close()
        conn.close()

def get_table_schema(table_name):
    """Получить структуру таблицы"""
    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"DESCRIBE {table_name}")
    schema = cursor.fetchall()
    cursor.close()
    conn.close()
    return schema

# ============ ФУНКЦИИ ДЛЯ МОДЕРАТОРА ============

def is_moderator_or_admin(user_role):
    """Проверка, является ли пользователь модератором или админом"""
    return user_role in ['moderator', 'admin']

def get_all_users_inventory():
    """Получить инвентари всех пользователей (для модератора)"""
    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT u.id, u.username, u.role, 
               i.id as item_id, i.name as item_name, i.category, inv.quantity
        FROM users u
        LEFT JOIN inventory inv ON u.id = inv.user_id
        LEFT JOIN items i ON inv.item_id = i.id
        ORDER BY u.username, i.name
    ''')
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data

def update_item_stock_moderator(item_id, new_stock):
    """Модератор может только пополнять склад (увеличивать количество)"""
    if new_stock < 0:
        return False, "Количество не может быть отрицательным"
    
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения"
    
    cursor = conn.cursor()
    try:
        # Модератор может только увеличивать или уменьшать до 0
        cursor.execute("UPDATE items SET stock = %s WHERE id = %s", (new_stock, item_id))
        conn.commit()
        return True, f"Количество обновлено: {new_stock} шт."
    except Error as e:
        return False, f"Ошибка: {e}"
    finally:
        cursor.close()
        conn.close()

def assign_moderator_role(user_id):
    """Назначить пользователя модератором (только админ)"""
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения"
    
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET role = 'moderator' WHERE id = %s", (user_id,))
        conn.commit()
        return True, "Пользователь назначен модератором"
    except Error as e:
        return False, f"Ошибка: {e}"
    finally:
        cursor.close()
        conn.close()



# ============ ФУНКЦИИ ДЛЯ МОДЕРАТОРА ============

def get_all_users_for_moderator():
    """Получить список всех пользователей (для модератора)"""
    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT id, username, role, balance, created_at 
        FROM users 
        ORDER BY username
    ''')
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return users

def get_user_inventory_readonly(user_id):
    """Получить инвентарь пользователя только для чтения (без количества, только названия)"""
    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT i.id, i.name, i.description, i.category, i.price, inv.quantity, inv.purchased_at
        FROM inventory inv
        JOIN items i ON inv.item_id = i.id
        WHERE inv.user_id = %s
        ORDER BY inv.purchased_at DESC
    ''', (user_id,))
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return items

# ============ РАСШИРЕННАЯ АНАЛИТИКА ============

def get_popular_items(period='all', limit=10):
    """
    Получить самые покупаемые предметы за период
    period: 'day', 'week', 'month', 'year', 'all'
    """
    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    
    # Определяем интервал
    interval = ""
    if period == 'day':
        interval = "AND transaction_date >= DATE_SUB(NOW(), INTERVAL 1 DAY)"
    elif period == 'week':
        interval = "AND transaction_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
    elif period == 'month':
        interval = "AND transaction_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)"
    elif period == 'year':
        interval = "AND transaction_date >= DATE_SUB(NOW(), INTERVAL 365 DAY)"
    
    query = f'''
        SELECT i.id, i.name, i.category, SUM(t.quantity) as total_sold
        FROM transactions t
        JOIN items i ON t.item_id = i.id
        WHERE t.transaction_type = 'purchase'
        {interval}
        GROUP BY i.id, i.name, i.category
        ORDER BY total_sold DESC
        LIMIT %s
    '''
    
    cursor.execute(query, (limit,))
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return items

def get_category_stats(period='all'):
    """Статистика покупок по категориям за период"""
    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    
    interval = ""
    if period == 'day':
        interval = "AND transaction_date >= DATE_SUB(NOW(), INTERVAL 1 DAY)"
    elif period == 'week':
        interval = "AND transaction_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
    elif period == 'month':
        interval = "AND transaction_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)"
    elif period == 'year':
        interval = "AND transaction_date >= DATE_SUB(NOW(), INTERVAL 365 DAY)"
    
    query = f'''
        SELECT i.category, SUM(t.quantity) as total_sold
        FROM transactions t
        JOIN items i ON t.item_id = i.id
        WHERE t.transaction_type = 'purchase'
        {interval}
        GROUP BY i.category
        ORDER BY total_sold DESC
    '''
    
    cursor.execute(query)
    stats = cursor.fetchall()
    cursor.close()
    conn.close()
    return stats

def get_sales_dynamics(period='week'):
    """Динамика продаж по дням/месяцам"""
    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    
    if period == 'day':
        # Последние 24 часа с группировкой по часам
        query = '''
            SELECT 
                DATE_FORMAT(transaction_date, '%Y-%m-%d %H:00') as date,
                COUNT(*) as sales_count,
                SUM(total_amount) as total_amount
            FROM transactions
            WHERE transaction_type = 'purchase'
                AND transaction_date >= DATE_SUB(NOW(), INTERVAL 1 DAY)
            GROUP BY DATE_FORMAT(transaction_date, '%Y-%m-%d %H:00')
            ORDER BY date ASC
        '''
    elif period == 'week':
        # Последние 7 дней с группировкой по дням
        query = '''
            SELECT 
                DATE(transaction_date) as date,
                COUNT(*) as sales_count,
                SUM(total_amount) as total_amount
            FROM transactions
            WHERE transaction_type = 'purchase'
                AND transaction_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY DATE(transaction_date)
            ORDER BY date ASC
        '''
    elif period == 'month':
        # Последние 30 дней с группировкой по дням
        query = '''
            SELECT 
                DATE(transaction_date) as date,
                COUNT(*) as sales_count,
                SUM(total_amount) as total_amount
            FROM transactions
            WHERE transaction_type = 'purchase'
                AND transaction_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY DATE(transaction_date)
            ORDER BY date ASC
        '''
    else:  # year
        # Последние 12 месяцев с группировкой по месяцам
        query = '''
            SELECT 
                DATE_FORMAT(transaction_date, '%Y-%m') as date,
                COUNT(*) as sales_count,
                SUM(total_amount) as total_amount
            FROM transactions
            WHERE transaction_type = 'purchase'
                AND transaction_date >= DATE_SUB(NOW(), INTERVAL 365 DAY)
            GROUP BY DATE_FORMAT(transaction_date, '%Y-%m')
            ORDER BY date ASC
        '''
    
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data

def get_market_price_history_advanced(item_id, period='week'):
    """
    Получить историю цен рынка с разной детализацией
    period: 'day' (15 мин), 'week' (день), 'month' (день), 'year' (месяц)
    """
    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    
    if period == 'day':
        # За последние 24 часа с группировкой по 15 минут
        query = '''
            SELECT 
                DATE_FORMAT(transaction_date, '%%Y-%%m-%%d %%H:%%i:00') as date,
                AVG(price_per_unit) as avg_price,
                MIN(price_per_unit) as min_price,
                MAX(price_per_unit) as max_price,
                SUM(quantity) as total_sold
            FROM player_transactions
            WHERE item_id = %s 
                AND transaction_date >= DATE_SUB(NOW(), INTERVAL 1 DAY)
            GROUP BY UNIX_TIMESTAMP(transaction_date) DIV 900
            ORDER BY transaction_date ASC
        '''
    elif period == 'week':
        # За последние 7 дней с группировкой по дням
        query = '''
            SELECT 
                DATE(transaction_date) as date,
                AVG(price_per_unit) as avg_price,
                MIN(price_per_unit) as min_price,
                MAX(price_per_unit) as max_price,
                SUM(quantity) as total_sold
            FROM player_transactions
            WHERE item_id = %s 
                AND transaction_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY DATE(transaction_date)
            ORDER BY date ASC
        '''
    elif period == 'month':
        # За последние 30 дней с группировкой по дням
        query = '''
            SELECT 
                DATE(transaction_date) as date,
                AVG(price_per_unit) as avg_price,
                MIN(price_per_unit) as min_price,
                MAX(price_per_unit) as max_price,
                SUM(quantity) as total_sold
            FROM player_transactions
            WHERE item_id = %s 
                AND transaction_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY DATE(transaction_date)
            ORDER BY date ASC
        '''
    else:  # year
        # За последние 12 месяцев с группировкой по месяцам
        query = '''
            SELECT 
                DATE_FORMAT(transaction_date, '%%Y-%%m') as date,
                AVG(price_per_unit) as avg_price,
                MIN(price_per_unit) as min_price,
                MAX(price_per_unit) as max_price,
                SUM(quantity) as total_sold
            FROM player_transactions
            WHERE item_id = %s 
                AND transaction_date >= DATE_SUB(NOW(), INTERVAL 365 DAY)
            GROUP BY DATE_FORMAT(transaction_date, '%%Y-%%m')
            ORDER BY date ASC
        '''
    
    cursor.execute(query, (item_id,))
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data

def get_total_stats(period='all'):
    """Получить общую статистику за период"""
    conn = get_connection()
    if not conn:
        return {}
    
    cursor = conn.cursor(dictionary=True)
    
    interval = ""
    if period == 'day':
        interval = "AND transaction_date >= DATE_SUB(NOW(), INTERVAL 1 DAY)"
    elif period == 'week':
        interval = "AND transaction_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
    elif period == 'month':
        interval = "AND transaction_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)"
    elif period == 'year':
        interval = "AND transaction_date >= DATE_SUB(NOW(), INTERVAL 365 DAY)"
    
    query = f'''
        SELECT 
            COUNT(*) as total_transactions,
            SUM(quantity) as total_items_sold,
            SUM(total_amount) as total_revenue
        FROM transactions
        WHERE transaction_type = 'purchase'
        {interval}
    '''
    
    cursor.execute(query)
    stats = cursor.fetchone()
    cursor.close()
    conn.close()
    return stats or {}

def add_test_transactions():
    """Добавляет тестовые транзакции для аналитики"""
    conn = get_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    # Проверяем, есть ли уже транзакции
    cursor.execute("SELECT COUNT(*) FROM transactions")
    count = cursor.fetchone()[0]
    
    if count == 0:
        # Получаем пользователя и предметы
        cursor.execute("SELECT id FROM users WHERE username = 'test_player'")
        user = cursor.fetchone()
        cursor.execute("SELECT id, price FROM items LIMIT 4")
        items = cursor.fetchall()
        
        if user and items:
            import random
            from datetime import datetime, timedelta
            
            for i in range(30):  # 30 тестовых транзакций
                item = random.choice(items)
                quantity = random.randint(1, 3)
                total = item[1] * quantity
                date = datetime.now() - timedelta(days=random.randint(0, 30))
                
                cursor.execute('''
                    INSERT INTO transactions (user_id, item_id, transaction_type, quantity, price_per_unit, total_amount, transaction_date)
                    VALUES (%s, %s, 'purchase', %s, %s, %s, %s)
                ''', (user[0], item[0], quantity, item[1], total, date))
        
        conn.commit()
        print("Добавлены тестовые транзакции")
    
    cursor.close()
    conn.close()


# ============ ИГРОВЫЕ МЕХАНИКИ ============

# Конфигурация наград
WHEEL_REWARDS = [
    {'type': 'coins', 'value': 10, 'chance': 30},   # 30% - 10 монет
    {'type': 'coins', 'value': 50, 'chance': 20},   # 20% - 50 монет
    {'type': 'coins', 'value': 100, 'chance': 10},  # 10% - 100 монет
    {'type': 'coins', 'value': 500, 'chance': 2},   # 2% - 500 монет
    {'type': 'item', 'item_id': 1, 'chance': 10},   # 10% - Меч огня
    {'type': 'item', 'item_id': 2, 'chance': 10},   # 10% - Железный щит
    {'type': 'item', 'item_id': 3, 'chance': 15},   # 15% - Зелье здоровья
    {'type': 'nothing', 'value': 0, 'chance': 3},   # 3% - ничего
]

HUNT_OUTCOMES = [
    {'result': 'win', 'coins': 200, 'chance': 40},   # 40% - победа +200
    {'result': 'win', 'coins': 100, 'chance': 30},   # 30% - победа +100
    {'result': 'lose', 'coins': -100, 'chance': 20}, # 20% - поражение -100
    {'result': 'lose', 'coins': -200, 'chance': 10}, # 10% - поражение -200
]

CHEST_REWARDS = [
    {'type': 'coins', 'value': 150, 'chance': 30},
    {'type': 'coins', 'value': 300, 'chance': 20},
    {'type': 'coins', 'value': 50, 'chance': 25},
    {'type': 'item', 'item_id': 1, 'chance': 8},
    {'type': 'item', 'item_id': 2, 'chance': 8},
    {'type': 'item', 'item_id': 4, 'chance': 5},  # Плащ невидимости
    {'type': 'nothing', 'value': 0, 'chance': 4},
]

def spin_wheel(user_id):
    """Колесо удачи - ежедневное бесплатное вращение"""
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения", 0, None
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Проверяем, крутил ли пользователь сегодня
        cursor.execute('''
            SELECT COUNT(*) as count FROM game_stats 
            WHERE user_id = %s AND action_type = 'wheel' 
            AND DATE(created_at) = CURDATE()
        ''', (user_id,))
        result = cursor.fetchone()
        
        if result['count'] > 0:
            return False, "Вы уже крутили колесо сегодня! Приходите завтра.", 0, None
        
        # Выбираем награду
        total_chance = sum(r['chance'] for r in WHEEL_REWARDS)
        rand = random.randint(1, total_chance)
        cumulative = 0
        reward = None
        
        for r in WHEEL_REWARDS:
            cumulative += r['chance']
            if rand <= cumulative:
                reward = r
                break
        
        message = ""
        reward_value = 0
        item_id = None
        
        if reward['type'] == 'coins':
            # Добавляем монеты
            cursor.execute("UPDATE users SET balance = balance + %s WHERE id = %s", (reward['value'], user_id))
            message = f"🎉 Поздравляем! Вы выиграли {reward['value']} монет!"
            reward_value = reward['value']
            
        elif reward['type'] == 'item':
            # Добавляем предмет в инвентарь
            cursor.execute('''
                INSERT INTO inventory (user_id, item_id, quantity)
                VALUES (%s, %s, 1)
                ON DUPLICATE KEY UPDATE quantity = quantity + 1
            ''', (user_id, reward['item_id']))
            
            cursor.execute("SELECT name FROM items WHERE id = %s", (reward['item_id'],))
            item = cursor.fetchone()
            message = f"🎁 Поздравляем! Вы выиграли предмет: {item['name']}!"
            reward_value = reward['item_id']
            item_id = reward['item_id']
            
        else:
            message = "😢 К сожалению, ничего не выпало. Попробуйте в следующий раз!"
        
        # Записываем статистику
        cursor.execute('''
            INSERT INTO game_stats (user_id, action_type, result, reward_type, reward_value)
            VALUES (%s, 'wheel', 'win', %s, %s)
        ''', (user_id, reward['type'], reward_value if reward['type'] == 'coins' else reward_value))
        
        conn.commit()
        
        # Обновляем баланс в current_user (для отображения)
        cursor.execute("SELECT balance FROM users WHERE id = %s", (user_id,))
        new_balance = cursor.fetchone()
        
        return True, message, new_balance['balance'], item_id
        
    except Error as e:
        conn.rollback()
        return False, f"Ошибка: {e}", 0, None
    finally:
        cursor.close()
        conn.close()

def hunt_monster(user_id):
    """Охота на монстра - рискованное сражение"""
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения", 0
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Выбираем исход
        total_chance = sum(h['chance'] for h in HUNT_OUTCOMES)
        rand = random.randint(1, total_chance)
        cumulative = 0
        outcome = None
        
        for h in HUNT_OUTCOMES:
            cumulative += h['chance']
            if rand <= cumulative:
                outcome = h
                break
        
        # Проверяем, хватит ли монет при проигрыше
        cursor.execute("SELECT balance FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        if outcome['coins'] < 0 and user['balance'] < abs(outcome['coins']):
            return False, "😢 У вас недостаточно монет для охоты! Пополните баланс.", user['balance']
        
        # Обновляем баланс
        new_balance = user['balance'] + outcome['coins']
        cursor.execute("UPDATE users SET balance = %s WHERE id = %s", (new_balance, user_id))
        
        # Записываем статистику
        cursor.execute('''
            INSERT INTO game_stats (user_id, action_type, result, reward_type, reward_value)
            VALUES (%s, 'hunt', %s, 'coins', %s)
        ''', (user_id, outcome['result'], outcome['coins']))
        
        conn.commit()
        
        if outcome['result'] == 'win':
            message = f"⚔️ Победа! Вы убили монстра и получили {outcome['coins']} монет!"
        else:
            message = f"💀 Поражение! Монстр оказался сильнее. Вы потеряли {abs(outcome['coins'])} монет."
        
        return True, message, new_balance
        
    except Error as e:
        conn.rollback()
        return False, f"Ошибка: {e}", 0
    finally:
        cursor.close()
        conn.close()

def open_chest(user_id):
    """Сундук с сокровищами - стоит 100 монет"""
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения", 0, None
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Проверяем баланс
        cursor.execute("SELECT balance FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        if user['balance'] < 100:
            return False, "😢 Недостаточно монет! Сундук стоит 100 монет.", user['balance'], None
        
        # Списываем 100 монет
        cursor.execute("UPDATE users SET balance = balance - 100 WHERE id = %s", (user_id,))
        
        # Выбираем награду
        total_chance = sum(c['chance'] for c in CHEST_REWARDS)
        rand = random.randint(1, total_chance)
        cumulative = 0
        reward = None
        
        for c in CHEST_REWARDS:
            cumulative += c['chance']
            if rand <= cumulative:
                reward = c
                break
        
        message = ""
        reward_value = 0
        item_id = None
        new_balance = user['balance'] - 100
        
        if reward['type'] == 'coins':
            # Добавляем монеты
            cursor.execute("UPDATE users SET balance = balance + %s WHERE id = %s", (reward['value'], user_id))
            new_balance = user['balance'] - 100 + reward['value']
            message = f"💰 Вы открыли сундук и нашли {reward['value']} монет!"
            reward_value = reward['value']
            
        elif reward['type'] == 'item':
            # Добавляем предмет
            cursor.execute('''
                INSERT INTO inventory (user_id, item_id, quantity)
                VALUES (%s, %s, 1)
                ON DUPLICATE KEY UPDATE quantity = quantity + 1
            ''', (user_id, reward['item_id']))
            
            cursor.execute("SELECT name FROM items WHERE id = %s", (reward['item_id'],))
            item = cursor.fetchone()
            message = f"✨ Вы открыли сундук и нашли предмет: {item['name']}!"
            reward_value = reward['item_id']
            item_id = reward['item_id']
            
        else:
            message = "😢 Сундук оказался пустым... В следующий раз повезёт!"
        
        # Записываем статистику
        cursor.execute('''
            INSERT INTO game_stats (user_id, action_type, result, reward_type, reward_value)
            VALUES (%s, 'chest', 'win', %s, %s)
        ''', (user_id, reward['type'], reward_value if reward['type'] == 'coins' else reward_value))
        
        conn.commit()
        
        cursor.execute("SELECT balance FROM users WHERE id = %s", (user_id,))
        final_balance = cursor.fetchone()
        
        return True, message, final_balance['balance'], item_id
        
    except Error as e:
        conn.rollback()
        return False, f"Ошибка: {e}", 0, None
    finally:
        cursor.close()
        conn.close()

def get_game_stats(user_id):
    """Получить игровую статистику пользователя"""
    conn = get_connection()
    if not conn:
        return {}
    
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('''
        SELECT 
            SUM(CASE WHEN action_type = 'wheel' THEN 1 ELSE 0 END) as wheel_spins,
            SUM(CASE WHEN action_type = 'hunt' AND result = 'win' THEN 1 ELSE 0 END) as hunt_wins,
            SUM(CASE WHEN action_type = 'hunt' AND result = 'lose' THEN 1 ELSE 0 END) as hunt_losses,
            SUM(CASE WHEN action_type = 'chest' THEN 1 ELSE 0 END) as chests_opened
        FROM game_stats
        WHERE user_id = %s
    ''', (user_id,))
    stats = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return stats or {}


def advanced_search(filters):
    """
    Расширенный поиск предметов по параметрам
    filters: словарь с параметрами поиска
    """
    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM items WHERE 1=1"
    params = []
    
    # Поиск по названию (частичное совпадение)
    if filters.get('name'):
        query += " AND name LIKE %s"
        params.append(f"%{filters['name']}%")
    
    # Фильтр по категории
    if filters.get('category'):
        query += " AND category = %s"
        params.append(filters['category'])
    
    # Фильтр по редкости
    if filters.get('rarity'):
        query += " AND rarity = %s"
        params.append(filters['rarity'])
    
    # Фильтр по слоту
    if filters.get('slot'):
        query += " AND slot = %s"
        params.append(filters['slot'])
    
    # Диапазон цены
    if filters.get('price_min'):
        query += " AND price >= %s"
        params.append(filters['price_min'])
    if filters.get('price_max'):
        query += " AND price <= %s"
        params.append(filters['price_max'])
    
    # Диапазон уровня
    if filters.get('level_min'):
        query += " AND level_required >= %s"
        params.append(filters['level_min'])
    if filters.get('level_max'):
        query += " AND level_required <= %s"
        params.append(filters['level_max'])
    
    # Фильтр по наличию
    if filters.get('stock_filter') == 'in_stock':
        query += " AND stock > 0"
    elif filters.get('stock_filter') == 'out_stock':
        query += " AND stock = 0"
    
    # Сортировка
    sort_by = filters.get('sort_by', 'name')
    order = filters.get('order', 'ASC')
    if sort_by in ['name', 'price', 'level_required']:
        query += f" ORDER BY {sort_by} {order}"
    
    cursor.execute(query, params)
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return items

def update_item_full(item_id, name, description, price, category, rarity, level_required, slot, durability, bonus_stats, stock, image_url):
    """Полное обновление предмета (админ)"""
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения"
    
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE items 
            SET name = %s, description = %s, price = %s, category = %s, 
                rarity = %s, level_required = %s, slot = %s, durability = %s, 
                bonus_stats = %s, stock = %s, image_url = %s
            WHERE id = %s
        ''', (name, description, price, category, rarity, level_required, 
              slot, durability, bonus_stats, stock, image_url, item_id))
        conn.commit()
        return True, "Предмет обновлён"
    except Error as e:
        return False, f"Ошибка: {e}"
    finally:
        cursor.close()
        conn.close()

def add_item_full(name, description, price, category, rarity, level_required, slot, durability, bonus_stats, stock, image_url):
    """Добавить новый предмет (админ)"""
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения"
    
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO items (name, description, price, category, rarity, level_required, slot, durability, bonus_stats, stock, image_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (name, description, price, category, rarity, level_required, slot, durability, bonus_stats, stock, image_url))
        conn.commit()
        return True, "Предмет добавлен"
    except Error as e:
        return False, f"Ошибка: {e}"
    finally:
        cursor.close()
        conn.close()

def add_item_full(name, description, price, category, rarity, level_required, slot, durability, bonus_stats, stock, image_url):
    """Добавить новый предмет со всеми параметрами (админ)"""
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения"
    
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO items (name, description, price, category, rarity, level_required, slot, durability, bonus_stats, stock, image_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (name, description, price, category, rarity, level_required, slot, durability, bonus_stats, stock, image_url))
        conn.commit()
        return True, "Предмет добавлен"
    except Error as e:
        return False, f"Ошибка: {e}"
    finally:
        cursor.close()
        conn.close()
        
import random
from datetime import datetime, timedelta
import bcrypt

def generate_test_data():
    """Генерация тестовых данных: пользователи, транзакции, рыночные предложения"""
    conn = get_connection()
    if not conn:
        print("Ошибка подключения к БД")
        return
    
    cursor = conn.cursor(dictionary=True)
    
    # ============ 1. Генерация пользователей ============
    print("Генерация пользователей...")
    
    # Проверяем, сколько уже есть пользователей
    cursor.execute("SELECT COUNT(*) as count FROM users")
    existing_users = cursor.fetchone()['count']
    
    if existing_users < 10:  # Если меньше 10 пользователей, добавляем
        users_to_add = 15 - existing_users
        usernames = [
            "WarriorKing", "MageMaster", "ElfArcher", "DarkKnight", "HealerPriest",
            "DragonSlayer", "ShadowRogue", "BeastTamer", "IceWizard", "FireMage",
            "ThunderBolt", "EarthShaker", "WindWalker", "MoonHunter", "StarSeeker"
        ]
        
        for i in range(min(users_to_add, len(usernames))):
            username = usernames[i]
            password_hash = bcrypt.hashpw("test123".encode(), bcrypt.gensalt())
            role = random.choice(['user', 'user', 'user', 'user', 'moderator'])  # 80% user, 20% moderator
            balance = random.randint(500, 5000)
            
            try:
                cursor.execute('''
                    INSERT INTO users (username, password_hash, role, balance, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (username, password_hash.decode(), role, balance, 
                      datetime.now() - timedelta(days=random.randint(1, 90))))
                print(f"  Добавлен пользователь: {username} (баланс: {balance})")
            except:
                pass
        
        conn.commit()
        print(f"  Добавлено {users_to_add} пользователей")
    else:
        print(f"  Пользователей уже достаточно: {existing_users}")
    
    # ============ 2. Получаем списки ID для связей ============
    cursor.execute("SELECT id, username, balance FROM users WHERE role != 'admin'")
    users = cursor.fetchall()
    
    cursor.execute("SELECT id, name, price, category FROM items")
    items = cursor.fetchall()
    
    if not users or not items:
        print("Нет пользователей или предметов для генерации данных")
        cursor.close()
        conn.close()
        return
    
    # ============ 3. Генерация транзакций покупок в магазине ============
    print("Генерация истории покупок в магазине...")
    
    cursor.execute("SELECT COUNT(*) as count FROM transactions WHERE transaction_type = 'purchase'")
    existing_transactions = cursor.fetchone()['count']
    
    if existing_transactions < 50:
        transactions_to_add = 100 - existing_transactions
        added = 0
        
        for _ in range(transactions_to_add):
            user = random.choice(users)
            item = random.choice(items)
            quantity = random.randint(1, 3)
            total_price = item['price'] * quantity
            
            # Проверяем, хватит ли баланса у пользователя
            if user['balance'] >= total_price:
                date = datetime.now() - timedelta(days=random.randint(0, 60))
                
                try:
                    cursor.execute('''
                        INSERT INTO transactions (user_id, item_id, transaction_type, quantity, price_per_unit, total_amount, transaction_date)
                        VALUES (%s, %s, 'purchase', %s, %s, %s, %s)
                    ''', (user['id'], item['id'], quantity, item['price'], total_price, date))
                    
                    # Обновляем баланс пользователя
                    cursor.execute("UPDATE users SET balance = balance - %s WHERE id = %s", (total_price, user['id']))
                    added += 1
                except:
                    pass
        
        conn.commit()
        print(f"  Добавлено {added} транзакций покупок")
    else:
        print(f"  Транзакций уже достаточно: {existing_transactions}")
    
    # ============ 4. Генерация рыночных предложений ============
    print("Генерация рыночных предложений...")
    
    # Получаем обновлённые балансы пользователей
    cursor.execute("SELECT id, username, balance FROM users WHERE role != 'admin'")
    users = cursor.fetchall()
    
    cursor.execute("SELECT COUNT(*) as count FROM market_offers WHERE status = 'active'")
    existing_offers = cursor.fetchone()['count']
    
    if existing_offers < 50:
        offers_to_add = 30 - existing_offers
        added = 0
        
        for _ in range(offers_to_add):
            seller = random.choice(users)
            item = random.choice(items)
            
            # У продавца должен быть предмет в инвентаре
            cursor.execute("SELECT quantity FROM inventory WHERE user_id = %s AND item_id = %s", (seller['id'], item['id']))
            inv = cursor.fetchone()
            
            if inv and inv['quantity'] > 0:
                quantity = random.randint(1, min(inv['quantity'], 5))
                price_per_unit = item['price'] + random.randint(-100, 200)  # Цена может быть ниже или выше магазинной
                price_per_unit = max(10, price_per_unit)  # Не меньше 10 монет
                
                try:
                    # Уменьшаем инвентарь продавца
                    if inv['quantity'] == quantity:
                        cursor.execute("DELETE FROM inventory WHERE user_id = %s AND item_id = %s", (seller['id'], item['id']))
                    else:
                        cursor.execute("UPDATE inventory SET quantity = quantity - %s WHERE user_id = %s AND item_id = %s", 
                                     (quantity, seller['id'], item['id']))
                    
                    # Создаём предложение
                    cursor.execute('''
                        INSERT INTO market_offers (seller_id, item_id, quantity, price_per_unit, status, created_at)
                        VALUES (%s, %s, %s, %s, 'active', %s)
                    ''', (seller['id'], item['id'], quantity, price_per_unit, 
                          datetime.now() - timedelta(days=random.randint(0, 14))))
                    added += 1
                except:
                    pass
        
        conn.commit()
        print(f"  Добавлено {added} активных предложений на рынке")
    else:
        print(f"  Активных предложений уже достаточно: {existing_offers}")
    
    # ============ 5. Генерация завершённых сделок на рынке ============
    print("Генерация истории сделок на рынке...")
    
    cursor.execute("SELECT COUNT(*) as count FROM player_transactions")
    existing_player_tx = cursor.fetchone()['count']
    
    if existing_player_tx < 50:
        tx_to_add = 60 - existing_player_tx
        added = 0
        
        for _ in range(tx_to_add):
            buyer = random.choice(users)
            seller = random.choice(users)
            
            # Покупатель и продавец не должны совпадать
            if buyer['id'] == seller['id']:
                continue
            
            item = random.choice(items)
            quantity = random.randint(1, 2)
            price_per_unit = item['price'] + random.randint(-50, 150)
            price_per_unit = max(10, price_per_unit)
            total_amount = price_per_unit * quantity
            
            # Проверяем баланс покупателя
            if buyer['balance'] >= total_amount:
                date = datetime.now() - timedelta(days=random.randint(0, 45))
                
                try:
                    # Создаём запись о предложении (как завершённое)
                    cursor.execute('''
                        INSERT INTO market_offers (seller_id, item_id, quantity, price_per_unit, status, created_at, sold_at)
                        VALUES (%s, %s, %s, %s, 'sold', %s, %s)
                    ''', (seller['id'], item['id'], quantity, price_per_unit, 
                          date - timedelta(hours=random.randint(1, 48)), date))
                    
                    offer_id = cursor.lastrowid
                    
                    # Записываем сделку
                    cursor.execute('''
                        INSERT INTO player_transactions (offer_id, buyer_id, seller_id, item_id, quantity, price_per_unit, total_amount, transaction_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (offer_id, buyer['id'], seller['id'], item['id'], quantity, price_per_unit, total_amount, date))
                    
                    # Обновляем балансы
                    cursor.execute("UPDATE users SET balance = balance - %s WHERE id = %s", (total_amount, buyer['id']))
                    cursor.execute("UPDATE users SET balance = balance + %s WHERE id = %s", (total_amount, seller['id']))
                    
                    # Добавляем предмет покупателю
                    cursor.execute('''
                        INSERT INTO inventory (user_id, item_id, quantity, purchased_at)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE quantity = quantity + %s
                    ''', (buyer['id'], item['id'], quantity, date, quantity))
                    
                    added += 1
                except:
                    pass
        
        conn.commit()
        print(f"  Добавлено {added} завершённых сделок на рынке")
    else:
        print(f"  Сделок на рынке уже достаточно: {existing_player_tx}")
    
    # ============ 6. Генерация игровых событий для статистики ============
    print("Генерация игровых событий...")
    
    cursor.execute("SELECT COUNT(*) as count FROM game_stats")
    existing_stats = cursor.fetchone()['count']
    
    if existing_stats < 50:
        stats_to_add = 100 - existing_stats
        added = 0
        
        actions = ['wheel', 'hunt', 'chest']
        results = ['win', 'lose']
        reward_types = ['coins', 'item', 'nothing']
        
        for _ in range(stats_to_add):
            user = random.choice(users)
            action = random.choice(actions)
            
            if action == 'wheel':
                result = 'win' if random.random() > 0.3 else 'lose'
                reward_type = random.choice(['coins', 'item', 'nothing'])
                reward_value = random.choice([10, 50, 100, 200, 500]) if reward_type == 'coins' else random.choice([1, 2, 3, 4, 5, 6])
            elif action == 'hunt':
                result = random.choice(results)
                reward_type = 'coins'
                reward_value = random.choice([100, 200]) if result == 'win' else random.choice([-100, -200])
            else:  # chest
                result = 'win'
                reward_type = random.choice(['coins', 'item', 'nothing'])
                reward_value = random.choice([50, 100, 150, 200, 300]) if reward_type == 'coins' else random.choice([1, 2, 3, 4])
            
            date = datetime.now() - timedelta(days=random.randint(0, 30))
            
            try:
                cursor.execute('''
                    INSERT INTO game_stats (user_id, action_type, result, reward_type, reward_value, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (user['id'], action, result, reward_type, reward_value, date))
                added += 1
            except:
                pass
        
        conn.commit()
        print(f"  Добавлено {added} игровых событий")
    else:
        print(f"  Игровых событий уже достаточно: {existing_stats}")
    
    # ============ 7. Вывод итоговой статистики ============
    print("\n" + "="*50)
    print("ИТОГОВАЯ СТАТИСТИКА БАЗЫ ДАННЫХ:")
    print("="*50)
    
    cursor.execute("SELECT COUNT(*) as count FROM users")
    print(f"👥 Пользователей: {cursor.fetchone()['count']}")
    
    cursor.execute("SELECT COUNT(*) as count FROM items")
    print(f"📦 Предметов в магазине: {cursor.fetchone()['count']}")
    
    cursor.execute("SELECT COUNT(*) as count FROM transactions")
    print(f"💳 Транзакций в магазине: {cursor.fetchone()['count']}")
    
    cursor.execute("SELECT COUNT(*) as count FROM market_offers WHERE status = 'active'")
    print(f"🏪 Активных предложений на рынке: {cursor.fetchone()['count']}")
    
    cursor.execute("SELECT COUNT(*) as count FROM player_transactions")
    print(f"🤝 Завершённых сделок на рынке: {cursor.fetchone()['count']}")
    
    cursor.execute("SELECT COUNT(*) as count FROM game_stats")
    print(f"🎮 Игровых событий: {cursor.fetchone()['count']}")
    
    cursor.execute("SELECT SUM(quantity) as total FROM inventory")
    total_items = cursor.fetchone()['total'] or 0
    print(f"🎒 Всего предметов в инвентарях: {total_items}")
    
    cursor.execute("SELECT SUM(balance) as total FROM users WHERE role != 'admin'")
    total_balance = cursor.fetchone()['total'] or 0
    print(f"💰 Общий баланс игроков: {total_balance} монет")
    
    print("="*50)
    
    cursor.close()
    conn.close()
    print("\nГенерация тестовых данных завершена!")


import json
import csv
import bcrypt
from datetime import datetime

# ============================================================
# ФУНКЦИИ ИМПОРТА ДАННЫХ ИЗ ВНЕШНИХ ИСТОЧНИКОВ
# ============================================================

def import_items_from_json(file_path):
    """
    Импорт предметов из JSON-файла.
    Формат JSON:
    [
        {
            "name": "Название",
            "description": "Описание",
            "price": 100,
            "category": "weapon",
            "rarity": "common",
            "level_required": 1,
            "slot": "weapon",
            "durability": 100,
            "bonus_stats": "{\"strength\": 5}",
            "stock": 10,
            "image_url": "/static/images/item.png"
        },
        ...
    ]
    """
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения к БД"
    
    cursor = conn.cursor()
    added = 0
    errors = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            items = json.load(f)
        
        for item in items:
            try:
                cursor.execute('''
                    INSERT INTO items 
                    (name, description, price, category, rarity, level_required, 
                     slot, durability, bonus_stats, stock, image_url)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    item.get('name', ''),
                    item.get('description', ''),
                    item.get('price', 0),
                    item.get('category', 'other'),
                    item.get('rarity', 'common'),
                    item.get('level_required', 1),
                    item.get('slot', 'other'),
                    item.get('durability', 100),
                    item.get('bonus_stats', '{}'),
                    item.get('stock', 0),
                    item.get('image_url', '')
                ))
                added += 1
            except Exception as e:
                errors.append(f"Ошибка при импорте '{item.get('name', 'unknown')}': {str(e)}")
        
        conn.commit()
        
        msg = f"Импортировано предметов: {added}"
        if errors:
            msg += f"\nОшибки: {len(errors)}"
        
        return True, msg, errors
        
    except FileNotFoundError:
        return False, f"Файл не найден: {file_path}"
    except json.JSONDecodeError as e:
        return False, f"Ошибка парсинга JSON: {e}"
    finally:
        cursor.close()
        conn.close()


def import_users_from_csv(file_path):
    """
    Импорт пользователей из CSV-файла.
    Формат CSV (с заголовками):
    username,password,role,balance
    test_user,123456,user,1000
    """
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения к БД"
    
    cursor = conn.cursor()
    added = 0
    errors = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    username = row.get('username', '').strip()
                    password = row.get('password', '')
                    role = row.get('role', 'user')
                    balance = int(row.get('balance', 1000))
                    
                    if not username:
                        errors.append("Пропущена запись: отсутствует username")
                        continue
                    
                    # Проверяем, существует ли пользователь
                    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                    if cursor.fetchone():
                        errors.append(f"Пользователь '{username}' уже существует, пропущен")
                        continue
                    
                    # Хешируем пароль
                    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
                    
                    cursor.execute('''
                        INSERT INTO users (username, password_hash, role, balance)
                        VALUES (%s, %s, %s, %s)
                    ''', (username, hashed.decode(), role, balance))
                    added += 1
                    
                except ValueError as e:
                    errors.append(f"Ошибка преобразования данных: {e}")
                except Exception as e:
                    errors.append(f"Ошибка при импорте '{row.get('username', 'unknown')}': {str(e)}")
        
        conn.commit()
        
        msg = f"Импортировано пользователей: {added}"
        if errors:
            msg += f"\nОшибки: {len(errors)}"
        
        return True, msg, errors
        
    except FileNotFoundError:
        return False, f"Файл не найден: {file_path}"
    except Exception as e:
        return False, f"Ошибка при импорте: {e}"
    finally:
        cursor.close()
        conn.close()


def export_items_to_json(file_path):
    """
    Экспорт всех предметов в JSON-файл.
    """
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения к БД"
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM items ORDER BY id")
        items = cursor.fetchall()
        
        # Преобразуем datetime в строку
        for item in items:
            if isinstance(item.get('created_at'), datetime):
                item['created_at'] = item['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=4)
        
        return True, f"Экспортировано {len(items)} предметов в {file_path}"
        
    except Exception as e:
        return False, f"Ошибка при экспорте: {e}"
    finally:
        cursor.close()
        conn.close()


def export_users_to_csv(file_path):
    """
    Экспорт пользователей в CSV-файл (без паролей, только логин, роль, баланс).
    """
    conn = get_connection()
    if not conn:
        return False, "Ошибка подключения к БД"
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT id, username, role, balance, created_at FROM users ORDER BY id")
        users = cursor.fetchall()
        
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'username', 'role', 'balance', 'created_at'])
            
            for user in users:
                writer.writerow([
                    user['id'],
                    user['username'],
                    user['role'],
                    user['balance'],
                    user['created_at'].strftime('%Y-%m-%d %H:%M:%S') if user['created_at'] else ''
                ])
        
        return True, f"Экспортировано {len(users)} пользователей в {file_path}"
        
    except Exception as e:
        return False, f"Ошибка при экспорте: {e}"
    finally:
        cursor.close()
        conn.close()
# ============ ЗАПУСК СОЗДАНИЯ ТАБЛИЦ ============

if __name__ == "__main__":
    init_db()
    add_test_items()
    add_test_user()
    add_test_transactions()
    generate_test_data()
    print("\n=== Готово! ===")
    print("Тестовый пользователь: test_player / test123")
    print("Баланс: 2000 монет")