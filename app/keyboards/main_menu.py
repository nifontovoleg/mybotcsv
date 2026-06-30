from typing import List

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.db.database import Task


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Простая клавиатура с основными командами.

    Кнопки повторяют текст команд, чтобы пользователю не нужно было
    каждый раз вводить их руками.
    """

    buttons = [
        [KeyboardButton(text="/add")],
        [KeyboardButton(text="/list"), KeyboardButton(text="/list_csv")],
    ]

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,  # Клавиатура подстраивается под размер экрана.
        one_time_keyboard=False,  # Клавиатура остаётся на экране после нажатия.
    )


def get_tasks_keyboard(tasks: List[Task]) -> InlineKeyboardMarkup:
    """
    Inline-клавиатура для списка заметок.

    Под каждой заметкой ряд компактных кнопок (с её номером):
    - ✅/↩️ — переключить статус «выполнено»;
    - ✏️ — изменить текст;
    - ⏰ — поставить напоминание;
    - ❌ — удалить.

    В callback_data зашиваем действие и id заметки, например "done:5".
    """

    rows: List[List[InlineKeyboardButton]] = []

    for index, task in enumerate(tasks, start=1):
        status_icon = "↩️" if task.done else "✅"

        rows.append(
            [
                InlineKeyboardButton(text=f"{status_icon}{index}", callback_data=f"done:{task.id}"),
                InlineKeyboardButton(text=f"✏️{index}", callback_data=f"edit:{task.id}"),
                InlineKeyboardButton(text=f"⏰{index}", callback_data=f"rem:{task.id}"),
                InlineKeyboardButton(text=f"❌{index}", callback_data=f"del:{task.id}"),
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=rows)
