import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.config import get_bot_token
from app.db.database import init_db
from app.handlers.start import start_router
from app.handlers.tasks import reminders_loop, tasks_router


async def set_bot_commands(bot: Bot) -> None:
    """
    Регистрирует список команд, который Telegram показывает
    в синем меню «/» рядом с полем ввода.
    """

    commands = [
        BotCommand(command="start", description="привет"),
        BotCommand(command="add", description="добавить новую заметку"),
        BotCommand(command="list", description="все заметки"),
        BotCommand(command="list_csv", description="все заметки в файле CSV"),
        BotCommand(command="edit", description="изменить заметку"),
        BotCommand(command="delete", description="начать удаление заметки"),
        BotCommand(command="cancel", description="отменить текущее действие"),
    ]

    await bot.set_my_commands(commands)


async def main() -> None:
    """
    Точка входа в приложение.

    Здесь мы:
    1. Создаём объект бота и диспетчер с хранилищем состояний (FSM).
    2. Подключаем роутеры (файлы с хэндлерами команд).
    3. Инициализируем БД и меню команд.
    4. Запускаем фоновый цикл напоминаний и long polling.
    """

    # Включаем простой логгер, чтобы видеть, что делает бот.
    logging.basicConfig(level=logging.INFO)

    # Получаем токен бота (из переменной окружения или .env).
    token = get_bot_token()

    # Создаём экземпляр бота и диспетчера.
    # MemoryStorage хранит состояния FSM (например, ожидание текста заметки) в памяти.
    bot = Bot(token=token)
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем роутеры (команды /start, /add, /list, /list_csv, /edit, /delete).
    dp.include_router(start_router)
    dp.include_router(tasks_router)

    # Гарантируем, что таблица и все колонки существуют.
    init_db()

    # Удаляем старый webhook (если он был), чтобы использовать long polling.
    await bot.delete_webhook(drop_pending_updates=True)

    # Регистрируем команды в меню Telegram.
    await set_bot_commands(bot)

    # Запускаем фоновую задачу, которая рассылает напоминания.
    reminder_task = asyncio.create_task(reminders_loop(bot))

    try:
        # Запускаем бесконечный цикл обработки апдейтов.
        await dp.start_polling(bot)
    finally:
        # Аккуратно останавливаем фоновую задачу при выходе.
        reminder_task.cancel()


if __name__ == "__main__":
    # Запускаем асинхронную функцию main при старте скрипта.
    asyncio.run(main())
