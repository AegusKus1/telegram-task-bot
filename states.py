from aiogram.fsm.state import State, StatesGroup

class TaskFlow(StatesGroup):
    waiting_task_text = State()
    waiting_task_due = State()
    waiting_done_number = State()
