# keyboards/user_keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

main_menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🚀 Решать задачи", callback_data="solve_tasks")],
    [InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats")],
    [InlineKeyboardButton(text="💬 Связаться с репетитором", callback_data="contact_tutor")]
])

def get_sections_keyboard(sections):
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"section_{section_id}")]
        for section_id, name in sections
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_task_keyboard(task_type, task_id, choices=None):
    buttons = []
    if task_type == 'multiple_choice':
        # Создаем кнопки с вариантами ответов
        buttons.extend([
            InlineKeyboardButton(text=text, callback_data=f"choice_{task_id}_{choice_id}_{is_correct}")
            for choice_id, text, is_correct in choices
        ])
        # Группируем по 2 кнопки в ряд для красоты
        buttons = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]

    # Добавляем универсальные кнопки
    action_buttons = [
        InlineKeyboardButton(text="💡 Подсказка", callback_data=f"hint_{task_id}"),
        InlineKeyboardButton(text="🔍 Посмотреть решение", callback_data=f"solution_{task_id}")
    ]
    buttons.append(action_buttons)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Клавиатура после правильного ответа
next_task_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="➡️ Следующая задача", callback_data="next_tasks"),
        InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")
    ]
])

back_to_menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")]
])