#!/usr/bin/env python3
"""
Скрипт для очистки базы данных TinaBorke.Art
Использовать с осторожностью - данные удаляются безвозвратно!
"""

import sqlite3
import os
import sys
from pathlib import Path


def clear_database():
    """Очистка всех данных из базы данных"""

    # Путь к базе данных
    db_path = "tinaborke.db"

    # Проверяем существование файла
    if not os.path.exists(db_path):
        print(f"❌ База данных {db_path} не найдена!")
        return False

    # Подтверждение удаления
    print("🚨 ВНИМАНИЕ: Это удалит ВСЕ данные из базы данных!")
    print(f"🗄️  База данных: {db_path}")
    print("📊 Будут удалены все заявки и другие данные")
    print()

    confirmation = input("❓ Вы уверены? Введите 'DELETE' для подтверждения: ")

    if confirmation != "DELETE":
        print("❌ Операция отменена")
        return False

    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Получаем информацию о таблицах перед удалением
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        print("📋 Найдены таблицы:")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"   - {table_name}: {count} записей")

        # Подтверждение удаления каждой таблицы
        print()
        print("🗑️  Начинаем очистку...")

        for table in tables:
            table_name = table[0]
            if table_name != "sqlite_sequence":  # Пропускаем системную таблицу
                cursor.execute(f"DELETE FROM {table_name}")
                print(f"✅ Очищена таблица: {table_name}")

        # Сбрасываем автоинкремент
        cursor.execute("DELETE FROM sqlite_sequence")

        # Сохраняем изменения
        conn.commit()
        conn.close()

        print()
        print("🎉 База данных успешно очищена!")
        print("📊 Все таблицы пусты, автоинкремент сброшен")

        return True

    except Exception as e:
        print(f"❌ Ошибка при очистке базы данных: {e}")
        return False


def backup_database():
    """Создание резервной копии базы данных перед очисткой"""

    db_path = "tinaborke.db"
    backup_path = "tinaborke_backup.db"

    if not os.path.exists(db_path):
        print(f"❌ База данных {db_path} не найдена!")
        return False

    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ Создана резервная копия: {backup_path}")
        return True
    except Exception as e:
        print(f"❌ Ошибка создания резервной копии: {e}")
        return False


def show_database_info():
    """Показать информацию о текущем состоянии базы данных"""

    db_path = "tinaborke.db"

    if not os.path.exists(db_path):
        print(f"❌ База данных {db_path} не найдена!")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("📊 Текущее состояние базы данных:")
        print(f"📁 Файл: {db_path}")
        print(f"📏 Размер: {os.path.getsize(db_path)} байт")
        print()

        # Информация о таблицах
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        for table in tables:
            table_name = table[0]
            if table_name != "sqlite_sequence":
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"📋 Таблица: {table_name}")
                print(f"   📝 Записей: {count}")

                # Показываем структуру таблицы
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                print("   🏗️  Структура:")
                for col in columns:
                    print(f"     - {col[1]} ({col[2]})")
                print()

        # Последние 5 заявок
        if 'bookings' in [t[0] for t in tables]:
            cursor.execute("""
                SELECT id, name, phone, service, created_at 
                FROM bookings 
                ORDER BY id DESC 
                LIMIT 5
            """)
            recent_bookings = cursor.fetchall()

            if recent_bookings:
                print("📨 Последние 5 заявок:")
                for booking in recent_bookings:
                    print(f"   🆔 {booking[0]}: {booking[1]}, {booking[2]}, {booking[3]}, {booking[4]}")
            else:
                print("📭 Заявок нет")

        conn.close()

    except Exception as e:
        print(f"❌ Ошибка получения информации: {e}")


def main():
    """Главная функция"""

    print("=" * 50)
    print("🗑️  Очистка базы данных TinaBorke.Art")
    print("=" * 50)
    print()

    # Показываем текущее состояние
    show_database_info()
    print()

    # Меню действий
    print("Доступные действия:")
    print("1. 🔍 Показать информацию о базе данных")
    print("2. 💾 Создать резервную копию")
    print("3. 🗑️  Очистить базу данных")
    print("4. ❌ Выйти")
    print()

    while True:
        try:
            choice = input("Выберите действие (1-4): ").strip()

            if choice == "1":
                print()
                show_database_info()
                print()
            elif choice == "2":
                print()
                if backup_database():
                    print("✅ Резервная копия создана успешно!")
                else:
                    print("❌ Не удалось создать резервную копию")
                print()
            elif choice == "3":
                print()
                if backup_database():
                    print("✅ Резервная копия создана перед очисткой")
                if clear_database():
                    print("✅ База данных очищена успешно!")
                print()
            elif choice == "4":
                print("👋 Выход...")
                break
            else:
                print("❌ Неверный выбор. Попробуйте снова.")

        except KeyboardInterrupt:
            print("\n👋 Выход...")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    main()