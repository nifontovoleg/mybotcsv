import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional


# Имя файла базы данных.
DB_FILE = Path("tasks.db")


@dataclass
class Task:
    """
    Простая структура данных для заметки.

    dataclass автоматически создаёт конструктор и __repr__,
    что делает код короче и удобнее для чтения.
    """

    id: int
    text: str
    user: str
    created_at: str
    done: bool = False
    remind_at: Optional[str] = None
    remind_chat_id: Optional[int] = None


def init_db() -> None:
    """
    Создаёт таблицу tasks, если её ещё нет, и при необходимости
    добавляет недостающие колонки (простейшая «миграция»).

    Вызываем эту функцию один раз при старте бота.
    """

    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                user TEXT NOT NULL,
                created_at TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                remind_at TEXT,
                remind_chat_id INTEGER
            );
            """
        )

        # Миграция для старых баз: добавляем недостающие колонки.
        columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks);")}
        if "done" not in columns:
            conn.execute("ALTER TABLE tasks ADD COLUMN done INTEGER NOT NULL DEFAULT 0;")
        if "remind_at" not in columns:
            conn.execute("ALTER TABLE tasks ADD COLUMN remind_at TEXT;")
        if "remind_chat_id" not in columns:
            conn.execute("ALTER TABLE tasks ADD COLUMN remind_chat_id INTEGER;")

        conn.commit()


@contextmanager
def get_connection() -> Iterable[sqlite3.Connection]:
    """
    Контекстный менеджер для подключения к базе данных.

    Пример использования:

    with get_connection() as conn:
        conn.execute("SELECT 1")

    Такое оформление гарантирует, что соединение будет закрыто.
    """

    conn = sqlite3.connect(DB_FILE)
    try:
        yield conn
    finally:
        conn.close()


def _row_to_task(row: tuple) -> Task:
    """Превращает строку из БД в объект Task."""

    return Task(
        id=row[0],
        text=row[1],
        user=row[2],
        created_at=row[3],
        done=bool(row[4]),
        remind_at=row[5],
        remind_chat_id=row[6],
    )


# Список колонок в едином порядке, чтобы все SELECT'ы были согласованы.
_SELECT_COLUMNS = "id, text, user, created_at, done, remind_at, remind_chat_id"


def add_task(text: str, user: str) -> None:
    """
    Добавляет новую заметку в таблицу tasks.

    :param text: текст заметки
    :param user: имя пользователя (например, username из Telegram)
    """

    # Используем локальное время машины, чтобы время заметок
    # совпадало с тем, что видит пользователь.
    created_at = datetime.now().isoformat(timespec="seconds")

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO tasks (text, user, created_at) VALUES (?, ?, ?);",
            (text, user, created_at),
        )
        conn.commit()


def get_all_tasks() -> List[Task]:
    """
    Возвращает все заметки из таблицы tasks.
    """

    with get_connection() as conn:
        cursor = conn.execute(
            f"SELECT {_SELECT_COLUMNS} FROM tasks ORDER BY id ASC;"
        )
        rows = cursor.fetchall()

    return [_row_to_task(row) for row in rows]


def get_task(task_id: int) -> Optional[Task]:
    """
    Возвращает одну заметку по её id или None, если такой нет.
    """

    with get_connection() as conn:
        cursor = conn.execute(
            f"SELECT {_SELECT_COLUMNS} FROM tasks WHERE id = ?;",
            (task_id,),
        )
        row = cursor.fetchone()

    return _row_to_task(row) if row is not None else None


def update_task_text(task_id: int, text: str) -> bool:
    """
    Меняет текст существующей заметки.

    Возвращает True, если заметка нашлась и была обновлена.
    """

    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE tasks SET text = ? WHERE id = ?;",
            (text, task_id),
        )
        conn.commit()

    return cursor.rowcount > 0


def set_task_done(task_id: int, done: bool) -> bool:
    """
    Помечает заметку как выполненную или снова невыполненной.

    Возвращает True, если заметка нашлась и была обновлена.
    """

    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE tasks SET done = ? WHERE id = ?;",
            (1 if done else 0, task_id),
        )
        conn.commit()

    return cursor.rowcount > 0


def set_reminder(task_id: int, remind_at: str, chat_id: int) -> bool:
    """
    Устанавливает напоминание для заметки.

    :param remind_at: время напоминания в ISO-формате (например, 2026-07-01T15:00:00)
    :param chat_id: чат, в который нужно отправить напоминание
    """

    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE tasks SET remind_at = ?, remind_chat_id = ? WHERE id = ?;",
            (remind_at, chat_id, task_id),
        )
        conn.commit()

    return cursor.rowcount > 0


def clear_reminder(task_id: int) -> bool:
    """
    Снимает напоминание с заметки.
    """

    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE tasks SET remind_at = NULL, remind_chat_id = NULL WHERE id = ?;",
            (task_id,),
        )
        conn.commit()

    return cursor.rowcount > 0


def get_due_reminders(now_iso: str) -> List[Task]:
    """
    Возвращает заметки, у которых наступило время напоминания
    (remind_at задано и не позже текущего момента).
    """

    with get_connection() as conn:
        cursor = conn.execute(
            f"SELECT {_SELECT_COLUMNS} FROM tasks "
            "WHERE remind_at IS NOT NULL AND remind_at <= ? ORDER BY remind_at ASC;",
            (now_iso,),
        )
        rows = cursor.fetchall()

    return [_row_to_task(row) for row in rows]


def delete_task(task_id: int) -> bool:
    """
    Удаляет заметку по её id.

    Возвращает True, если заметка была удалена (нашлась в БД),
    и False, если заметки с таким id не существует.
    """

    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM tasks WHERE id = ?;", (task_id,))
        conn.commit()

    return cursor.rowcount > 0
