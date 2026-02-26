import asyncio
import logging
import os

from aiogram import Bot, Dispatcher

from app.config import get_bot_token
from app.handlers.start import start_router
from app.handlers.tasks import tasks_router


async def main() -> None:
    """
    Точка входа в приложение.

    Здесь мы:
    1. Создаём объект бота.
    2. Создаём диспетчер (Dispatcher), который будет получать апдейты от Telegram.
    3. Подключаем роутеры (файлы с хэндлерами команд).
    4. Запускаем бесконечный цикл обработки апдейтов (long polling).
    """

    # Включаем простой логгер, чтобы видеть, что делает бот.
    logging.basicConfig(level=logging.INFO)

    # Получаем токен бота из переменной окружения.
    # Такой подход безопаснее, чем хранить токен прямо в коде.
    token = get_bot_token()

    # Создаём экземпляр бота и диспетчера.
    bot = Bot(token=token)
    dp = Dispatcher()

    # Регистрируем наши роутеры (команды /start, /add, /list, /list_csv).
    dp.include_router(start_router)
    dp.include_router(tasks_router)

    # Удаляем старый webhook (если он был), чтобы использовать long polling.
    await bot.delete_webhook(drop_pending_updates=True)

    # Запускаем бесконечный цикл обработки апдейтов.
    await dp.start_polling(bot)


if __name__ == "__main__":
    # Запускаем асинхронную функцию main при старте скрипта.
    asyncio.run(main())

