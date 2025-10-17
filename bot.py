# bot.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.database import create_tables
from handlers import user_handlers, admin_handlers # Пока только пользовательские

# Включаем логирование, чтобы видеть в консоли, что происходит
logging.basicConfig(level=logging.INFO)

async def main():
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage()) # FSM будет хранить состояния в памяти

    # Создаем таблицы в БД при старте
    await create_tables()

    # Регистрируем роутеры (обработчики)
    dp.include_router(admin_handlers.router)  # Пока не используем, но оставим для структуры
    dp.include_router(user_handlers.router)
    # Позже добавим роутер для админа

    # Запускаем бота
    await bot.delete_webhook(drop_pending_updates=True) # Пропускаем старые апдейты
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())