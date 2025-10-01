"""
FastAPI Backend для TinaBorke.Art
Основной файл приложения с интеграцией Telegram бота
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from contextlib import asynccontextmanager
import logging
import asyncio
from typing import List, Optional
from datetime import datetime
import os
from pydantic import BaseModel, validator
import sqlite3
import aiosqlite
import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import json

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
class Settings:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID", "")
    STAFF_TELEGRAM_IDS = os.getenv("STAFF_TELEGRAM_IDS", "").split(",")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tinaborke.db")
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
    
settings = Settings()

# Pydantic модели
class BookingCreate(BaseModel):
    name: str
    phone: str
    service: Optional[str] = None
    date: Optional[str] = None
    message: Optional[str] = None
    
    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Имя не может быть пустым')
        return v.strip()
    
    @validator('phone')
    def phone_must_be_valid(cls, v):
        # Базовая валидация телефона
        cleaned = ''.join(filter(str.isdigit, v))
        if len(cleaned) < 10:
            raise ValueError('Некорректный номер телефона')
        return v

class BookingResponse(BaseModel):
    id: int
    name: str
    phone: str
    service: Optional[str]
    date: Optional[str]
    message: Optional[str]
    created_at: datetime
    status: str = "new"

# База данных
class Database:
    def __init__(self, db_path: str = "./tinaborke.db"):
        self.db_path = db_path
        
    async def init_db(self):
        """Инициализация базы данных"""
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
            
    async def create_booking(self, booking: BookingCreate) -> int:
        """Создание новой заявки"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO bookings (name, phone, service, date, message)
                VALUES (?, ?, ?, ?, ?)
            """, (booking.name, booking.phone, booking.service, booking.date, booking.message))
            await db.commit()
            return cursor.lastrowid
            
    async def get_booking(self, booking_id: int) -> Optional[dict]:
        """Получение заявки по ID"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT * FROM bookings WHERE id = ?
            """, (booking_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    columns = [column[0] for column in cursor.description]
                    return dict(zip(columns, row))
                return None
                
    async def get_all_bookings(self, limit: int = 100) -> List[dict]:
        """Получение всех заявок"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT * FROM bookings ORDER BY created_at DESC LIMIT ?
            """, (limit,)) as cursor:
                rows = await cursor.fetchall()
                columns = [column[0] for column in cursor.description]
                return [dict(zip(columns, row)) for row in rows]

# Telegram Bot Service
class TelegramService:
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.admin_id = settings.ADMIN_TELEGRAM_ID
        self.staff_ids = [id.strip() for id in settings.STAFF_TELEGRAM_IDS if id.strip()]
        self.bot = None
        self.application = None
        
    async def init_bot(self):
        """Инициализация Telegram бота"""
        if not self.bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN не настроен")
            return
            
        try:
            self.application = Application.builder().token(self.bot_token).build()
            self.bot = self.application.bot
            
            # Добавляем обработчики команд
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(CommandHandler("status", self.status_command))
            
            # Запускаем бота
            await self.application.initialize()
            await self.application.start()
            
            logger.info("Telegram bot инициализирован успешно")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации Telegram бота: {e}")
            
    async def send_booking_notification(self, booking: dict):
        """Отправка уведомления о новой заявке"""
        if not self.bot:
            logger.warning("Telegram bot не инициализирован")
            return
            
        message = f"""
🎭 **Новая заявка на TinaBorke.Art**

👤 **Имя:** {booking['name']}
📱 **Телефон:** {booking['phone']}
💄 **Услуга:** {booking.get('service', 'Не указана')}
📅 **Дата:** {booking.get('date', 'Не указана')}
💬 **Сообщение:** {booking.get('message', 'Не указано')}

⏰ **Время заявки:** {booking['created_at']}
🆔 **ID заявки:** {booking['id']}
        """
        
        try:
            # Отправляем администратору
            if self.admin_id:
                await self.bot.send_message(
                    chat_id=self.admin_id,
                    text=message,
                    parse_mode='Markdown'
                )
                
            # Отправляем сотрудникам
            for staff_id in self.staff_ids:
                if staff_id and staff_id != self.admin_id:
                    try:
                        await self.bot.send_message(
                            chat_id=staff_id,
                            text=message,
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logger.error(f"Ошибка отправки уведомления сотруднику {staff_id}: {e}")
                        
            logger.info(f"Уведомления отправлены для заявки {booking['id']}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомлений: {e}")
            
    async def start_command(self, update, context):
        """Обработчик команды /start"""
        welcome_message = """
🎭 Добро пожаловать в TinaBorke.Art!

Я буду уведомлять о новых заявках на услуги визажа и грима.

Доступные команды:
/help - Справка по командам
/status - Статус бота
        """
        await update.message.reply_text(welcome_message)
        
    async def help_command(self, update, context):
        """Обработчик команды /help"""
        help_message = """
🤖 **Доступные команды:**

/start - Начать работу с ботом
/help - Показать эту справку
/status - Проверить статус бота

📝 **Информация:**
Бот автоматически уведомляет о новых заявках с сайта TinaBorke.Art
        """
        await update.message.reply_text(help_message, parse_mode='Markdown')
        
    async def status_command(self, update, context):
        """Обработчик команды /status"""
        status_message = f"""
✅ **Статус бота:** Активен
🕐 **Время:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🤖 **Версия:** 1.0.0
        """
        await update.message.reply_text(status_message, parse_mode='Markdown')

# Инициализация сервисов
db = Database()
telegram_service = TelegramService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager для FastAPI"""
    # Startup
    await db.init_db()
    await telegram_service.init_bot()
    logger.info("Приложение запущено")
    
    yield
    
    # Shutdown
    if telegram_service.application:
        await telegram_service.application.stop()
    logger.info("Приложение остановлено")

# FastAPI приложение
app = FastAPI(
    title="TinaBorke.Art API",
    description="API для сайта визажиста-гримера Тины Борке",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статические файлы и шаблоны
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Маршруты
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Главная страница"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """Проверка здоровья приложения"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.post("/api/booking", response_model=dict)
async def create_booking(booking: BookingCreate, background_tasks: BackgroundTasks):
    """Создание новой заявки"""
    try:
        # Сохраняем в базу данных
        booking_id = await db.create_booking(booking)
        
        # Получаем созданную заявку
        created_booking = await db.get_booking(booking_id)
        
        if created_booking:
            # Отправляем уведомления в фоне
            background_tasks.add_task(
                telegram_service.send_booking_notification, 
                created_booking
            )
            
        return {
            "success": True,
            "message": "Заявка успешно создана",
            "booking_id": booking_id
        }
        
    except Exception as e:
        logger.error(f"Ошибка создания заявки: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")

@app.post("/api/quick-booking", response_model=dict)
async def create_quick_booking(booking: BookingCreate, background_tasks: BackgroundTasks):
    """Быстрая заявка (алиас для обычной заявки)"""
    return await create_booking(booking, background_tasks)

@app.get("/api/bookings", response_model=List[dict])
async def get_bookings(limit: int = 100):
    """Получение списка заявок (для админ панели)"""
    try:
        bookings = await db.get_all_bookings(limit)
        return bookings
    except Exception as e:
        logger.error(f"Ошибка получения заявок: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")

@app.get("/api/booking/{booking_id}", response_model=dict)
async def get_booking(booking_id: int):
    """Получение заявки по ID"""
    try:
        booking = await db.get_booking(booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Заявка не найдена")
        return booking
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения заявки: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Webhook для Telegram бота"""
    try:
        if telegram_service.application:
            data = await request.json()
            update = telegram.Update.de_json(data, telegram_service.bot)
            await telegram_service.application.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Ошибка обработки webhook: {e}")
        return {"status": "error", "message": str(e)}

# Обработчик ошибок
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Обработчик HTTP ошибок"""
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
    logger.error(f"Необработанная ошибка: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Внутренняя ошибка сервера",
            "status_code": 500
        }
    )

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level="info"
    )