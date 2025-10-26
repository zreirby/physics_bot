# states/admin_states.py
from aiogram.fsm.state import State, StatesGroup

class Registration(StatesGroup):
    waiting_for_name = State()

class SolveTasks(StatesGroup):
    waiting_for_text_answer = State()

class AddTask(StatesGroup):
    waiting_for_type = State()
    waiting_for_section = State()
    waiting_for_photo = State()
    waiting_for_correct_choice = State()      # Для multiple_choice
    waiting_for_incorrect_choice_1 = State()  # Для multiple_choice
    waiting_for_incorrect_choice_2 = State()  # Для multiple_choice
    waiting_for_incorrect_choice_3 = State()  # Для multiple_choice
    waiting_for_text_answer = State()         # Для text_input
    waiting_for_hint = State()
    waiting_for_solution = State()
    confirming = State()

class Broadcast(StatesGroup):
    waiting_for_message = State()
    confirming = State()