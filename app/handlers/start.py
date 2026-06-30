from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.db.database import init_db


# Router — это "контейнер" для группы хэндлеров (обработчиков).
start_router = Router()


@start_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """
    Обработчик команды /start.

    Гарантирует, что таблица в базе данных создана, и отправляет
    приветственное сообщение с описанием команд.
    """

    # На всякий случай гарантируем, что таблица существует.
    init_db()

    text = (
        "Привет! Я бот заметок.\n\n"
        "Команды:\n"
        "/start — привет\n"
        "/add — добавить новую заметку\n"
        "/list — все заметки\n"
        "/list_csv — все заметки в файле CSV\n"
        "/edit — изменить заметку\n"
        "/delete — начать удаление заметки\n"
        "/cancel — отменить текущее действие\n\n"
        "В списке /list под каждой заметкой есть кнопки:\n"
        "✅ готово · ✏️ изменить · ⏰ напомнить · ❌ удалить."
    )

    await message.answer(text)
