import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_database():
    """Проверка состояния базы данных"""
    try:
        conn = sqlite3.connect('tinaborke.db')
        cursor = conn.cursor()

        # Проверяем существование таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bookings'")
        table_exists = cursor.fetchone()

        if table_exists:
            logger.info("✅ Таблица 'bookings' существует")

            # Проверяем структуру таблицы
            cursor.execute("PRAGMA table_info(bookings)")
            columns = cursor.fetchall()
            logger.info("Структура таблицы bookings:")
            for col in columns:
                logger.info(f"  {col}")

            # Проверяем существующие записи
            cursor.execute("SELECT COUNT(*) FROM bookings")
            count = cursor.fetchone()[0]
            logger.info(f"Количество записей в таблице: {count}")

            if count > 0:
                cursor.execute("SELECT * FROM bookings ORDER BY id DESC LIMIT 5")
                recent_bookings = cursor.fetchall()
                logger.info("Последние 5 записей:")
                for booking in recent_bookings:
                    logger.info(f"  {booking}")
        else:
            logger.error("❌ Таблица 'bookings' не существует!")

        conn.close()

    except Exception as e:
        logger.error(f"Ошибка проверки базы данных: {e}")


if __name__ == "__main__":
    check_database()