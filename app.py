import os
import sqlite3
from functools import wraps
from urllib.parse import urlparse, urljoin
from uuid import uuid4

from flask import Flask, g, render_template, request, redirect, url_for, flash, abort, send_from_directory
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from FDataBase import FDataBase
from User_login import UserLogin

# -------------------- Конфигурация --------------------
DATABASE = '/tmp/database.db'
DEBUG = True
SECRET_KEY = 'municipal-navigator-secret-key'
UPLOAD_FOLDER = os.path.join('static', 'uploads')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg'}
COURSES = ['1', '2', '3', '4', '5']
VACANCY_IMAGES = ['law.svg', 'communication.svg', 'projects.svg', 'economy.svg', 'youth.svg', 'archive.svg', 'digital.svg', 'hr.svg', 'procurement.svg', 'territory.svg', 'media.svg', 'service.svg']
RESPONSE_STATUSES = ['Отправлен', 'На рассмотрении', 'Приглашен', 'Отклонен']

app = Flask(__name__)
app.config.from_object(__name__)
app.config.update(
    DATABASE=os.path.join(app.root_path, 'database.db'),
    UPLOAD_FOLDER=os.path.join(app.root_path, 'static', 'uploads')
)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Сначала войдите в аккаунт.'
login_manager.login_message_category = 'warning'

dbase = None


# -------------------- Работа с БД --------------------
def connect_db():
    """Создает новое соединение с БД SQLite."""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def create_db():
    """Создает БД с набором таблиц и стартовыми данными."""
    db = connect_db()
    with app.open_resource('schema.sql', mode='r', encoding='utf-8') as file:
        db.executescript(file.read())
    db.commit()
    db.close()


def get_db():
    """Возвращает активное соединение, а если его нет — создает и сохраняет в g."""
    if not hasattr(g, 'link_db'):
        g.link_db = connect_db()
    return g.link_db


@app.teardown_appcontext
def close_db(error):
    """Закрывает соединение с БД после завершения запроса, если оно открывалось."""
    if hasattr(g, 'link_db'):
        g.link_db.close()


@app.before_request
def before_request():
    global dbase
    dbase = FDataBase(get_db())
    g.dbase = dbase


@app.context_processor
def inject_common_data():
    menu = []
    try:
        if hasattr(g, 'dbase'):
            role = current_user.get_role() if current_user.is_authenticated else 'guest'
            menu = g.dbase.get_menu(role)
    except Exception:
        menu = []
    return dict(menu=menu, courses=COURSES, vacancy_images=VACANCY_IMAGES)


# -------------------- Flask-Login --------------------
@login_manager.user_loader
def load_user(user_id):
    """Создает UserLogin при запросах авторизованного пользователя."""
    global dbase
    if dbase is None:
        dbase = FDataBase(get_db())
    return UserLogin().fromDB(user_id, dbase)


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if current_user.get_role() != 'admin':
            abort(403)
        return view(*args, **kwargs)
    return wrapped_view


def student_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if current_user.get_role() != 'student':
            abort(403)
        return view(*args, **kwargs)
    return wrapped_view


# -------------------- Вспомогательные функции --------------------
def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file):
    if not file or file.filename == '':
        return None
    if not allowed_file(file.filename):
        flash('Можно загрузить только PDF, DOC, DOCX, PNG, JPG или JPEG.', 'danger')
        return None
    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[1].lower()
    unique_name = f'{uuid4().hex}.{ext}'
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))
    return unique_name


def remove_uploaded_file(filename):
    # Удаляет файл из папки загрузок, если он действительно находится внутри нее.
    if not filename:
        return
    upload_dir = os.path.abspath(app.config['UPLOAD_FOLDER'])
    file_path = os.path.abspath(os.path.join(upload_dir, filename))
    if file_path.startswith(upload_dir) and os.path.exists(file_path):
        os.remove(file_path)


def get_application_from_form():
    return {
        'full_name': request.form.get('full_name', '').strip(),
        'email': request.form.get('email', '').strip().lower(),
        'phone': request.form.get('phone', '').strip(),
        'university': request.form.get('university', '').strip(),
        'direction': request.form.get('direction', '').strip(),
        'course': request.form.get('course', '').strip(),
        'cover_letter': request.form.get('cover_letter', '').strip(),
    }


def make_initial_application(student, vacancy, portfolio=None):
    return {
        'full_name': student['full_name'] or '',
        'email': student['email'] or '',
        'phone': student['phone'] or '',
        'university': student['university'] or '',
        'direction': student['direction'] or '',
        'course': student['course'] or '',
        'cover_letter': (
            f'Здравствуйте! Прошу рассмотреть мою кандидатуру на вакансию «{vacancy["title"]}». '
            f'Готов(а) пройти собеседование и подробнее рассказать о своем опыте.'
        ),
    }


# -------------------- Основные страницы --------------------
@app.route('/')
def index():
    vacancies = g.dbase.get_vacancies(limit=6)
    return render_template('index.html', title='Муниципальный карьерный навигатор', vacancies=vacancies)


@app.route('/about')
def about():
    return render_template('about.html', title='О проекте')


@app.route('/vacancies')
def vacancies():
    search = request.args.get('q', '').strip()
    city = request.args.get('city', '').strip()
    vacancies_list = g.dbase.get_vacancies(search=search, city=city)
    cities = g.dbase.get_cities()
    return render_template('vacancies.html', title='Вакансии', vacancies=vacancies_list, cities=cities, search=search, city=city)


@app.route('/vacancy/<int:vacancy_id>')
def vacancy_page(vacancy_id):
    vacancy = g.dbase.get_vacancy(vacancy_id)
    if not vacancy:
        abort(404)
    already_applied = False
    if current_user.is_authenticated and current_user.get_role() == 'student':
        student = g.dbase.get_student_by_user_id(current_user.get_id())
        already_applied = bool(student and g.dbase.response_exists(student['id'], vacancy_id))
    return render_template('vacancy.html', title=vacancy['title'], vacancy=vacancy, already_applied=already_applied, back=request.args.get('back', ''))


# -------------------- Регистрация и вход --------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        university = request.form.get('university', '').strip()
        direction = request.form.get('direction', '').strip()
        course = request.form.get('course', '').strip()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')

        errors = []
        if not full_name:
            errors.append('Укажите ФИО.')
        if not email or '@' not in email:
            errors.append('Укажите корректный email.')
        if course and course not in COURSES:
            errors.append('Выберите курс от 1 до 5.')
        if len(password) < 6:
            errors.append('Пароль должен быть не короче 6 символов.')
        if password != password2:
            errors.append('Пароли не совпадают.')
        if g.dbase.get_user_by_email(email):
            errors.append('Пользователь с таким email уже зарегистрирован.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html', title='Регистрация', form=request.form)

        user_id = g.dbase.add_user(
            name=full_name,
            email=email,
            password_hash=generate_password_hash(password),
            role='student'
        )
        if user_id:
            g.dbase.create_student_profile(
                user_id=user_id,
                full_name=full_name,
                university=university,
                direction=direction,
                course=course,
                email=email,
                phone=phone
            )
            flash('Регистрация выполнена. Теперь войдите в аккаунт.', 'success')
            return redirect(url_for('login'))

        flash('Не удалось зарегистрировать пользователя.', 'danger')

    return render_template('register.html', title='Регистрация', form={})


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        user = g.dbase.get_user_by_email(email)

        if user and check_password_hash(user['password'], password):
            login_user(UserLogin().create(user), remember=remember)
            flash('Вы вошли в систему.', 'success')
            next_page = request.args.get('next')
            if next_page and is_safe_url(next_page):
                return redirect(next_page)
            return redirect(url_for('profile'))

        flash('Неверный email или пароль.', 'danger')

    return render_template('login.html', title='Авторизация')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из аккаунта.', 'success')
    return redirect(url_for('index'))


# -------------------- Личный кабинет --------------------
@app.route('/profile')
@login_required
def profile():
    if current_user.get_role() == 'admin':
        return redirect(url_for('admin_panel'))

    student = g.dbase.get_student_by_user_id(current_user.get_id())
    portfolio = g.dbase.get_portfolio(student['id']) if student else None
    documents = g.dbase.get_portfolio_documents(student['id']) if student else []
    responses = g.dbase.get_student_responses(student['id']) if student else []
    return render_template(
        'profile.html',
        title='Личный кабинет студента',
        student=student,
        portfolio=portfolio,
        documents=documents,
        responses=responses
    )


@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    organs = g.dbase.get_organs()
    vacancies_list = g.dbase.get_vacancies(include_inactive=True)
    response_status = request.args.get('status', '').strip()
    response_query = request.args.get('q', '').strip()
    responses = g.dbase.get_all_responses(search=response_query, status=response_status)
    stats = g.dbase.get_stats()
    student_ids = list({response['student_id'] for response in responses})
    all_docs = g.dbase.get_documents_for_students(student_ids)
    docs_by_student = {}
    for doc in all_docs:
        docs_by_student.setdefault(doc['student_id'], []).append(doc)
    return render_template(
        'admin.html',
        title='Админ-панель',
        organs=organs,
        vacancies=vacancies_list,
        responses=responses,
        stats=stats,
        docs_by_student=docs_by_student,
        response_status=response_status,
        response_query=response_query,
        response_statuses=RESPONSE_STATUSES
    )


@app.route('/profile/student/update', methods=['POST'])
@login_required
@student_required
def update_student():
    student = g.dbase.get_student_by_user_id(current_user.get_id())
    if not student:
        abort(404)
    course = request.form.get('course', '').strip()
    if course and course not in COURSES:
        flash('Выберите курс от 1 до 5.', 'danger')
        return redirect(url_for('profile'))
    g.dbase.update_student_profile(
        student_id=student['id'],
        full_name=request.form.get('full_name', '').strip(),
        university=request.form.get('university', '').strip(),
        direction=request.form.get('direction', '').strip(),
        course=course,
        email=request.form.get('email', '').strip().lower(),
        phone=request.form.get('phone', '').strip()
    )
    flash('Данные студента обновлены.', 'success')
    return redirect(url_for('profile'))


@app.route('/profile/portfolio/save', methods=['POST'])
@login_required
@student_required
def save_portfolio():
    student = g.dbase.get_student_by_user_id(current_user.get_id())
    if not student:
        abort(404)

    g.dbase.save_portfolio(
        student_id=student['id'],
        description=request.form.get('description', '').strip(),
        skills=request.form.get('skills', '').strip(),
        achievements=request.form.get('achievements', '').strip(),
        resume_link=request.form.get('resume_link', '').strip()
    )

    uploaded_count = 0
    for file in request.files.getlist('documents'):
        original_name = file.filename
        saved_name = save_upload(file)
        if saved_name:
            g.dbase.add_portfolio_document(student['id'], saved_name, original_name)
            uploaded_count += 1

    if uploaded_count:
        flash(f'Портфолио сохранено. Загружено файлов: {uploaded_count}.', 'success')
    else:
        flash('Портфолио сохранено.', 'success')
    return redirect(url_for('profile'))


@app.route('/profile/document/<int:document_id>/delete', methods=['POST'])
@login_required
@student_required
def delete_document(document_id):
    student = g.dbase.get_student_by_user_id(current_user.get_id())
    if not student:
        abort(404)

    document = g.dbase.get_portfolio_document(document_id, student['id'])
    if document and g.dbase.delete_portfolio_document(document_id, student['id']):
        remove_uploaded_file(document['filename'])
        flash('Документ удален из портфолио.', 'success')
    else:
        flash('Документ не найден.', 'warning')
    return redirect(url_for('profile'))


@app.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    if current_user.get_role() == 'admin':
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=False)

    student = g.dbase.get_student_by_user_id(current_user.get_id())
    if not student or not g.dbase.user_has_document(student['id'], filename):
        abort(403)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=False)


@app.route('/apply/<int:vacancy_id>', methods=['GET', 'POST'])
@login_required
@student_required
def apply(vacancy_id):
    vacancy = g.dbase.get_vacancy(vacancy_id)
    if not vacancy:
        abort(404)
    student = g.dbase.get_student_by_user_id(current_user.get_id())
    if not student:
        flash('Сначала заполните данные студента в личном кабинете.', 'warning')
        return redirect(url_for('profile'))
    if g.dbase.response_exists(student['id'], vacancy_id):
        flash('Вы уже откликались на эту вакансию.', 'warning')
        return redirect(url_for('vacancy_page', vacancy_id=vacancy_id))

    portfolio = g.dbase.get_portfolio(student['id'])
    documents = g.dbase.get_portfolio_documents(student['id'])

    if request.method == 'POST':
        action = request.form.get('action')
        application = get_application_from_form()
        errors = []
        if not application['full_name']:
            errors.append('Укажите ФИО в анкете.')
        if not application['email'] or '@' not in application['email']:
            errors.append('Укажите корректный email в анкете.')
        if application['course'] and application['course'] not in COURSES:
            errors.append('Выберите курс от 1 до 5.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('apply.html', title='Анкета отклика', vacancy=vacancy, student=student,
                                   portfolio=portfolio, documents=documents, application=application, mode='form')

        if action == 'preview':
            return render_template('apply.html', title='Проверка анкеты', vacancy=vacancy, student=student,
                                   portfolio=portfolio, documents=documents, application=application, mode='preview')

        if action == 'edit':
            return render_template('apply.html', title='Анкета отклика', vacancy=vacancy, student=student,
                                   portfolio=portfolio, documents=documents, application=application, mode='form')

        if action == 'send':
            g.dbase.add_response(student['id'], vacancy_id, application)
            flash('Анкета отправлена работодателю.', 'success')
            return redirect(url_for('profile'))

    application = make_initial_application(student, vacancy, portfolio)
    return render_template('apply.html', title='Анкета отклика', vacancy=vacancy, student=student,
                           portfolio=portfolio, documents=documents, application=application, mode='form')


# -------------------- Администрирование --------------------
@app.route('/admin/organ/add', methods=['POST'])
@login_required
@admin_required
def add_organ():
    name = request.form.get('name', '').strip()
    city = request.form.get('city', '').strip()
    address = request.form.get('address', '').strip()
    contact = request.form.get('contact', '').strip()
    if not name or not city:
        flash('Укажите название органа и город.', 'danger')
        return redirect(url_for('admin_panel'))
    g.dbase.add_organ(name, city, address, contact)
    flash('Муниципальный орган добавлен.', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/vacancy/add', methods=['POST'])
@login_required
@admin_required
def add_vacancy():
    organ_id = request.form.get('organ_id', type=int)
    title = request.form.get('title', '').strip()
    requirements = request.form.get('requirements', '').strip()
    conditions = request.form.get('conditions', '').strip()
    image = request.form.get('image', 'city.svg')
    if image not in VACANCY_IMAGES:
        image = 'city.svg'
    if not organ_id or not title:
        flash('Выберите орган и укажите название вакансии.', 'danger')
        return redirect(url_for('admin_panel'))
    g.dbase.add_vacancy(organ_id, title, requirements, conditions, image)
    flash('Вакансия добавлена.', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/vacancy/<int:vacancy_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_vacancy(vacancy_id):
    if g.dbase.toggle_vacancy(vacancy_id):
        flash('Статус вакансии изменен.', 'success')
    else:
        flash('Вакансия не найдена.', 'warning')
    return redirect(url_for('admin_panel'))


@app.route('/admin/vacancy/<int:vacancy_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_vacancy(vacancy_id):
    vacancy = g.dbase.get_vacancy(vacancy_id)
    if not vacancy:
        flash('Вакансия не найдена.', 'warning')
        return redirect(url_for('admin_panel'))

    if g.dbase.delete_vacancy(vacancy_id):
        flash(f'Вакансия «{vacancy["title"]}» удалена.', 'success')
    else:
        flash('Не удалось удалить вакансию.', 'danger')
    return redirect(url_for('admin_panel'))


@app.route('/admin/response/<int:response_id>/status', methods=['POST'])
@login_required
@admin_required
def update_response_status(response_id):
    status = request.form.get('status', 'Отправлен')
    if status not in RESPONSE_STATUSES:
        status = 'Отправлен'
    g.dbase.update_response_status(response_id, status)
    flash('Статус отклика обновлен.', 'success')
    return redirect(url_for('admin_panel'))


# -------------------- Ошибки --------------------
@app.errorhandler(403)
def forbidden(error):
    return render_template('403.html', title='Доступ запрещен'), 403


@app.errorhandler(404)
def not_found(error):
    return render_template('404.html', title='Страница не найдена'), 404


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
