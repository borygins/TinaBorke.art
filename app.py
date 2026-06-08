"""
FastAPI приложение для TinaBorke.Art
Упрощенная версия с исправлениями для запуска
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Depends, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from contextlib import asynccontextmanager
import logging
import asyncio
import secrets
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import os
import html
from pathlib import Path
from pydantic import BaseModel, field_validator
import aiosqlite
import httpx
import json
import sys
import re
from uuid import uuid4
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С ВРЕМЕНЕМ ==========
def get_moscow_time():
    """Получение текущего времени по Москве"""
    moscow_tz = timezone(timedelta(hours=3))  # UTC+3 для Москвы
    return datetime.now(moscow_tz)

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
# Функция для удаления emoji из строк
def remove_emoji(text):
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002700-\U000027BF"  # dingbats
        u"\U0001F900-\U0001F9FF"  # supplemental symbols and pictographs
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text)

class NoEmojiFormatter(logging.Formatter):
    def format(self, record):
        # Сохраняем оригинальное сообщение
        original_msg = record.msg
        original_args = record.args

        try:
            # Удаляем emoji из сообщения
            if record.msg:
                record.msg = remove_emoji(str(record.msg))
            # Форматируем как обычно
            result = super().format(record)
        except UnicodeEncodeError:
            # Если все равно ошибка, используем безопасное кодирование
            record.msg = original_msg.encode('utf-8', errors='ignore').decode('utf-8')
            result = super().format(record)
        finally:
            # Восстанавливаем оригинальные значения
            record.msg = original_msg
            record.args = original_args

        return result

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Создаем handler для консоли
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# Устанавливаем форматтер без emoji
formatter = NoEmojiFormatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
console_handler.setFormatter(formatter)

# Добавляем handler к логгеру
logger.addHandler(console_handler)

# Также пишем в файл (там emoji работают нормально)
file_handler = logging.FileHandler('app.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(file_handler)

# ========== КОНФИГУРАЦИЯ ПРИЛОЖЕНИЯ ==========
class Settings:
    """Класс для хранения настроек приложения"""
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID", "")
    STAFF_TELEGRAM_IDS = os.getenv("STAFF_TELEGRAM_IDS", "").split(",")
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
    TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")
    BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    DATABASE_URL = os.getenv("DATABASE_URL", "tinaborke.db")
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")

settings = Settings()
security = HTTPBasic()
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

def slugify(value: str) -> str:
    """Простой slug для ЧПУ без внешних зависимостей."""
    translit = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    }
    text = "".join(translit.get(ch, ch) for ch in value.lower())
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or f"item-{uuid4().hex[:8]}"

def plain_excerpt(value: str, limit: int = 160) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit].rstrip()

def require_admin(credentials: HTTPBasicCredentials = Depends(security)):
    expected_username = settings.ADMIN_USERNAME
    expected_password = settings.ADMIN_PASSWORD
    username_ok = secrets.compare_digest(credentials.username, expected_username)
    password_ok = bool(expected_password) and secrets.compare_digest(credentials.password, expected_password)
    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=401,
            detail="Требуется вход в админку",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# Логируем настройки (без чувствительных данных)
logger.info(f"Конфигурация загружена: DB={settings.DATABASE_URL}, Telegram настроен: {bool(settings.TELEGRAM_BOT_TOKEN)}")

# ========== МОДЕЛИ ДАННЫХ ==========
class BookingCreate(BaseModel):
    """Модель для создания заявки"""
    name: str
    phone: str
    service: Optional[str] = None
    date: Optional[str] = None
    message: Optional[str] = None

    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v):
        """Валидация имени - не может быть пустым"""
        if not v.strip():
            raise ValueError('Имя не может быть пустым')
        return v.strip()

    @field_validator('phone')
    @classmethod
    def phone_must_be_valid(cls, v):
        """Валидация телефона - должен содержать минимум 10 цифр"""
        cleaned = ''.join(filter(str.isdigit, v))
        if len(cleaned) < 10:
            raise ValueError('Некорректный номер телефона')
        return v

# ========== РАБОТА С БАЗОЙ ДАННЫХ ==========
class Database:
    """Класс для работы с базой данных SQLite"""
    def __init__(self, db_path: str = "tinaborke.db"):
        self.db_path = db_path
        logger.info(f"Инициализирован Database с путем: {db_path}")

    async def init_db(self):
        """Инициализация базы данных - создание таблицы если не существует"""
        logger.info("Начало инициализации базы данных")
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS bookings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        phone TEXT NOT NULL,
                        service TEXT,
                        date TEXT,
                        message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status TEXT DEFAULT 'new'
                    )
                """)
                await db.executescript("""
                    CREATE TABLE IF NOT EXISTS settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        key TEXT NOT NULL UNIQUE,
                        value TEXT NOT NULL DEFAULT ''
                    );
                    CREATE TABLE IF NOT EXISTS services (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        slug TEXT NOT NULL UNIQUE,
                        description TEXT NOT NULL DEFAULT '',
                        price TEXT NOT NULL DEFAULT '',
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        seo_title TEXT NOT NULL DEFAULT '',
                        seo_description TEXT NOT NULL DEFAULT '',
                        is_active INTEGER NOT NULL DEFAULT 1
                    );
                    CREATE TABLE IF NOT EXISTS gallery (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        image_path TEXT NOT NULL,
                        alt_text TEXT NOT NULL DEFAULT '',
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        is_active INTEGER NOT NULL DEFAULT 1
                    );
                    CREATE TABLE IF NOT EXISTS reviews (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        client_name TEXT NOT NULL,
                        text TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        is_active INTEGER NOT NULL DEFAULT 1
                    );
                    CREATE TABLE IF NOT EXISTS blog_posts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        telegram_message_id TEXT UNIQUE,
                        title TEXT NOT NULL,
                        slug TEXT NOT NULL UNIQUE,
                        text_html TEXT NOT NULL DEFAULT '',
                        text_markdown TEXT NOT NULL DEFAULT '',
                        first_image TEXT,
                        created_at TEXT NOT NULL,
                        is_visible INTEGER NOT NULL DEFAULT 1,
                        seo_title TEXT NOT NULL DEFAULT '',
                        seo_description TEXT NOT NULL DEFAULT ''
                    );
                    CREATE TABLE IF NOT EXISTS blog_photos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        post_id INTEGER NOT NULL,
                        image_path TEXT NOT NULL,
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        FOREIGN KEY(post_id) REFERENCES blog_posts(id) ON DELETE CASCADE
                    );
                """)
                await self.seed_defaults(db)
                await db.commit()
                logger.info("База данных успешно инициализирована")
        except Exception as e:
            logger.error(f"Ошибка инициализации базы данных: {e}")
            raise

    async def seed_defaults(self, db):
        default_settings = {
            "master_name": "Тина Борке",
            "city": "Санкт-Петербург",
            "phone": "+7 999 000-00-00",
            "telegram_url": "https://t.me/TinaBorkeMakeUp",
            "working_hours": "Ежедневно по предварительной записи",
            "area_served": "Санкт-Петербург и районы выезда",
            "about_text": "Я профессиональный визажист-гример. Работаю легко и с любовью, использую качественные продукты и подбираю образ под вашу внешность и настроение.",
            "promo_text": "ОСЕННЯЯ АКЦИЯ - Скидка 10% на все услуги",
            "home_title": "Визажист в Санкт-Петербурге Тина Борке",
            "home_description": "Профессиональный визажист-гример в Санкт-Петербурге: лифтинг макияж, свадебные образы, грим, укладки и обучение.",
            "blog_title": "Блог визажиста Тины Борке",
            "blog_description": "Советы по макияжу, новости, образы и посты из Telegram-канала Тины Борке.",
        }
        for key, value in default_settings.items():
            await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))

        default_services = [
            ("Дневной макияж", "dnevnoy-makiyazh", "Легкий аккуратный макияж на каждый день.", "от 2 500 ₽", 10),
            ("Вечерний макияж", "vecherniy-makiyazh", "Выразительный образ для события, съемки или вечера.", "от 3 000 ₽", 20),
            ("ЛИФТИНГ макияж", "lifting-makiyazh", "Свежий деликатный макияж с акцентом на лифтинг-эффект.", "от 3 500 ₽", 30),
            ("Свадебный образ", "svadebnyy-obraz", "Полный образ невесты с учетом платья, прически и стилистики свадьбы.", "от 7 000 ₽", 40),
            ("Макияж для фотосессии", "makiyazh-dlya-fotosessii", "Стойкий макияж для камеры, света и выбранной концепции.", "от 5 500 ₽", 50),
            ("Обучение макияжу", "obuchenie-makiyazhu", "Индивидуальный урок для повседневного или вечернего макияжа.", "Договорная", 60),
        ]
        for title, slug, description, price, sort_order in default_services:
            await db.execute("""
                INSERT OR IGNORE INTO services
                (title, slug, description, price, sort_order, seo_title, seo_description, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, (title, slug, description, price, sort_order, title[:60], plain_excerpt(description)))

        default_reviews = [
            ("Клиент", "Очень аккуратная работа и приятная атмосфера. Образ продержался весь день."),
            ("Невеста", "Спасибо за свадебный образ. Макияж выглядел нежно и красиво на фото."),
        ]
        for client_name, text in default_reviews:
            await db.execute("""
                INSERT INTO reviews (client_name, text, created_at, is_active)
                SELECT ?, ?, ?, 1
                WHERE NOT EXISTS (SELECT 1 FROM reviews WHERE client_name = ? AND text = ?)
            """, (client_name, text, get_moscow_time().strftime("%Y-%m-%d"), client_name, text))

    async def create_booking(self, booking: BookingCreate) -> int:
        """Создание новой заявки в базе данных"""
        logger.info(f"Создание заявки в БД: {booking.name}, {booking.phone}")
        try:
            # Получаем московское время
            moscow_time = get_moscow_time().strftime('%Y-%m-%d %H:%M:%S')

            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO bookings (name, phone, service, date, message, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (booking.name, booking.phone, booking.service, booking.date, booking.message, moscow_time))
                await db.commit()
                booking_id = cursor.lastrowid
                logger.info(f"Заявка успешно создана в БД с ID: {booking_id}")
                return booking_id
        except Exception as e:
            logger.error(f"Ошибка создания заявки в БД: {e}")
            raise

    async def get_booking(self, booking_id: int) -> Optional[dict]:
        """Получение заявки по ID из базы данных"""
        logger.info(f"Получение заявки из БД с ID: {booking_id}")
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT * FROM bookings WHERE id = ?
                """, (booking_id,)) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        columns = [column[0] for column in cursor.description]
                        booking_data = dict(zip(columns, row))
                        logger.info(f"Заявка найдена: {booking_data}")
                        return booking_data
                    logger.warning(f"Заявка с ID {booking_id} не найдена")
                    return None
        except Exception as e:
            logger.error(f"Ошибка получения заявки из БД: {e}")
            raise

    async def fetch_all(self, query: str, params: tuple = ()) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def execute(self, query: str, params: tuple = ()) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, params)
            await db.commit()
            return cursor.lastrowid

    async def get_settings(self) -> dict:
        rows = await self.fetch_all("SELECT key, value FROM settings")
        return {row["key"]: row["value"] for row in rows}

    async def update_settings(self, values: dict):
        async with aiosqlite.connect(self.db_path) as db:
            for key, value in values.items():
                await db.execute("""
                    INSERT INTO settings (key, value) VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """, (key, value or ""))
            await db.commit()

    async def get_services(self, active_only: bool = True) -> list[dict]:
        where = "WHERE is_active = 1" if active_only else ""
        return await self.fetch_all(f"SELECT * FROM services {where} ORDER BY sort_order, id")

    async def get_service_by_slug(self, slug: str) -> Optional[dict]:
        return await self.fetch_one("SELECT * FROM services WHERE slug = ? AND is_active = 1", (slug,))

    async def save_service(self, form: dict):
        service_id = form.get("id")
        title = (form.get("title") or "").strip()
        slug = slugify(form.get("slug") or title)
        values = (
            title,
            slug,
            form.get("description") or "",
            form.get("price") or "",
            int(form.get("sort_order") or 0),
            form.get("seo_title") or title[:60],
            form.get("seo_description") or plain_excerpt(form.get("description") or title),
            1 if form.get("is_active") == "on" else 0,
        )
        if service_id:
            await self.execute("""
                UPDATE services
                SET title=?, slug=?, description=?, price=?, sort_order=?, seo_title=?, seo_description=?, is_active=?
                WHERE id=?
            """, values + (service_id,))
        else:
            await self.execute("""
                INSERT INTO services
                (title, slug, description, price, sort_order, seo_title, seo_description, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, values)

    async def delete_service(self, service_id: int):
        await self.execute("DELETE FROM services WHERE id = ?", (service_id,))

    async def get_reviews(self, active_only: bool = True) -> list[dict]:
        where = "WHERE is_active = 1" if active_only else ""
        return await self.fetch_all(f"SELECT * FROM reviews {where} ORDER BY created_at DESC, id DESC")

    async def save_review(self, form: dict):
        review_id = form.get("id")
        values = (
            form.get("client_name") or "",
            form.get("text") or "",
            form.get("created_at") or get_moscow_time().strftime("%Y-%m-%d"),
            1 if form.get("is_active") == "on" else 0,
        )
        if review_id:
            await self.execute("UPDATE reviews SET client_name=?, text=?, created_at=?, is_active=? WHERE id=?", values + (review_id,))
        else:
            await self.execute("INSERT INTO reviews (client_name, text, created_at, is_active) VALUES (?, ?, ?, ?)", values)

    async def delete_review(self, review_id: int):
        await self.execute("DELETE FROM reviews WHERE id = ?", (review_id,))

    async def get_gallery(self, active_only: bool = True) -> list[dict]:
        where = "WHERE is_active = 1" if active_only else ""
        return await self.fetch_all(f"SELECT * FROM gallery {where} ORDER BY sort_order, id")

    async def save_gallery_item(self, image_path: str, alt_text: str, sort_order: int = 0):
        await self.execute(
            "INSERT INTO gallery (image_path, alt_text, sort_order, is_active) VALUES (?, ?, ?, 1)",
            (image_path, alt_text, sort_order),
        )

    async def update_gallery_item(self, form: dict):
        await self.execute("""
            UPDATE gallery SET alt_text=?, sort_order=?, is_active=? WHERE id=?
        """, (
            form.get("alt_text") or "",
            int(form.get("sort_order") or 0),
            1 if form.get("is_active") == "on" else 0,
            form.get("id"),
        ))

    async def delete_gallery_item(self, item_id: int):
        await self.execute("DELETE FROM gallery WHERE id = ?", (item_id,))

    async def get_blog_posts(self, visible_only: bool = True) -> list[dict]:
        where = "WHERE is_visible = 1" if visible_only else ""
        return await self.fetch_all(f"SELECT * FROM blog_posts {where} ORDER BY created_at DESC, id DESC")

    async def get_blog_post(self, slug: str) -> Optional[dict]:
        post = await self.fetch_one("SELECT * FROM blog_posts WHERE slug = ? AND is_visible = 1", (slug,))
        if post:
            post["photos"] = await self.fetch_all("SELECT * FROM blog_photos WHERE post_id = ? ORDER BY sort_order, id", (post["id"],))
        return post

    async def save_blog_post(self, form: dict):
        post_id = form.get("id")
        title = (form.get("title") or "").strip()
        slug = slugify(form.get("slug") or title)
        text_markdown = form.get("text_markdown") or ""
        text_html = "<br>".join(html.escape(line) for line in text_markdown.splitlines())
        values = (
            form.get("telegram_message_id") or None,
            title,
            slug,
            text_html,
            text_markdown,
            form.get("first_image") or None,
            form.get("created_at") or get_moscow_time().strftime("%Y-%m-%d %H:%M:%S"),
            1 if form.get("is_visible") == "on" else 0,
            form.get("seo_title") or title[:60],
            form.get("seo_description") or plain_excerpt(text_markdown),
        )
        if post_id:
            await self.execute("""
                UPDATE blog_posts
                SET telegram_message_id=?, title=?, slug=?, text_html=?, text_markdown=?, first_image=?,
                    created_at=?, is_visible=?, seo_title=?, seo_description=?
                WHERE id=?
            """, values + (post_id,))
        else:
            await self.execute("""
                INSERT INTO blog_posts
                (telegram_message_id, title, slug, text_html, text_markdown, first_image, created_at, is_visible, seo_title, seo_description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, values)

    async def toggle_blog_post(self, post_id: int):
        await self.execute("UPDATE blog_posts SET is_visible = CASE is_visible WHEN 1 THEN 0 ELSE 1 END WHERE id = ?", (post_id,))

    async def import_telegram_updates(self) -> int:
        if not settings.TELEGRAM_BOT_TOKEN:
            logger.warning("TELEGRAM_BOT_TOKEN не настроен - импорт Telegram пропущен")
            return 0
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getUpdates"
        imported = 0
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params={"allowed_updates": json.dumps(["channel_post"])})
            if response.status_code != 200:
                logger.warning(f"Telegram import failed: {response.status_code}")
                return 0
            for item in response.json().get("result", []):
                post = item.get("channel_post") or {}
                channel_id = str(post.get("chat", {}).get("id", ""))
                if settings.TELEGRAM_CHANNEL_ID and channel_id != str(settings.TELEGRAM_CHANNEL_ID):
                    continue
                message_id = str(post.get("message_id", ""))
                text = post.get("text") or post.get("caption") or ""
                if not message_id or not text:
                    continue
                exists = await self.fetch_one("SELECT id FROM blog_posts WHERE telegram_message_id = ?", (message_id,))
                if exists:
                    continue
                title = plain_excerpt(text, 60) or f"Пост Telegram {message_id}"
                await self.save_blog_post({
                    "telegram_message_id": message_id,
                    "title": title,
                    "slug": f"telegram-{message_id}",
                    "text_markdown": text,
                    "created_at": datetime.fromtimestamp(post.get("date", datetime.now().timestamp())).strftime("%Y-%m-%d %H:%M:%S"),
                    "is_visible": "on",
                })
                imported += 1
        return imported

# ========== СЕРВИС TELEGRAM УВЕДОМЛЕНИЙ ==========
class TelegramService:
    """Класс для отправки уведомлений в Telegram"""
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.admin_id = settings.ADMIN_TELEGRAM_ID
        self.staff_ids = [id.strip() for id in settings.STAFF_TELEGRAM_IDS if id.strip()]
        logger.info(f"Инициализирован TelegramService: admin_id={self.admin_id}, staff_count={len(self.staff_ids)}")

    async def send_booking_notification(self, booking: dict):
        """Отправка уведомления о новой заявке в Telegram"""
        logger.info(f"Начало отправки уведомления в Telegram для заявки {booking.get('id')}")

        if not self.bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN не настроен - пропускаем отправку в Telegram")
            return

        # Формируем сообщение для Telegram
        message = f"""
Новая заявка на TinaBorke.Art

Имя: {booking['name']}
Телефон: {booking['phone']}
Услуга: {booking.get('service', 'Не указана')}
Дата: {booking.get('date', 'Не указана')}
Сообщение: {booking.get('message', 'Не указано')}

Время заявки: {booking.get('created_at', 'Не указано')} (МСК)
ID заявки: {booking['id']}
        """

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        logger.info(f"URL для отправки в Telegram: {url.split('/bot')[0]}/bot***")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                sent_count = 0

                # Отправляем администратору
                if self.admin_id:
                    logger.info(f"Отправка уведомления администратору: {self.admin_id}")
                    try:
                        response = await client.post(url, json={
                            'chat_id': self.admin_id,
                            'text': message,
                            'parse_mode': 'Markdown'
                        })
                        if response.status_code == 200:
                            logger.info(f"Уведомление успешно отправлено администратору")
                            sent_count += 1
                        else:
                            logger.error(f"Ошибка отправки администратору: {response.status_code} - {response.text}")
                    except Exception as e:
                        logger.error(f"Исключение при отправке администратору: {e}")

                # Отправляем сотрудникам
                for staff_id in self.staff_ids:
                    if staff_id and staff_id != self.admin_id:
                        logger.info(f"Отправка уведомления сотруднику: {staff_id}")
                        try:
                            response = await client.post(url, json={
                                'chat_id': staff_id,
                                'text': message,
                                'parse_mode': 'Markdown'
                            })
                            if response.status_code == 200:
                                logger.info(f"Уведомление успешно отправлено сотруднику {staff_id}")
                                sent_count += 1
                            else:
                                logger.error(f"Ошибка отправки сотруднику {staff_id}: {response.status_code} - {response.text}")
                        except Exception as e:
                            logger.error(f"Исключение при отправке сотруднику {staff_id}: {e}")

            logger.info(f"Процесс отправки уведомлений завершен. Отправлено: {sent_count}")

        except Exception as e:
            logger.error(f"Критическая ошибка отправки уведомлений в Telegram: {e}")

# ========== ИНИЦИАЛИЗАЦИЯ СЕРВИСОВ ==========
logger.info("Инициализация сервисов...")
db = Database()
telegram_service = TelegramService()
telegram_import_task = None
logger.info("Сервисы инициализированы")

# ========== СОЗДАНИЕ ДИРЕКТОРИЙ ==========
logger.info("Проверка и создание необходимых директорий...")
directories = ["static", "static/css", "static/js", "static/images", "static/uploads", "static/blog_photos", "templates"]
for directory in directories:
    Path(directory).mkdir(exist_ok=True)
    logger.info(f"Директория {directory} создана/проверена")

# ========== LIFECYCLE МЕНЕДЖЕР FASTAPI ==========
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager для управления запуском и остановкой приложения"""
    logger.info(">>> Запуск приложения TinaBorke.Art")

    # Startup логика
    try:
        await db.init_db()
        logger.info("[OK] База данных готова к работе")
    except Exception as e:
        logger.error(f"[ERROR] Ошибка инициализации базы данных: {e}")
        raise

    async def telegram_import_loop():
        while True:
            try:
                await db.import_telegram_updates()
            except Exception as e:
                logger.warning(f"Автоимпорт Telegram пропущен: {e}")
            await asyncio.sleep(600)

    global telegram_import_task
    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHANNEL_ID:
        telegram_import_task = asyncio.create_task(telegram_import_loop())
        logger.info("[OK] Автоимпорт Telegram запущен с интервалом 10 минут")
    else:
        logger.info("Автоимпорт Telegram не запущен: задайте TELEGRAM_BOT_TOKEN и TELEGRAM_CHANNEL_ID")

    yield  # Здесь приложение работает

    # Shutdown логика
    if telegram_import_task:
        telegram_import_task.cancel()
    logger.info("<<< Остановка приложения TinaBorke.Art")

# ========== СОЗДАНИЕ FASTAPI ПРИЛОЖЕНИЯ ==========
app = FastAPI(
    title="TinaBorke.Art API",
    description="API для сайта визажиста-гримера Тины Борке",
    version="1.0.0",
    lifespan=lifespan
)

logger.info("FastAPI приложение создано")

# ========== CORS MIDDLEWARE ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене заменить на конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("CORS middleware добавлен")

@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "public, max-age=604800"
    if request.url.path.startswith("/admin"):
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response

# ========== СТАТИЧЕСКИЕ ФАЙЛЫ ==========
if Path("static").exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("Статические файлы подключены")
else:
    logger.warning("[WARN] Директория static не найдена")

# ========== ШАБЛОНЫ JINJA2 ==========
if Path("templates").exists():
    templates = Jinja2Templates(directory="templates")
    logger.info("Шаблоны Jinja2 инициализированы")
else:
    logger.warning("[WARN] Директория templates не найдена")

async def save_upload(file: UploadFile, directory: str) -> str:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Разрешены только JPG, PNG и WebP")
    safe_name = f"{uuid4().hex}{suffix}"
    target_dir = Path(directory)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / safe_name
    content = await file.read()
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Файл слишком большой")
    target.write_bytes(content)
    return "/" + str(target).replace("\\", "/")

# ========== МАРШРУТЫ API ==========
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Главная страница сайта"""
    logger.info("Запрос главной страницы")
    if Path("templates").exists():
        logger.info("Рендеринг index.html из templates")
        site_settings = await db.get_settings()
        services = await db.get_services()
        reviews = await db.get_reviews()
        gallery = await db.get_gallery()
        json_ld = {
            "@context": "https://schema.org",
            "@type": "BeautySalon",
            "name": f"Визажист {site_settings.get('master_name', 'Тина Борке')}",
            "description": site_settings.get("home_description", ""),
            "telephone": site_settings.get("phone", ""),
            "priceRange": "₽₽",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": site_settings.get("city", "Санкт-Петербург"),
                "addressCountry": "RU",
            },
            "areaServed": site_settings.get("area_served", ""),
            "sameAs": [site_settings.get("telegram_url", "")],
        }
        return templates.TemplateResponse(request, "index.html", {
            "site_settings": site_settings,
            "services": services,
            "reviews": reviews,
            "gallery": gallery,
            "canonical_url": settings.BASE_URL + "/",
            "json_ld": json.dumps(json_ld, ensure_ascii=False),
        })
    else:
        logger.info("Отдача fallback HTML (шаблоны не найдены)")
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>TinaBorke.Art</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body>
            <h1>TinaBorke.Art - Скоро здесь будет красивый сайт!</h1>
            <p>API работает. Добавьте файлы в папку templates и static.</p>
        </body>
        </html>
        """)

@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    site_settings = await db.get_settings()
    return templates.TemplateResponse(request, "about.html", {
        "site_settings": site_settings,
        "canonical_url": settings.BASE_URL + "/about",
    })

@app.get("/blog", response_class=HTMLResponse)
async def blog_index(request: Request):
    site_settings = await db.get_settings()
    posts = await db.get_blog_posts()
    return templates.TemplateResponse(request, "blog.html", {
        "site_settings": site_settings,
        "posts": posts,
        "canonical_url": settings.BASE_URL + "/blog",
    })

@app.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post(request: Request, slug: str):
    site_settings = await db.get_settings()
    post = await db.get_blog_post(slug)
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")
    article_ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": post["title"],
        "datePublished": post["created_at"],
        "description": post.get("seo_description") or plain_excerpt(post.get("text_markdown", "")),
        "author": {"@type": "Person", "name": site_settings.get("master_name", "Тина Борке")},
    }
    return templates.TemplateResponse(request, "blog_post.html", {
        "site_settings": site_settings,
        "post": post,
        "canonical_url": settings.BASE_URL + f"/blog/{slug}",
        "json_ld": json.dumps(article_ld, ensure_ascii=False),
    })

@app.get("/uslugi/{slug}", response_class=HTMLResponse)
async def service_page(request: Request, slug: str):
    site_settings = await db.get_settings()
    service = await db.get_service_by_slug(slug)
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    service_ld = {
        "@context": "https://schema.org",
        "@type": "Service",
        "name": service["title"],
        "description": service["description"],
        "provider": {"@type": "BeautySalon", "name": f"Визажист {site_settings.get('master_name', 'Тина Борке')}"},
        "areaServed": site_settings.get("city", "Санкт-Петербург"),
        "offers": {"@type": "Offer", "price": service["price"], "priceCurrency": "RUB"},
    }
    return templates.TemplateResponse(request, "service.html", {
        "site_settings": site_settings,
        "service": service,
        "canonical_url": settings.BASE_URL + f"/uslugi/{slug}",
        "json_ld": json.dumps(service_ld, ensure_ascii=False),
    })

@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    return f"User-agent: *\nDisallow: /admin\nAllow: /\n\nSitemap: {settings.BASE_URL}/sitemap.xml\n"

@app.get("/sitemap.xml", response_class=PlainTextResponse)
async def sitemap_xml():
    services = await db.get_services()
    posts = await db.get_blog_posts()
    urls = ["/", "/about", "/blog"] + [f"/uslugi/{item['slug']}" for item in services] + [f"/blog/{item['slug']}" for item in posts]
    body = "\n".join(f"<url><loc>{settings.BASE_URL}{url}</loc></url>" for url in urls)
    return PlainTextResponse(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>',
        media_type="application/xml",
    )

@app.get("/health")
async def health_check():
    """Проверка здоровья приложения - диагностический endpoint"""
    logger.info("Запрос health check")
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "telegram_configured": bool(settings.TELEGRAM_BOT_TOKEN),
        "database_file_exists": Path(settings.DATABASE_URL).exists()
    }
    logger.info(f"Health check результат: {health_status}")
    return health_status

@app.post("/api/booking")
async def create_booking(booking: BookingCreate, background_tasks: BackgroundTasks):
    """Создание новой заявки - основной endpoint"""
    logger.info("Начало создания заявки")
    logger.info(f"Данные заявки: {booking.dict()}")

    try:
        # Шаг 1: Сохраняем в базу данных
        logger.info("Сохранение заявки в базу данных...")
        booking_id = await db.create_booking(booking)
        logger.info(f"[OK] Заявка сохранена в БД с ID: {booking_id}")

        # Шаг 2: Получаем созданную заявку для подтверждения
        logger.info(f"Получение созданной заявки из БД...")
        created_booking = await db.get_booking(booking_id)

        if created_booking:
            logger.info(f"[OK] Заявка подтверждена в БД: {created_booking}")

            # Шаг 3: Отправляем уведомления в фоне
            logger.info("Добавление задачи отправки Telegram уведомления в фон")
            background_tasks.add_task(
                telegram_service.send_booking_notification,
                created_booking
            )
            logger.info("[OK] Задача Telegram уведомления добавлена в background_tasks")
        else:
            logger.error(f"[ERROR] Заявка с ID {booking_id} не найдена после создания!")

        # Шаг 4: Возвращаем успешный ответ
        response_data = {
            "success": True,
            "message": "Заявка успешно создана",
            "booking_id": booking_id
        }
        logger.info(f"Отправка ответа клиенту: {response_data}")
        return response_data

    except Exception as e:
        logger.error(f"[ERROR] Критическая ошибка создания заявки: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка сервера при создании заявки")

@app.post("/api/quick-booking")
async def create_quick_booking(booking: BookingCreate, background_tasks: BackgroundTasks):
    """Быстрая заявка - альтернативный endpoint"""
    logger.info("Запрос быстрой заявки")
    return await create_booking(booking, background_tasks)

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, _: str = Depends(require_admin)):
    return templates.TemplateResponse(request, "admin.html", {
        "site_settings": await db.get_settings(),
        "services": await db.get_services(active_only=False),
        "reviews": await db.get_reviews(active_only=False),
        "gallery": await db.get_gallery(active_only=False),
        "posts": await db.get_blog_posts(visible_only=False),
    })

@app.post("/admin/settings")
async def admin_save_settings(request: Request, _: str = Depends(require_admin)):
    form = dict(await request.form())
    allowed = {
        "master_name", "city", "phone", "telegram_url", "working_hours", "area_served",
        "about_text", "promo_text", "home_title", "home_description", "blog_title", "blog_description",
    }
    await db.update_settings({key: form.get(key, "") for key in allowed})
    return RedirectResponse("/admin", status_code=303)

@app.post("/admin/services/save")
async def admin_save_service(request: Request, _: str = Depends(require_admin)):
    await db.save_service(dict(await request.form()))
    return RedirectResponse("/admin#services", status_code=303)

@app.post("/admin/services/{service_id}/delete")
async def admin_delete_service(service_id: int, _: str = Depends(require_admin)):
    await db.delete_service(service_id)
    return RedirectResponse("/admin#services", status_code=303)

@app.post("/admin/reviews/save")
async def admin_save_review(request: Request, _: str = Depends(require_admin)):
    await db.save_review(dict(await request.form()))
    return RedirectResponse("/admin#reviews", status_code=303)

@app.post("/admin/reviews/{review_id}/delete")
async def admin_delete_review(review_id: int, _: str = Depends(require_admin)):
    await db.delete_review(review_id)
    return RedirectResponse("/admin#reviews", status_code=303)

@app.post("/admin/gallery/upload")
async def admin_upload_gallery(
    image: UploadFile = File(...),
    request: Request = None,
    _: str = Depends(require_admin),
):
    form = dict(await request.form())
    image_path = await save_upload(image, "static/uploads")
    await db.save_gallery_item(image_path, form.get("alt_text") or "Работа визажиста", int(form.get("sort_order") or 0))
    return RedirectResponse("/admin#gallery", status_code=303)

@app.post("/admin/gallery/save")
async def admin_save_gallery(request: Request, _: str = Depends(require_admin)):
    await db.update_gallery_item(dict(await request.form()))
    return RedirectResponse("/admin#gallery", status_code=303)

@app.post("/admin/gallery/{item_id}/delete")
async def admin_delete_gallery(item_id: int, _: str = Depends(require_admin)):
    await db.delete_gallery_item(item_id)
    return RedirectResponse("/admin#gallery", status_code=303)

@app.post("/admin/blog/save")
async def admin_save_blog(request: Request, _: str = Depends(require_admin)):
    await db.save_blog_post(dict(await request.form()))
    return RedirectResponse("/admin#blog", status_code=303)

@app.post("/admin/blog/{post_id}/toggle")
async def admin_toggle_blog(post_id: int, _: str = Depends(require_admin)):
    await db.toggle_blog_post(post_id)
    return RedirectResponse("/admin#blog", status_code=303)

@app.post("/admin/blog/import")
async def admin_import_blog(_: str = Depends(require_admin)):
    imported = await db.import_telegram_updates()
    logger.info(f"Telegram import completed: {imported} posts")
    return RedirectResponse("/admin#blog", status_code=303)

# ========== ОБРАБОТЧИКИ ОШИБОК ==========
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Обработчик HTTP ошибок"""
    logger.warning(f"HTTP ошибка {exc.status_code}: {exc.detail} - URL: {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Обработчик общих ошибок"""
    logger.error(f"Необработанная ошибка: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Внутренняя ошибка сервера",
            "status_code": 500
        }
    )

# ========== ЗАПУСК ПРИЛОЖЕНИЯ ==========
if __name__ == "__main__":
    import uvicorn

    logger.info(">>> Запуск сервера Uvicorn...")
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
