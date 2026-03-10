import asyncio
import random
from datetime import datetime, date, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from config import BOT_TOKEN
from keyboards import main_menu
from states import TaskFlow
from storage import load_db, save_db, get_user, add_task, list_tasks, complete_task, get_stats


MOTIVATION = [
    "Сделай маленький шаг — и ты уже не на нуле.",
    "Не жди мотивацию. Начни — она догонит.",
    "Сегодня ты строишь результат завтра.",
    "Лучше 20 минут работы, чем 2 часа прокрастинации.",
    "Сначала действие, потом вдохновение.",
]


def parse_due_date(text: str) -> date:
    """
    Принимает:
    - DD.MM.YYYY
    - сегодня
    - завтра
    """
    s = (text or "").strip().lower()
    today = date.today()

    if s in ("сегодня", "today"):
        return today
    if s in ("завтра", "tomorrow"):
        return today + timedelta(days=1)

    # DD.MM.YYYY
    return datetime.strptime(s, "%d.%m.%Y").date()


def format_tasks(tasks):
    if not tasks:
        return "📭 У тебя пока нет задач."
    lines = ["📋 Твои задачи:"]
    for i, t in enumerate(tasks, 1):
        # t = {"text":..., "due": "YYYY-MM-DD", "reminded": ...}
        due = t.get("due", "")
        lines.append(f"{i}) {t.get('text','')}  (до: {due})")
    return "\n".join(lines)


async def cmd_start(message: Message):
    text = (
        "Привет! Я FocusDrive 🤖\n"
        "Добавляй задачи с дедлайном, я напомню за день.\n\n"
        "Команды:\n"
        "/add — добавить задачу\n"
        "/tasks — список задач\n"
        "/done — отметить выполненной\n"
        "/stats — статистика\n"
        "/motivation — мотивация"
    )
    await message.answer(text, reply_markup=main_menu)


async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ Помощь:\n"
        "/add — добавить задачу (потом попросит дату)\n"
        "/tasks — список задач\n"
        "/done — выполнить задачу (по номеру)\n"
        "/stats — статистика\n"
        "/motivation — мотивация\n\n"
        "Формат даты: 31.03.2026 или слова: сегодня/завтра",
        reply_markup=main_menu
    )


# --- ДОБАВЛЕНИЕ ЗАДАЧИ В 2 ШАГА ---
async def cmd_add(message: Message, state: FSMContext):
    await state.set_state(TaskFlow.waiting_task_text)
    await message.answer("Напиши текст задачи одним сообщением ✍️", reply_markup=main_menu)


async def on_task_text(message: Message, state: FSMContext):
    task_text = (message.text or "").strip()
    if len(task_text) < 2:
        await message.answer("Слишком коротко. Напиши задачу нормально 🙂")
        return

    await state.update_data(task_text=task_text)
    await state.set_state(TaskFlow.waiting_task_due)
    await message.answer(
        "Теперь введи дату, когда нужно сделать задачу.\n"
        "Формат: 31.03.2026\n"
        "Можно написать: сегодня или завтра",
        reply_markup=main_menu
    )


async def on_task_due(message: Message, state: FSMContext):
    raw = (message.text or "").strip()
    try:
        d = parse_due_date(raw)
    except Exception:
        await message.answer("Не понял дату 😅 Напиши в формате ДД.ММ.ГГГГ (например 05.04.2026) или 'завтра'.")
        return

    # не даём поставить дедлайн в прошлом
    if d < date.today():
        await message.answer("Дата в прошлом. Введи сегодняшнюю или будущую дату 🙂")
        return

    data = await state.get_data()
    task_text = data.get("task_text", "").strip()

    db = load_db()
    user = get_user(db, message.from_user.id)
    add_task(user, task_text, d.isoformat())
    save_db(db)

    await state.clear()
    await message.answer(f"✅ Задача добавлена: «{task_text}»\n📅 Дедлайн: {d.isoformat()}", reply_markup=main_menu)


async def cmd_tasks(message: Message):
    db = load_db()
    user = get_user(db, message.from_user.id)
    tasks = list_tasks(user)
    await message.answer(format_tasks(tasks), reply_markup=main_menu)


# --- ВЫПОЛНИТЬ ЗАДАЧУ ---
async def cmd_done(message: Message, state: FSMContext):
    db = load_db()
    user = get_user(db, message.from_user.id)
    tasks = list_tasks(user)
    if not tasks:
        await message.answer("📭 Выполнять нечего — задач нет.", reply_markup=main_menu)
        return

    await state.set_state(TaskFlow.waiting_done_number)
    await message.answer(format_tasks(tasks) + "\n\nВведи номер задачи, которую выполнил(а):", reply_markup=main_menu)


async def on_done_number(message: Message, state: FSMContext):
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer("Нужно число (номер задачи). Например: 1")
        return

    num = int(raw)
    db = load_db()
    user = get_user(db, message.from_user.id)

    try:
        finished = complete_task(user, num)
    except IndexError:
        await message.answer("Такого номера нет. Проверь список задач и попробуй снова.")
        return

    save_db(db)
    await state.clear()
    await message.answer(f"🏁 Отлично! Выполнено: «{finished.get('text','')}»", reply_markup=main_menu)


async def cmd_stats(message: Message):
    db = load_db()
    user = get_user(db, message.from_user.id)
    s = get_stats(user)

    total = s["in_progress"] + s["done"]
    percent = 0 if total == 0 else round((s["done"] / total) * 100)

    await message.answer(
        "📊 Статистика:\n"
        f"✅ Выполнено: {s['done']}\n"
        f"🕒 В процессе: {s['in_progress']}\n"
        f"🏆 Продуктивность: {percent}%",
        reply_markup=main_menu
    )


async def cmd_motivation(message: Message):
    await message.answer("🔥 " + random.choice(MOTIVATION), reply_markup=main_menu)


async def unknown(message: Message):
    await message.answer(
        "Я не понимаю 😅\n"
        "Нажми «ℹ️ Помощь» или введи /help",
        reply_markup=main_menu
    )


# --- НАПОМИНАНИЯ ---
async def reminder_loop(bot: Bot):
    """
    Раз в минуту проверяет задачи и напоминает за 1 день до дедлайна.
    Напоминание отправляется 1 раз (reminded=True).
    """
    while True:
        try:
            db = load_db()
            today = date.today()
            tomorrow_iso = (today + timedelta(days=1)).isoformat()

            changed = False

            for uid_str, udata in db.items():
                tasks = udata.get("tasks", [])
                for t in tasks:
                    if t.get("due") == tomorrow_iso and not t.get("reminded", False):
                        await bot.send_message(
                            int(uid_str),
                            f"⏰ Напоминание!\nЗавтра дедлайн по задаче:\n«{t.get('text','')}»\n📅 {tomorrow_iso}"
                        )
                        t["reminded"] = True
                        changed = True

            if changed:
                save_db(db)

        except Exception:
            # чтобы бот не падал из-за одной ошибки
            pass

        await asyncio.sleep(60)


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_add, Command("add"))
    dp.message.register(cmd_tasks, Command("tasks"))
    dp.message.register(cmd_done, Command("done"))
    dp.message.register(cmd_stats, Command("stats"))
    dp.message.register(cmd_motivation, Command("motivation"))

    dp.message.register(cmd_add, F.text == "➕ Добавить задачу")
    dp.message.register(cmd_tasks, F.text == "📋 Мои задачи")
    dp.message.register(cmd_done, F.text == "✅ Выполнить задачу")
    dp.message.register(cmd_stats, F.text == "📊 Статистика")
    dp.message.register(cmd_motivation, F.text == "🔥 Мотивация")
    dp.message.register(cmd_help, F.text == "ℹ️ Помощь")

    dp.message.register(on_task_text, TaskFlow.waiting_task_text)
    dp.message.register(on_task_due, TaskFlow.waiting_task_due)
    dp.message.register(on_done_number, TaskFlow.waiting_done_number)

    dp.message.register(unknown)
    return dp


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN пустой. Добавь токен в config.py.")

    bot = Bot(token=BOT_TOKEN)
    dp = build_dispatcher()

    # запускаем фоновую проверку напоминаний
    asyncio.create_task(reminder_loop(bot))

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
