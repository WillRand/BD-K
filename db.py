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
    
    # Проверяем, есть ли уже предметы
    cursor.execute("SELECT COUNT(*) FROM items")
    count = cursor.fetchone()[0]
    
    if count == 0:
        items = [
            ("Меч огня", "Наносит 50-70 урона", 500, "weapon", 10, "/static/images/sword.png"),
            ("Железный щит", "Блокирует 30% урона", 300, "armor", 15, "/static/images/shield.png"),
            ("Зелье здоровья", "Восстанавливает 50 HP", 100, "potion", 50, "/static/images/potion.png"),
            ("Плащ невидимости", "Скрывает на 10 секунд", 800, "cosmetic", 5, "/static/images/cloak.png"),
            ("Магический посох", "Увеличивает магический урон", 650, "weapon", 8, "/static/images/staff.png"),
            ("Кожаная броня", "Защита +15", 250, "armor", 20, "/static/images/leather.png"),
        ]
        
        cursor.executemany('''
            INSERT INTO items (name, description, price, category, stock, image_url)
            VALUES (%s, %s, %s, %s, %s, %s)
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
    """Купить предмет с рынка"""
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
            return False, "Нельзя купить свой же товар"
        
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
        
        # Записываем сделку
        cursor.execute('''
            INSERT INTO player_transactions (offer_id, buyer_id, seller_id, item_id, quantity, price_per_unit, total_amount)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (offer_id, buyer_id, offer['seller_id'], offer['item_id'], quantity, offer['price_per_unit'], total_cost))
        
        conn.commit()
        return True, f"Куплено {quantity} шт. '{offer['name']}' за {total_cost} монет"
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
    """Получить историю сделок игрока (покупки и продажи)"""
    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        (SELECT 
            'purchase' as type,
            pt.transaction_date as date,
            pt.quantity,
            pt.price_per_unit,
            pt.total_amount,
            i.name as item_name,
            u.username as other_party
        FROM player_transactions pt
        JOIN items i ON pt.item_id = i.id
        JOIN users u ON pt.seller_id = u.id
        WHERE pt.buyer_id = %s)
        
        UNION ALL
        
        (SELECT 
            'sale' as type,
            pt.transaction_date as date,
            pt.quantity,
            pt.price_per_unit,
            pt.total_amount,
            i.name as item_name,
            u.username as other_party
        FROM player_transactions pt
        JOIN items i ON pt.item_id = i.id
        JOIN users u ON pt.buyer_id = u.id
        WHERE pt.seller_id = %s)
        
        ORDER BY date DESC
        LIMIT %s
    ''', (user_id, user_id, limit))
    transactions = cursor.fetchall()
    cursor.close()
    conn.close()
    return transactions

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

# ============ ЗАПУСК СОЗДАНИЯ ТАБЛИЦ ============

if __name__ == "__main__":
    init_db()
    add_test_items()
    add_test_user()
    add_test_transactions()
    print("\n=== Готово! ===")
    print("Тестовый пользователь: test_player / test123")
    print("Баланс: 2000 монет")