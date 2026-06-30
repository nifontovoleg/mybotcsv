import os
from pathlib import Path
from typing import Optional


def _load_token_from_env_file() -> Optional[str]:
    """
    Пробует прочитать BOT_TOKEN из .env-файла.

    Для удобства смотрим несколько путей:
    - .env в корне проекта;
    - app/.env;
    - app/keyboards/.env (где у тебя уже лежит токен).
    """

    possible_paths = [
        Path(".env"),
        Path("app/.env"),
        Path("app/keyboards/.env"),
    ]

    for env_path in possible_paths:
        if not env_path.exists():
            continue

        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()

            # Пропускаем пустые строки и комментарии.
            if not stripped or stripped.startswith("#"):
                continue

            if stripped.startswith("BOT_TOKEN="):
                # Берём всё после "BOT_TOKEN=" и убираем кавычки по краям.
                value = stripped.split("=", 1)[1].strip()
                return value.strip('"').strip("'")

    return None


def get_bot_token() -> str:
    """
    Возвращает токен Telegram-бота.

    1. Сначала пытаемся взять его из переменной окружения BOT_TOKEN.
    2. Если там пусто — читаем из .env-файла (несколько типовых путей).
    """

    # 1. Пробуем получить токен из переменных окружения.
    token = os.getenv("BOT_TOKEN")

    # 2. Если не нашли — пробуем прочитать из .env.
    if not token:
        token = _load_token_from_env_file()

    if not token:
        # Если токена нет ни там, ни там — бросаем понятную ошибку.
        raise RuntimeError(
            "Не найден токен бота.\n"
            "Установите переменную окружения BOT_TOKEN или добавьте её в один из файлов:\n"
            "- .env\n"
            "- app/.env\n"
            "- app/keyboards/.env\n"
            "Пример строки в файле:\n"
            "BOT_TOKEN=123456:ABC-DEF"
        )

    return token


