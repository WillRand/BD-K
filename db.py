import mysql.connector
from mysql.connector import Error

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
    
    # Таблица для истории покупок/продаж (опционально, для отладки)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            item_id INT NOT NULL,
            transaction_type ENUM('purchase', 'sale') NOT NULL,
            quantity INT NOT NULL,
            price_per_unit INT NOT NULL,
            total_amount INT NOT NULL,
            transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
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

def get_all_items(category=None, sort_by=None, order='ASC'):
    """Получить все товары (только те, что есть в наличии)"""
    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM items WHERE stock > 0"
    params = []
    
    if category:
        query += " AND category = %s"
        params.append(category)
    
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
    
    cursor = conn.cursor(dictionary=True)
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
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 1. Получаем информацию о предмете
        cursor.execute("SELECT price, stock FROM items WHERE id = %s", (item_id,))
        item = cursor.fetchone()
        
        if not item:
            return False, "Предмет не найден"
        
        if item['stock'] < quantity:
            return False, f"Недостаточно товара. В наличии: {item['stock']}"
        
        # 2. Получаем баланс пользователя
        cursor.execute("SELECT balance FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
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
    
    cursor = conn.cursor(dictionary=True)
    
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
        cursor.execute("SELECT name, price FROM items WHERE id = %s", (item_id,))
        item = cursor.fetchone()
        
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
    
    cursor = conn.cursor(dictionary=True)
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

# ============ ЗАПУСК СОЗДАНИЯ ТАБЛИЦ ============

if __name__ == "__main__":
    init_db()
    add_test_items()
    add_test_user()
    print("\n=== Готово! ===")
    print("Тестовый пользователь: test_player / test123")
    print("Баланс: 2000 монет")