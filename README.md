# Telegram Notes Bot

Учебный Telegram-бот для заметок на **Python**, **aiogram 3** и **SQLite**.

Бот умеет добавлять заметки, показывать список, отмечать заметки выполненными, редактировать их, удалять, ставить напоминания и выгружать все данные в CSV-файл.

## Repository Info

**Название репозитория:** `telegram-notes-bot`

**Description для GitHub:**

```text
Telegram notes bot built with Python, aiogram 3 and SQLite. Supports notes, inline buttons, reminders, editing, CSV export and FSM-based dialogs.
```

**Topics / теги для GitHub:**

```text
python, telegram-bot, aiogram, aiogram3, sqlite, notes, reminders, csv-export, fsm, inline-keyboard, beginner-project
```

## Features

- Добавление заметок через команду `/add`.
- Просмотр всех заметок через `/list`.
- Inline-кнопки под заметками: готово, изменить, напомнить, удалить.
- Редактирование заметок через `/edit` или кнопку `✏️`.
- Напоминания по времени через кнопку `⏰`.
- Экспорт всех заметок в CSV через `/list_csv`.
- FSM-диалоги на `aiogram.fsm` для ввода текста и времени.
- Хранение данных в локальной базе `SQLite`.
- Автоматическое меню команд Telegram через `set_my_commands`.

## Bot Commands

| Команда | Описание |
| --- | --- |
| `/start` | Приветствие и список возможностей |
| `/add` | Добавить новую заметку |
| `/list` | Показать все заметки |
| `/list_csv` | Скачать заметки в CSV-файле |
| `/edit` | Начать редактирование заметки |
| `/delete` | Начать удаление заметки |
| `/cancel` | Отменить текущее действие |

## Reminder Formats

Бот понимает несколько форматов времени для напоминаний:

```text
10m                 через 10 минут
2h                  через 2 часа
1d                  через 1 день
15:30               сегодня в 15:30 или завтра, если время уже прошло
2026-07-01 09:00    конкретная дата и время
```

## Tech Stack

- Python 3.10+
- aiogram 3
- SQLite
- FSM
- Telegram Bot API

## Project Structure

```text
mybotcsv/
├── main.py                     # точка входа, запуск бота, меню команд, напоминания
├── requirements.txt            # зависимости проекта
├── README.md                   # описание проекта
├── tasks.db                    # локальная SQLite-база данных
└── app/
    ├── config.py               # получение BOT_TOKEN
    ├── db/
    │   └── database.py         # функции работы с SQLite
    ├── handlers/
    │   ├── start.py            # команда /start
    │   └── tasks.py            # команды, FSM, inline-кнопки, напоминания
    └── keyboards/
        └── main_menu.py        # reply и inline-клавиатуры
```

## Installation

1. Склонируйте репозиторий:

```bash
git clone https://github.com/USERNAME/telegram-notes-bot.git
cd telegram-notes-bot
```

2. Создайте виртуальное окружение:

```bash
python -m venv venv
```

3. Активируйте виртуальное окружение.

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Linux / macOS:

```bash
source venv/bin/activate
```

4. Установите зависимости:

```bash
pip install -r requirements.txt
```

## Configuration

Создайте переменную окружения `BOT_TOKEN`:

Windows PowerShell:

```powershell
$env:BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
```

Или создайте файл `.env` в корне проекта:

```text
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
```

Токен можно получить у [@BotFather](https://t.me/BotFather).

## Run

```bash
python main.py
```

После запуска откройте своего бота в Telegram и отправьте:

```text
/start
```

## Database

Данные хранятся в файле `tasks.db` в корне проекта.

Если база уже существовала раньше, недостающие колонки (`done`, `remind_at`, `remind_chat_id`) добавляются автоматически при старте бота.

## Educational Purpose

Проект хорошо подходит для изучения:

- создания Telegram-ботов на `aiogram 3`;
- работы с командами и callback-кнопками;
- FSM-сценариев;
- хранения данных в SQLite;
- фоновых задач в асинхронном Python;
- экспорта данных в CSV.
