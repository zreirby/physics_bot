# keyboards/admin_keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

admin_main_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="👥 Мои ученики и их статистика", callback_data="view_students")],
    [InlineKeyboardButton(text="➕ Добавить задачу", callback_data="add_task")],
    [InlineKeyboardButton(text="📤 Создать рассылку", callback_data="create_broadcast")]
])

task_type_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="📝 Тест (выбор ответа)", callback_data="type_multiple_choice"),
        InlineKeyboardButton(text="🔢 Ввод числа", callback_data="type_text_input")
    ]
])

# Эта функция будет похожа на пользовательскую
def get_sections_keyboard_admin(sections):
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"admin_section_{section_id}")]
        for section_id, name in sections
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="✅ Подтвердить и сохранить", callback_data="confirm_add_task"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_add_task")
    ]
])

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

STUDENTS_PER_PAGE = 10

def get_students_keyboard(students, page=1):
    buttons = []
    # Кнопки с учениками
    for student in students:
        # student[0] - telegram_id, student[1] - full_name
        buttons.append([
            InlineKeyboardButton(text=student[1], callback_data=f"student_{student[0]}")
        ])

    # Кнопки пагинации
    pagination_buttons = []
    if page > 1:
        pagination_buttons.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"view_students_{page - 1}")
        )
    if len(students) == STUDENTS_PER_PAGE:
        pagination_buttons.append(
            InlineKeyboardButton(text="Вперед ➡️", callback_data=f"view_students_{page + 1}")
        )

    if pagination_buttons:
        buttons.append(pagination_buttons)

    buttons.append([InlineKeyboardButton(text="🏠 В админ-меню", callback_data="admin_main_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


confirm_broadcast_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="✅ Да, отправить", callback_data="confirm_broadcast"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_broadcast")
    ]
])