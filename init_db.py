from app import app, create_db, connect_db
from werkzeug.security import generate_password_hash

with app.app_context():
    create_db()
    db = connect_db()
    cur = db.cursor()

    cur.execute('''INSERT INTO "Пользователи" ("имя", "email", "пароль", "роль") VALUES (?, ?, ?, ?)''',
                ('Администратор', 'admin@mail.ru', generate_password_hash('admin123'), 'admin'))
    cur.execute('''INSERT INTO "Пользователи" ("имя", "email", "пароль", "роль") VALUES (?, ?, ?, ?)''',
                ('Петров Иван Сергеевич', 'student@mail.ru', generate_password_hash('123456'), 'student'))
    student_user_id = cur.lastrowid
    cur.execute('''INSERT INTO "Студенты" ("id_пользователя", "ФИО", "ВУЗ", "направление", "курс", "email", "телефон")
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (student_user_id, 'Петров Иван Сергеевич', 'ТГУ им. Г. Р. Державина',
                 'Государственное и муниципальное управление', '3', 'student@mail.ru', '+7 900 123-45-67'))
    student_id = cur.lastrowid
    cur.execute('''INSERT INTO "Портфолио" ("id_студента", "описание", "навыки", "достижения", "ссылка_на_резюме")
                   VALUES (?, ?, ?, ?, ?)''',
                (student_id, 'Интересуюсь муниципальным управлением, правовой работой и проектной деятельностью.',
                 'Деловая переписка, работа с документами, Excel, подготовка презентаций',
                 'Участие в студенческой конференции и волонтерских проектах',
                 'https://example.com/resume'))
    cur.execute('''INSERT INTO "Отклики" (
                    "id_студента", "id_вакансии", "ФИО_анкеты", "email_анкеты", "телефон_анкеты",
                    "ВУЗ_анкеты", "направление_анкеты", "курс_анкеты", "сопроводительное_письмо", "статус"
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (student_id, 1, 'Петров Иван Сергеевич', 'student@mail.ru', '+7 900 123-45-67',
                 'ТГУ им. Г. Р. Державина', 'Государственное и муниципальное управление', '3',
                 'Прошу рассмотреть мою кандидатуру. Готов пройти собеседование и предоставить дополнительные материалы.',
                 'На рассмотрении'))

    db.commit()
    db.close()

print('База database.db пересоздана.')
