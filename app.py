"""
FastAPI приложение для TinaBorke.Art
Упрощенная версия с исправлениями для запуска
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from contextlib import asynccontextmanager
import logging
import asyncio
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import os
from pathlib import Path
from pydantic import BaseModel, field_validator
import aiosqlite
import httpx
import json
import sys
import re
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
    DATABASE_URL = os.getenv("DATABASE_URL", "tinaborke.db")
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")

settings = Settings()

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
                await db.commit()
                logger.info("База данных успешно инициализирована")
        except Exception as e:
            logger.error(f"Ошибка инициализации базы данных: {e}")
            raise

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
logger.info("Сервисы инициализированы")

# ========== СОЗДАНИЕ ДИРЕКТОРИЙ ==========
logger.info("Проверка и создание необходимых директорий...")
directories = ["static", "static/css", "static/js", "static/images", "templates"]
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

    yield  # Здесь приложение работает

    # Shutdown логика
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

# ========== МАРШРУТЫ API ==========
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Главная страница сайта"""
    logger.info("Запрос главной страницы")
    if Path("templates").exists():
        logger.info("Рендеринг index.html из templates")
        return templates.TemplateResponse("index.html", {"request": request})
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

# ========== ОБРАБОТЧИКИ ОШИБОК ==========
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Обработчик HTTP ошибок"""
    logger.warning(f"HTTP ошибка {exc.status_code}: {exc.detail} - URL: {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
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