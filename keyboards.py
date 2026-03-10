from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить задачу"), KeyboardButton(text="📋 Мои задачи")],
        [KeyboardButton(text="✅ Выполнить задачу"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="🔥 Мотивация"), KeyboardButton(text="ℹ️ Помощь")],
    ],
    resize_keyboard=True
)
