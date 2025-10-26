# darabase/database.py
import aiosqlite

DB_NAME = 'physics_bot.db'

async def create_tables():
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица пользователей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id BIGINT UNIQUE NOT NULL,
                full_name VARCHAR(255),
                role VARCHAR(50) DEFAULT 'student',
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Таблица разделов физики
        await db.execute('''
            CREATE TABLE IF NOT EXISTS sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) UNIQUE NOT NULL
            )
        ''')
        # Таблица задач
        await db.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER,
                task_type VARCHAR(50) NOT NULL,
                photo_file_id VARCHAR(255),
                hint_text TEXT,
                solution_data TEXT,
                solution_type VARCHAR(50),
                FOREIGN KEY (section_id) REFERENCES sections(id)
            )
        ''')
        # Варианты ответов для multiple_choice
        await db.execute('''
            CREATE TABLE IF NOT EXISTS task_choices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                choice_text VARCHAR(255) NOT NULL,
                is_correct BOOLEAN NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        ''')
        # Правильные ответы для text_input
        await db.execute('''
            CREATE TABLE IF NOT EXISTS task_text_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                correct_answer REAL NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        ''')
        # Лог ответов пользователей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                task_id INTEGER,
                answer_given TEXT,
                is_correct BOOLEAN,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action_type VARCHAR(50),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        ''')
        await db.commit()

# --- Функции для работы с пользователями ---
async def add_user(telegram_id, full_name):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT telegram_id FROM users WHERE telegram_id = ?", (telegram_id,))
        if await cursor.fetchone() is None:
            await db.execute("INSERT INTO users (telegram_id, full_name) VALUES (?, ?)", (telegram_id, full_name))
            await db.commit()

async def get_user(telegram_id):
     async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        return await cursor.fetchone()

# --- Функции для работы с разделами и задачами ---
async def get_sections():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT id, name FROM sections")
        return await cursor.fetchall()

async def get_random_task_by_section(section_id):
    async with aiosqlite.connect(DB_NAME) as db:
        # Выбираем случайную задачу из указанного раздела
        cursor = await db.execute(
            "SELECT id, task_type, photo_file_id FROM tasks WHERE section_id = ? ORDER BY RANDOM() LIMIT 1",
            (section_id,)
        )
        return await cursor.fetchone()

async def get_task_choices(task_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT id, choice_text, is_correct FROM task_choices WHERE task_id = ?",
            (task_id,)
        )
        return await cursor.fetchall()

async def get_task_text_answer(task_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT correct_answer FROM task_text_answers WHERE task_id = ?",
            (task_id,)
        )
        return await cursor.fetchone()

async def log_user_action(user_id, task_id, action_type, answer_given=None, is_correct=None):
    async with aiosqlite.connect(DB_NAME) as db:
        user_db_id_cursor = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (user_id,))
        user_db_id = await user_db_id_cursor.fetchone()
        if user_db_id:
            await db.execute(
                "INSERT INTO user_answers (user_id, task_id, answer_given, is_correct, action_type) VALUES (?, ?, ?, ?, ?)",
                (user_db_id[0], task_id, answer_given, is_correct, action_type)
            )
            await db.commit()

async def get_task_hint(task_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT hint_text FROM tasks WHERE id = ?", (task_id,))
        return await cursor.fetchone()

async def get_task_solution(task_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT solution_data, solution_type FROM tasks WHERE id = ?", (task_id,))
        return await cursor.fetchone()

async def get_user_statistics(telegram_id):
    async with aiosqlite.connect(DB_NAME) as db:
        # Находим внутренний ID пользователя
        cursor = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        user_id_tuple = await cursor.fetchone()
        if not user_id_tuple:
            return None
        user_id = user_id_tuple[0]

        # Общая статистика
        cursor = await db.execute(
            "SELECT COUNT(*), SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) FROM user_answers WHERE user_id = ? AND action_type = 'answered'",
            (user_id,)
        )
        total_answers, correct_answers = await cursor.fetchone()
        total_answers = total_answers or 0
        correct_answers = correct_answers or 0

        # Статистика по разделам
        cursor = await db.execute('''
            SELECT s.name, COUNT(ua.id), SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END)
            FROM user_answers ua
            JOIN tasks t ON ua.task_id = t.id
            JOIN sections s ON t.section_id = s.id
            WHERE ua.user_id = ? AND ua.action_type = 'answered'
            GROUP BY s.name
        ''', (user_id,))
        sections_stats = await cursor.fetchall()

        return {
            "total": total_answers,
            "correct": correct_answers,
            "sections": sections_stats
        }

# database/database.py

async def add_new_task(task_data):
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            # 1. Вставляем основную информацию о задаче
            cursor = await db.execute(
                "INSERT INTO tasks (section_id, task_type, photo_file_id, hint_text, solution_data, solution_type) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    task_data['section_id'],
                    task_data['type'],
                    task_data['photo'],
                    task_data['hint'],
                    task_data['solution_data'],
                    task_data['solution_type']
                )
            )
            task_id = cursor.lastrowid # Получаем ID только что вставленной задачи

            # 2. Вставляем ответы в зависимости от типа задачи
            if task_data['type'] == 'multiple_choice':
                # Сначала правильный ответ. Используем 1 для True.
                await db.execute(
                    "INSERT INTO task_choices (task_id, choice_text, is_correct) VALUES (?, ?, ?)",
                    (task_id, task_data['correct_choice'], 1)
                )
                # Затем неправильные. Используем 0 для False.
                for choice in task_data['incorrect_choices']:
                    await db.execute(
                        "INSERT INTO task_choices (task_id, choice_text, is_correct) VALUES (?, ?, ?)",
                        (task_id, choice, 0)
                    )
            elif task_data['type'] == 'text_input':
                print(f"--- ПЫТАЮСЬ СОХРАНИТЬ ТЕКСТОВЫЙ ОТВЕТ для task_id {task_id}: {task_data['text_answer']} ---")
                await db.execute(
                    "INSERT INTO task_text_answers (task_id, correct_answer) VALUES (?, ?)",
                    (task_id, task_data['text_answer'])
                )

            # 3. Подтверждаем ВСЮ транзакцию ОДИН раз в конце
            await db.commit()

        except Exception as e:
            print(f"Error adding task to DB: {e}")
            await db.rollback() # Откатываем изменения в случае ошибки

# database/database.py
# ... (в конец файла)

STUDENTS_PER_PAGE = 10

async def get_all_students(page=1):
    async with aiosqlite.connect(DB_NAME) as db:
        offset = (page - 1) * STUDENTS_PER_PAGE
        cursor = await db.execute(
            "SELECT telegram_id, full_name FROM users WHERE role = 'student' ORDER BY registration_date DESC LIMIT ? OFFSET ?",
            (STUDENTS_PER_PAGE, offset)
        )
        return await cursor.fetchall()

async def get_student_last_answers(telegram_id, limit=10):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        user_id = await cursor.fetchone()
        if not user_id:
            return []

        cursor = await db.execute(
            """
            SELECT task_id, answer_given, is_correct, timestamp, action_type
            FROM user_answers
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (user_id[0], limit)
        )
        return await cursor.fetchall()

async def get_all_user_ids():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT telegram_id FROM users WHERE role = 'student'")
        return await cursor.fetchall()