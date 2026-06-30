import asyncio
import csv
import logging
import re
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardMarkup, Message

from app.db.database import (
    Task,
    add_task,
    clear_reminder,
    delete_task,
    get_all_tasks,
    get_due_reminders,
    get_task,
    set_reminder,
    set_task_done,
    update_task_text,
)
from app.keyboards.main_menu import get_tasks_keyboard


logger = logging.getLogger(__name__)

tasks_router = Router()


class AddNote(StatesGroup):
    """FSM для добавления заметки: ждём текст."""

    waiting_for_text = State()


class EditNote(StatesGroup):
    """FSM для редактирования заметки: ждём новый текст."""

    waiting_for_text = State()


class RemindNote(StatesGroup):
    """FSM для установки напоминания: ждём время."""

    waiting_for_time = State()


# --------------------------------------------------------------------------- #
# Вспомогательные функции
# --------------------------------------------------------------------------- #

# Единицы для относительного времени напоминания: "10m", "2h", "1d", "30s".
_RELATIVE_UNITS = {
    "s": "seconds",
    "с": "seconds",
    "m": "minutes",
    "м": "minutes",
    "мин": "minutes",
    "h": "hours",
    "ч": "hours",
    "d": "days",
    "д": "days",
}


def parse_remind_time(text: str, now: Optional[datetime] = None) -> Optional[datetime]:
    """
    Разбирает введённое пользователем время напоминания.

    Поддерживаемые форматы:
    - относительное: "30s", "10m", "2h", "1d" (а также с русскими буквами: "10мин", "2ч", "1д");
    - время сегодня: "15:30" (если уже прошло — переносим на завтра);
    - дата и время: "2026-07-01 15:30".

    Возвращает datetime или None, если разобрать не удалось.
    """

    now = now or datetime.now()
    value = text.strip().lower().replace(",", ".")

    # 1. Относительное время вида "<число><единица>".
    match = re.fullmatch(r"(\d+)\s*([a-zа-я]+)", value)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        if unit in _RELATIVE_UNITS:
            return now + timedelta(**{_RELATIVE_UNITS[unit]: amount})
        return None

    # 2. Полные дата и время.
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    # 3. Только время "HH:MM" — на сегодня, либо на завтра, если уже прошло.
    try:
        parsed_time = datetime.strptime(value, "%H:%M").time()
    except ValueError:
        return None

    candidate = now.replace(
        hour=parsed_time.hour,
        minute=parsed_time.minute,
        second=0,
        microsecond=0,
    )
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def _format_task_line(index: int, task: Task) -> str:
    """Формирует одну строку списка для заметки."""

    mark = "✅" if task.done else "🔘"
    line = f"{index}. {mark} [{task.user}] {task.text}"
    if task.remind_at:
        # Показываем время без секунд для компактности.
        pretty = task.remind_at.replace("T", " ")[:16]
        line += f"\n    ⏰ напоминание: {pretty}"
    return line


def _render_tasks_list(tasks: List[Task]) -> Tuple[str, InlineKeyboardMarkup]:
    """
    Готовит текст списка заметок и inline-клавиатуру под ним.
    """

    lines = [_format_task_line(index, task) for index, task in enumerate(tasks, start=1)]

    legend = "Кнопки под номером: ✅ готово · ✏️ изменить · ⏰ напомнить · ❌ удалить"
    text = "Список заметок:\n\n" + "\n".join(lines) + "\n\n" + legend
    return text, get_tasks_keyboard(tasks)


async def _refresh_list_message(callback: CallbackQuery) -> None:
    """
    Перерисовывает сообщение со списком заметок после изменения.
    """

    tasks = get_all_tasks()

    if not tasks:
        await callback.message.edit_text("Список заметок пуст. Добавьте заметку командой /add.")
        return

    text, keyboard = _render_tasks_list(tasks)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        # Telegram кидает ошибку, если текст и клавиатура не изменились — игнорируем.
        pass


# --------------------------------------------------------------------------- #
# Команды
# --------------------------------------------------------------------------- #


@tasks_router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext) -> None:
    """Команда /add — начинает добавление заметки через FSM."""

    await state.set_state(AddNote.waiting_for_text)
    await message.answer(
        "Добавление новой заметки.\n"
        "Пришли текст заметки одним сообщением.\n\n"
        "Чтобы отменить — отправь /cancel."
    )


@tasks_router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Команда /cancel — выход из любого активного состояния FSM."""

    if await state.get_state() is None:
        await message.answer("Сейчас нечего отменять.")
        return

    await state.clear()
    await message.answer("Действие отменено.")


@tasks_router.message(AddNote.waiting_for_text)
async def process_note_text(message: Message, state: FSMContext) -> None:
    """Принимает текст новой заметки и сохраняет её."""

    text = (message.text or "").strip()
    if not text:
        await message.answer("Пустое сообщение. Пришли содержательный текст заметки.")
        return

    user_name = message.from_user.username or message.from_user.full_name
    add_task(text=text, user=user_name)

    await state.clear()
    await message.answer(f"Заметка сохранена:\n{text}")


@tasks_router.message(EditNote.waiting_for_text)
async def process_edit_text(message: Message, state: FSMContext) -> None:
    """Принимает новый текст заметки при редактировании."""

    text = (message.text or "").strip()
    if not text:
        await message.answer("Пустое сообщение. Пришли новый текст заметки.")
        return

    data = await state.get_data()
    task_id = data.get("task_id")
    await state.clear()

    if task_id is None or not update_task_text(task_id, text):
        await message.answer("Не удалось изменить заметку — возможно, она была удалена.")
        return

    await message.answer(f"Заметка обновлена:\n{text}")


@tasks_router.message(RemindNote.waiting_for_time)
async def process_remind_time(message: Message, state: FSMContext) -> None:
    """Принимает время напоминания и сохраняет его."""

    remind_dt = parse_remind_time(message.text or "")
    if remind_dt is None:
        await message.answer(
            "Не понял время. Примеры:\n"
            "• 10m — через 10 минут\n"
            "• 2h — через 2 часа\n"
            "• 15:30 — сегодня в 15:30\n"
            "• 2026-07-01 09:00 — конкретные дата и время\n\n"
            "Попробуй ещё раз или отправь /cancel."
        )
        return

    if remind_dt <= datetime.now():
        await message.answer("Это время уже прошло. Укажи момент в будущем.")
        return

    data = await state.get_data()
    task_id = data.get("task_id")
    await state.clear()

    if task_id is None or get_task(task_id) is None:
        await message.answer("Не удалось поставить напоминание — заметка не найдена.")
        return

    set_reminder(task_id, remind_dt.isoformat(timespec="seconds"), message.chat.id)
    await message.answer(f"⏰ Напомню {remind_dt.strftime('%Y-%m-%d %H:%M')}.")


@tasks_router.message(Command("list"))
async def cmd_list(message: Message) -> None:
    """Команда /list — показывает все заметки с inline-кнопками."""

    tasks = get_all_tasks()
    if not tasks:
        await message.answer("Список заметок пуст. Добавьте первую заметку командой /add.")
        return

    text, keyboard = _render_tasks_list(tasks)
    await message.answer(text, reply_markup=keyboard)


@tasks_router.message(Command("edit"))
async def cmd_edit(message: Message) -> None:
    """Команда /edit — показывает список, редактирование через кнопку ✏️."""

    tasks = get_all_tasks()
    if not tasks:
        await message.answer("Список заметок пуст, редактировать нечего.")
        return

    text, keyboard = _render_tasks_list(tasks)
    await message.answer("Выбери заметку для изменения кнопкой ✏️.\n\n" + text, reply_markup=keyboard)


@tasks_router.message(Command("delete"))
async def cmd_delete(message: Message) -> None:
    """Команда /delete — показывает список, удаление через кнопку ❌."""

    tasks = get_all_tasks()
    if not tasks:
        await message.answer("Список заметок пуст, удалять нечего.")
        return

    text, keyboard = _render_tasks_list(tasks)
    await message.answer("Выбери заметку для удаления кнопкой ❌.\n\n" + text, reply_markup=keyboard)


@tasks_router.message(Command("list_csv"))
async def cmd_list_csv(message: Message) -> None:
    """Команда /list_csv — выгружает все заметки в CSV-файл."""

    tasks = get_all_tasks()
    if not tasks:
        await message.answer("Список заметок пуст. Добавлять нечего в CSV-файл.")
        return

    # delete=False нужен, чтобы на Windows закрыть файл и затем открыть его для отправки.
    with tempfile.NamedTemporaryFile("w", newline="", suffix=".csv", delete=False, encoding="utf-8") as tmp_file:
        tmp_path = Path(tmp_file.name)
        writer = csv.writer(tmp_file, delimiter=";")
        writer.writerow(["id", "text", "user", "created_at", "done", "remind_at"])
        for task in tasks:
            writer.writerow(
                [task.id, task.text, task.user, task.created_at, int(task.done), task.remind_at or ""]
            )

    csv_file = FSInputFile(path=tmp_path, filename="tasks.csv")
    await message.answer_document(csv_file, caption="Вот ваш список заметок в формате CSV.")

    try:
        tmp_path.unlink(missing_ok=True)
    except OSError:
        pass


# --------------------------------------------------------------------------- #
# Колбэки inline-кнопок
# --------------------------------------------------------------------------- #


@tasks_router.callback_query(F.data.startswith("done:"))
async def cb_toggle_done(callback: CallbackQuery) -> None:
    """Переключает статус «выполнено / не выполнено»."""

    task_id = int(callback.data.split(":", 1)[1])
    task = get_task(task_id)

    if task is None:
        await callback.answer("Заметка уже удалена.", show_alert=True)
        await _refresh_list_message(callback)
        return

    set_task_done(task_id, not task.done)
    await callback.answer("Готово!" if not task.done else "Снова в работе.")
    await _refresh_list_message(callback)


@tasks_router.callback_query(F.data.startswith("del:"))
async def cb_delete(callback: CallbackQuery) -> None:
    """Удаляет заметку."""

    task_id = int(callback.data.split(":", 1)[1])
    deleted = delete_task(task_id)
    await callback.answer("Заметка удалена." if deleted else "Заметка уже удалена.")
    await _refresh_list_message(callback)


@tasks_router.callback_query(F.data.startswith("edit:"))
async def cb_edit(callback: CallbackQuery, state: FSMContext) -> None:
    """Запускает редактирование заметки через FSM."""

    task_id = int(callback.data.split(":", 1)[1])
    task = get_task(task_id)

    if task is None:
        await callback.answer("Заметка уже удалена.", show_alert=True)
        await _refresh_list_message(callback)
        return

    await state.set_state(EditNote.waiting_for_text)
    await state.update_data(task_id=task_id)
    await callback.answer()
    await callback.message.answer(
        f"Изменение заметки:\n«{task.text}»\n\n"
        "Пришли новый текст одним сообщением (или /cancel)."
    )


@tasks_router.callback_query(F.data.startswith("rem:"))
async def cb_remind(callback: CallbackQuery, state: FSMContext) -> None:
    """Запускает установку напоминания через FSM."""

    task_id = int(callback.data.split(":", 1)[1])
    task = get_task(task_id)

    if task is None:
        await callback.answer("Заметка уже удалена.", show_alert=True)
        await _refresh_list_message(callback)
        return

    await state.set_state(RemindNote.waiting_for_time)
    await state.update_data(task_id=task_id)
    await callback.answer()
    await callback.message.answer(
        f"Напоминание для заметки:\n«{task.text}»\n\n"
        "Когда напомнить? Примеры:\n"
        "• 10m — через 10 минут\n"
        "• 2h — через 2 часа\n"
        "• 15:30 — сегодня в 15:30\n"
        "• 2026-07-01 09:00 — дата и время\n\n"
        "Отправь /cancel для отмены."
    )


# --------------------------------------------------------------------------- #
# Фоновый цикл напоминаний
# --------------------------------------------------------------------------- #


async def reminders_loop(bot: Bot, poll_interval: int = 15) -> None:
    """
    Бесконечный цикл: периодически проверяет наступившие напоминания
    и отправляет их пользователям, после чего снимает напоминание.

    Запускается как фоновая задача при старте бота.
    """

    while True:
        try:
            now_iso = datetime.now().isoformat(timespec="seconds")
            for task in get_due_reminders(now_iso):
                if task.remind_chat_id is None:
                    clear_reminder(task.id)
                    continue
                try:
                    await bot.send_message(
                        task.remind_chat_id,
                        f"⏰ Напоминание о заметке:\n{task.text}",
                    )
                finally:
                    # Снимаем напоминание, даже если отправка не удалась,
                    # чтобы не спамить одним и тем же каждые 15 секунд.
                    clear_reminder(task.id)
        except Exception:
            logger.exception("Ошибка в цикле напоминаний")

        await asyncio.sleep(poll_interval)
