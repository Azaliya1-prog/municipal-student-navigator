class FDataBase:
    """Класс для работы приложения с базой данных."""

    def __init__(self, db):
        self.__db = db
        self.__cur = db.cursor()

    # ---------- Меню ----------
    def get_menu(self, role='guest'):
        return self.__cur.execute('''
            SELECT "название" AS title, "ссылка" AS url, "роль" AS role
            FROM "Главное_меню"
            WHERE "роль" = 'all' OR "роль" = ?
            ORDER BY "порядок"
        ''', (role,)).fetchall()

    # ---------- Пользователи ----------
    def add_user(self, name, email, password_hash, role='student'):
        try:
            self.__cur.execute('''
                INSERT INTO "Пользователи" ("имя", "email", "пароль", "роль")
                VALUES (?, ?, ?, ?)
            ''', (name, email, password_hash, role))
            self.__db.commit()
            return self.__cur.lastrowid
        except Exception:
            self.__db.rollback()
            return None

    def get_user(self, user_id):
        return self.__cur.execute('''
            SELECT "id" AS id, "имя" AS name, "email" AS email,
                   "пароль" AS password, "роль" AS role,
                   "дата_регистрации" AS created_at
            FROM "Пользователи"
            WHERE "id" = ?
            LIMIT 1
        ''', (user_id,)).fetchone()

    def get_user_by_email(self, email):
        return self.__cur.execute('''
            SELECT "id" AS id, "имя" AS name, "email" AS email,
                   "пароль" AS password, "роль" AS role,
                   "дата_регистрации" AS created_at
            FROM "Пользователи"
            WHERE "email" = ?
            LIMIT 1
        ''', (email,)).fetchone()

    # ---------- Студенты ----------
    def create_student_profile(self, user_id, full_name, university, direction, course, email, phone):
        try:
            self.__cur.execute('''
                INSERT INTO "Студенты" (
                    "id_пользователя", "ФИО", "ВУЗ", "направление", "курс", "email", "телефон"
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, full_name, university, direction, course, email, phone))
            self.__db.commit()
            return True
        except Exception:
            self.__db.rollback()
            return False

    def get_student_by_user_id(self, user_id):
        return self.__cur.execute('''
            SELECT "id" AS id, "id_пользователя" AS user_id, "ФИО" AS full_name,
                   "ВУЗ" AS university, "направление" AS direction, "курс" AS course,
                   "email" AS email, "телефон" AS phone
            FROM "Студенты"
            WHERE "id_пользователя" = ?
            LIMIT 1
        ''', (user_id,)).fetchone()

    def update_student_profile(self, student_id, full_name, university, direction, course, email, phone):
        self.__cur.execute('''
            UPDATE "Студенты"
            SET "ФИО" = ?, "ВУЗ" = ?, "направление" = ?, "курс" = ?, "email" = ?, "телефон" = ?
            WHERE "id" = ?
        ''', (full_name, university, direction, course, email, phone, student_id))
        self.__db.commit()

    # ---------- Портфолио ----------
    def get_portfolio(self, student_id):
        return self.__cur.execute('''
            SELECT "id" AS id, "id_студента" AS student_id, "описание" AS description,
                   "навыки" AS skills, "достижения" AS achievements,
                   "ссылка_на_резюме" AS resume_link,
                   "дата_обновления" AS updated_at
            FROM "Портфолио"
            WHERE "id_студента" = ?
            LIMIT 1
        ''', (student_id,)).fetchone()

    def save_portfolio(self, student_id, description, skills, achievements, resume_link):
        portfolio = self.get_portfolio(student_id)
        if portfolio:
            self.__cur.execute('''
                UPDATE "Портфолио"
                SET "описание" = ?, "навыки" = ?, "достижения" = ?, "ссылка_на_резюме" = ?,
                    "дата_обновления" = CURRENT_TIMESTAMP
                WHERE "id_студента" = ?
            ''', (description, skills, achievements, resume_link, student_id))
        else:
            self.__cur.execute('''
                INSERT INTO "Портфолио" (
                    "id_студента", "описание", "навыки", "достижения", "ссылка_на_резюме"
                ) VALUES (?, ?, ?, ?, ?)
            ''', (student_id, description, skills, achievements, resume_link))
        self.__db.commit()

    def add_portfolio_document(self, student_id, filename, original_name):
        self.__cur.execute('''
            INSERT INTO "Документы_портфолио" ("id_студента", "имя_файла", "исходное_имя")
            VALUES (?, ?, ?)
        ''', (student_id, filename, original_name))
        self.__db.commit()

    def get_portfolio_documents(self, student_id):
        return self.__cur.execute('''
            SELECT "id" AS id, "id_студента" AS student_id,
                   "имя_файла" AS filename, "исходное_имя" AS original_name,
                   "дата_загрузки" AS uploaded_at
            FROM "Документы_портфолио"
            WHERE "id_студента" = ?
            ORDER BY "дата_загрузки" DESC, "id" DESC
        ''', (student_id,)).fetchall()

    def get_portfolio_document(self, document_id, student_id):
        return self.__cur.execute('''
            SELECT "id" AS id, "id_студента" AS student_id,
                   "имя_файла" AS filename, "исходное_имя" AS original_name
            FROM "Документы_портфолио"
            WHERE "id" = ? AND "id_студента" = ?
            LIMIT 1
        ''', (document_id, student_id)).fetchone()

    def user_has_document(self, student_id, filename):
        return self.__cur.execute('''
            SELECT "id"
            FROM "Документы_портфолио"
            WHERE "id_студента" = ? AND "имя_файла" = ?
            LIMIT 1
        ''', (student_id, filename)).fetchone() is not None

    def get_documents_for_students(self, student_ids):
        if not student_ids:
            return []
        placeholders = ','.join(['?'] * len(student_ids))
        return self.__cur.execute(f'''
            SELECT "id" AS id, "id_студента" AS student_id,
                   "имя_файла" AS filename, "исходное_имя" AS original_name,
                   "дата_загрузки" AS uploaded_at
            FROM "Документы_портфолио"
            WHERE "id_студента" IN ({placeholders})
            ORDER BY "дата_загрузки" DESC, "id" DESC
        ''', student_ids).fetchall()

    def delete_portfolio_document(self, document_id, student_id):
        self.__cur.execute('''
            DELETE FROM "Документы_портфолио"
            WHERE "id" = ? AND "id_студента" = ?
        ''', (document_id, student_id))
        self.__db.commit()
        return self.__cur.rowcount > 0

    # ---------- Муниципальные органы ----------
    def get_organs(self):
        return self.__cur.execute('''
            SELECT "id" AS id, "название" AS name, "город" AS city,
                   "адрес" AS address, "контактное_лицо" AS contact
            FROM "Муниципальные_органы"
            ORDER BY "город", "название"
        ''').fetchall()

    def add_organ(self, name, city, address, contact):
        self.__cur.execute('''
            INSERT INTO "Муниципальные_органы" ("название", "город", "адрес", "контактное_лицо")
            VALUES (?, ?, ?, ?)
        ''', (name, city, address, contact))
        self.__db.commit()

    def get_cities(self):
        return self.__cur.execute('''
            SELECT DISTINCT "город" AS city
            FROM "Муниципальные_органы"
            ORDER BY "город"
        ''').fetchall()

    # ---------- Вакансии ----------
    def get_vacancies(self, search='', city='', limit=None, include_inactive=False):
        query = '''
            SELECT v."id" AS id, v."название" AS title, v."требования" AS requirements,
                   v."условия" AS conditions, v."изображение" AS image,
                   v."дата_публикации" AS date_publication,
                   v."активна" AS active, o."название" AS organ_name,
                   o."город" AS city, o."адрес" AS address, o."контактное_лицо" AS contact,
                   COUNT(r."id") AS responses_count
            FROM "Вакансии" v
            JOIN "Муниципальные_органы" o ON v."id_органа" = o."id"
            LEFT JOIN "Отклики" r ON r."id_вакансии" = v."id"
            WHERE 1 = 1
        '''
        params = []
        if not include_inactive:
            query += ' AND v."активна" = 1'
        if search:
            query += ' AND (LOWER(v."название") LIKE ? OR LOWER(v."требования") LIKE ? OR LOWER(o."название") LIKE ?)'
            pattern = f'%{search.lower()}%'
            params.extend([pattern, pattern, pattern])
        if city:
            query += ' AND o."город" = ?'
            params.append(city)
        query += ' GROUP BY v."id" ORDER BY v."дата_публикации" DESC, v."id" DESC'
        if limit:
            query += ' LIMIT ?'
            params.append(limit)
        return self.__cur.execute(query, params).fetchall()

    def get_vacancy(self, vacancy_id):
        return self.__cur.execute('''
            SELECT v."id" AS id, v."id_органа" AS organ_id, v."название" AS title,
                   v."требования" AS requirements, v."условия" AS conditions,
                   v."изображение" AS image,
                   v."дата_публикации" AS date_publication, v."активна" AS active,
                   o."название" AS organ_name, o."город" AS city, o."адрес" AS address,
                   o."контактное_лицо" AS contact
            FROM "Вакансии" v
            JOIN "Муниципальные_органы" o ON v."id_органа" = o."id"
            WHERE v."id" = ?
            LIMIT 1
        ''', (vacancy_id,)).fetchone()

    def add_vacancy(self, organ_id, title, requirements, conditions, image='city.svg'):
        self.__cur.execute('''
            INSERT INTO "Вакансии" ("id_органа", "название", "требования", "условия", "изображение")
            VALUES (?, ?, ?, ?, ?)
        ''', (organ_id, title, requirements, conditions, image))
        self.__db.commit()

    def toggle_vacancy(self, vacancy_id):
        self.__cur.execute('''
            UPDATE "Вакансии"
            SET "активна" = CASE WHEN "активна" = 1 THEN 0 ELSE 1 END
            WHERE "id" = ?
        ''', (vacancy_id,))
        self.__db.commit()
        return self.__cur.rowcount > 0

    def delete_vacancy(self, vacancy_id):
        self.__cur.execute('''
            DELETE FROM "Вакансии"
            WHERE "id" = ?
        ''', (vacancy_id,))
        self.__db.commit()
        return self.__cur.rowcount > 0

    # ---------- Отклики ----------
    def add_response(self, student_id, vacancy_id, application):
        self.__cur.execute('''
            INSERT INTO "Отклики" (
                "id_студента", "id_вакансии", "ФИО_анкеты", "email_анкеты", "телефон_анкеты",
                "ВУЗ_анкеты", "направление_анкеты", "курс_анкеты", "сопроводительное_письмо", "статус"
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Отправлен')
        ''', (
            student_id, vacancy_id, application.get('full_name', ''), application.get('email', ''),
            application.get('phone', ''), application.get('university', ''), application.get('direction', ''),
            application.get('course', ''), application.get('cover_letter', '')
        ))
        self.__db.commit()

    def response_exists(self, student_id, vacancy_id):
        return self.__cur.execute('''
            SELECT "id" FROM "Отклики"
            WHERE "id_студента" = ? AND "id_вакансии" = ?
            LIMIT 1
        ''', (student_id, vacancy_id)).fetchone()

    def get_student_responses(self, student_id):
        return self.__cur.execute('''
            SELECT r."id" AS id, r."дата_отклика" AS response_date, r."статус" AS status,
                   r."сопроводительное_письмо" AS cover_letter,
                   v."id" AS vacancy_id, v."название" AS vacancy_title,
                   o."название" AS organ_name, o."город" AS city
            FROM "Отклики" r
            JOIN "Вакансии" v ON r."id_вакансии" = v."id"
            JOIN "Муниципальные_органы" o ON v."id_органа" = o."id"
            WHERE r."id_студента" = ?
            ORDER BY r."дата_отклика" DESC
        ''', (student_id,)).fetchall()

    def get_all_responses(self, search='', status=''):
        query = '''
            SELECT r."id" AS id, r."id_студента" AS student_id,
                   r."дата_отклика" AS response_date, r."статус" AS status,
                   r."ФИО_анкеты" AS application_name, r."email_анкеты" AS application_email,
                   r."телефон_анкеты" AS application_phone, r."ВУЗ_анкеты" AS application_university,
                   r."направление_анкеты" AS application_direction, r."курс_анкеты" AS application_course,
                   r."сопроводительное_письмо" AS cover_letter,
                   s."ФИО" AS student_name, s."email" AS student_email, s."телефон" AS phone,
                   v."название" AS vacancy_title, v."id" AS vacancy_id, o."название" AS organ_name
            FROM "Отклики" r
            JOIN "Студенты" s ON r."id_студента" = s."id"
            JOIN "Вакансии" v ON r."id_вакансии" = v."id"
            JOIN "Муниципальные_органы" o ON v."id_органа" = o."id"
            WHERE 1 = 1
        '''
        params = []
        if status:
            query += ' AND r."статус" = ?'
            params.append(status)
        if search:
            query += ''' AND (
                LOWER(r."ФИО_анкеты") LIKE ? OR LOWER(r."email_анкеты") LIKE ?
                OR LOWER(v."название") LIKE ? OR LOWER(o."название") LIKE ?
            )'''
            pattern = f'%{search.lower()}%'
            params.extend([pattern, pattern, pattern, pattern])
        query += ' ORDER BY r."дата_отклика" DESC, r."id" DESC'
        return self.__cur.execute(query, params).fetchall()

    def update_response_status(self, response_id, status):
        self.__cur.execute('''
            UPDATE "Отклики"
            SET "статус" = ?
            WHERE "id" = ?
        ''', (status, response_id))
        self.__db.commit()

    # ---------- Статистика ----------
    def get_stats(self):
        return {
            'vacancies': self.__cur.execute('SELECT COUNT(*) FROM "Вакансии" WHERE "активна" = 1').fetchone()[0],
            'organs': self.__cur.execute('SELECT COUNT(*) FROM "Муниципальные_органы"').fetchone()[0],
            'students': self.__cur.execute('SELECT COUNT(*) FROM "Студенты"').fetchone()[0],
            'responses': self.__cur.execute('SELECT COUNT(*) FROM "Отклики"').fetchone()[0],
            'new_responses': self.__cur.execute('SELECT COUNT(*) FROM "Отклики" WHERE "статус" = ?', ('Отправлен',)).fetchone()[0],
            'review_responses': self.__cur.execute('SELECT COUNT(*) FROM "Отклики" WHERE "статус" = ?', ('На рассмотрении',)).fetchone()[0],
        }
