# Лабораторна робота 5: веб-додаток «Адміністратор готелю»
#
# Python + Bottle (веб-фреймворк) + SQLAlchemy (ORM) над базою PostgreSQL «Готель»
# з лабораторних робіт 1-4: тригери цілісності, збережені процедури та кеш memcached
# працюють у базі, а додаток лише викликає їх і показує результат.
#
# Запуск для розробки:  python lab5.py   (http://localhost:8085)
# Запуск у Docker:      uWSGI за nginx, див. bottle.ini та docker-compose.yml

import json
import os
import urllib.parse
from datetime import date

import bottle
from bottle import redirect, request, response, template

from hotel import services as svc
from hotel import validation as v

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
bottle.TEMPLATE_PATH.insert(0, os.path.join(BASE_DIR, 'views'))

app = application = bottle.Bottle()


# ---------------------------------------------------------------------------
# Допоміжні функції для шаблонів
# ---------------------------------------------------------------------------

def fmt_date(value):
    """Дата у вигляді ДД.ММ.РРРР (порожнє значення - прочерк)."""
    return value.strftime('%d.%m.%Y') if value else '—'


def fmt_money(value):
    """Сума з пробілом між тисячами та двома знаками після коми."""
    return f'{value:,.2f}'.replace(',', ' ') + ' грн'


def full_name(row):
    """Повне імʼя «Прізвище Імʼя По батькові» (порожні частини пропускаються)."""
    return ' '.join(p for p in (row['last_name'], row['first_name'], row['patronymic']) if p)


bottle.BaseTemplate.defaults.update({
    'fmt_date': fmt_date,
    'fmt_money': fmt_money,
    'full_name': full_name,
    'iso': lambda d: d.isoformat() if d else '',
    'urlq': urllib.parse.quote,
    'today': lambda: date.today().isoformat(),
    'WEEKDAYS': svc.WEEKDAYS,
    'WEEKDAYS_SHORT': svc.WEEKDAYS_SHORT,
    'nav_items': [
        ('home', 'Огляд', '/'),
        ('rooms', 'Номери', '/rooms'),
        ('types', 'Типи номерів', '/room-types'),
        ('clients', 'Клієнти', '/clients'),
        ('stays', 'Проживання', '/stays'),
        ('employees', 'Службовці', '/employees'),
        ('queries', 'Запити', '/queries'),
    ],
})


# ---------------------------------------------------------------------------
# Повідомлення користувачеві (flash): зберігаються в cookie до наступної сторінки
# ---------------------------------------------------------------------------

def set_flash(kind, text, warnings=()):
    """Запамʼятовує повідомлення для користувача в cookie до показу наступної сторінки."""
    payload = json.dumps({'kind': kind, 'text': text, 'warnings': list(warnings)},
                         ensure_ascii=False)
    # JSON кодується у відсотки (%XX), щоб кирилиця безпечно пройшла через cookie
    response.set_cookie('flash', urllib.parse.quote(payload), path='/', httponly=True)


def pop_flash():
    """Читає повідомлення з cookie й одразу видаляє його, щоб воно показалося один раз."""
    raw = request.get_cookie('flash')
    if not raw:
        return None
    # повідомлення показується один раз: після читання cookie видаляється
    response.delete_cookie('flash', path='/')
    try:
        return json.loads(urllib.parse.unquote(raw))
    except ValueError:
        return None


def page(name, **context):
    """Показує сторінку-шаблон разом із повідомленням, що чекає користувача.

    here - адреса поточної сторінки: форми дій (наприклад, виселення) повертають
    користувача на неї.
    """
    here = request.path + ('?' + request.query_string if request.query_string else '')
    return template(name, flash=pop_flash(), here=here, **context)


def safe_back(default):
    """Адреса повернення з форми: лише всередині сайту (захист від переходу на чужий сайт)."""
    back = request.forms.get('back') or ''
    return back if back.startswith('/') and not back.startswith('//') else default


def form_data():
    """Значення форми як звичайний словник рядків."""
    data = request.forms.decode()
    return {key: data.get(key, '') for key in data.keys()}


def act(action, *args, back):
    """Дія без форми (видалення, виселення): результат показується повідомленням."""
    try:
        outcome = action(*args)
        set_flash('ok', outcome.message, outcome.warnings)
    except v.ValidationError as exc:
        set_flash('error', ' '.join(exc.errors.values()))
    except svc.UserError as exc:
        set_flash('error', str(exc))
    redirect(back)


def submit(action, *args, success_url, retry):
    """Дія з формою: при успіху - перехід на success_url, при помилці - форма з помилками."""
    try:
        outcome = action(*args)
    except v.ValidationError as exc:
        return retry(exc.errors, '')
    except svc.UserError as exc:
        return retry({}, str(exc))
    set_flash('ok', outcome.message, outcome.warnings)
    redirect(success_url)


def lookup(getter, *args, back):
    """Знаходить запис для форми редагування; якщо його немає - повідомлення й перехід назад."""
    try:
        return getter(*args)
    except svc.UserError as exc:
        set_flash('error', str(exc))
        redirect(back)


# ---------------------------------------------------------------------------
# Службові маршрути
# ---------------------------------------------------------------------------

@app.route('/static/<filename:path>')
def static(filename):
    """Статичні файли (стилі)."""
    return bottle.static_file(filename, root=os.path.join(BASE_DIR, 'static'))


@app.error(404)
def error404(_):
    """Сторінка помилки 404: такої адреси в додатку немає."""
    return template('error', flash=None, title='Сторінку не знайдено',
                    text='Такої сторінки немає.')


@app.error(500)
def error500(_):
    """Сторінка помилки 500: непередбачена помилка (зазвичай недоступна база)."""
    return template('error', flash=None, title='Помилка сервера',
                    text='Сталася непередбачена помилка. Перевірте, чи працює база даних.')


# ---------------------------------------------------------------------------
# Огляд
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    """Головна сторінка: кількість номерів, клієнтів, службовців і список поточних мешканців."""
    return page('index', title='Огляд', active='home', data=svc.get_dashboard())


# ---------------------------------------------------------------------------
# Типи номерів
# ---------------------------------------------------------------------------

@app.route('/room-types')
def room_types():
    """Сторінка «Типи номерів»: таблиця типів із кількістю номерів кожного типу."""
    return page('room_types', title='Типи номерів', active='types',
                types=svc.list_room_types())


def room_type_form(raw, errors, error, action, heading):
    """Показує форму типу номера (створення або зміна) разом із помилками перевірки."""
    return page('room_type_form', title=heading, active='types', raw=raw, errors=errors,
                error=error, action=action)


@app.get('/room-types/new')
def room_type_new():
    """GET /room-types/new: порожня форма нового типу номера."""
    return room_type_form({}, {}, '', '/room-types/new', 'Новий тип номера')


@app.post('/room-types/new')
def room_type_create():
    """POST /room-types/new: перевіряє дані й створює тип номера."""
    raw = form_data()
    return submit(svc.create_room_type, raw, success_url='/room-types',
                  retry=lambda e, m: room_type_form(raw, e, m, '/room-types/new',
                                                    'Новий тип номера'))


@app.get('/room-types/<type_id:int>/edit')
def room_type_edit(type_id):
    """GET /room-types/<id>/edit: форма зміни типу номера із поточними значеннями."""
    raw = lookup(svc.get_room_type, type_id, back='/room-types')
    return room_type_form(raw, {}, '', f'/room-types/{type_id}/edit', 'Зміна типу номера')


@app.post('/room-types/<type_id:int>/edit')
def room_type_update(type_id):
    """POST /room-types/<id>/edit: перевіряє дані й змінює тип номера."""
    raw = form_data()
    return submit(svc.update_room_type, type_id, raw, success_url='/room-types',
                  retry=lambda e, m: room_type_form(raw, e, m, f'/room-types/{type_id}/edit',
                                                    'Зміна типу номера'))


@app.post('/room-types/<type_id:int>/delete')
def room_type_delete(type_id):
    """POST /room-types/<id>/delete: видаляє тип номера (якщо його не використовують номери)."""
    act(svc.delete_room_type, type_id, back='/room-types')


# ---------------------------------------------------------------------------
# Номери
# ---------------------------------------------------------------------------

@app.route('/rooms')
def rooms():
    """Сторінка «Номери»: усі номери зі станом (скільки мешканців, скільки місць вільно)."""
    return page('rooms', title='Номери', active='rooms', rooms=svc.list_rooms())


def room_form(raw, errors, error, action, heading):
    """Показує форму номера (створення або зміна) разом із помилками перевірки."""
    return page('room_form', title=heading, active='rooms', raw=raw, errors=errors,
                error=error, action=action, types=svc.list_room_types())


@app.get('/rooms/new')
def room_new():
    """GET /rooms/new: порожня форма нового номера."""
    return room_form({}, {}, '', '/rooms/new', 'Новий номер')


@app.post('/rooms/new')
def room_create():
    """POST /rooms/new: перевіряє дані й додає номер."""
    raw = form_data()
    return submit(svc.create_room, raw, success_url='/rooms',
                  retry=lambda e, m: room_form(raw, e, m, '/rooms/new', 'Новий номер'))


@app.get('/rooms/<room_id:int>/edit')
def room_edit(room_id):
    """GET /rooms/<id>/edit: форма зміни номера із поточними значеннями."""
    raw = lookup(svc.get_room, room_id, back='/rooms')
    return room_form(raw, {}, '', f'/rooms/{room_id}/edit', 'Зміна номера')


@app.post('/rooms/<room_id:int>/edit')
def room_update(room_id):
    """POST /rooms/<id>/edit: перевіряє дані й змінює номер."""
    raw = form_data()
    return submit(svc.update_room, room_id, raw, success_url='/rooms',
                  retry=lambda e, m: room_form(raw, e, m, f'/rooms/{room_id}/edit',
                                               'Зміна номера'))


@app.post('/rooms/<room_id:int>/delete')
def room_delete(room_id):
    """POST /rooms/<id>/delete: видаляє номер (якщо в ньому немає історії проживань)."""
    act(svc.delete_room, room_id, back='/rooms')


# ---------------------------------------------------------------------------
# Клієнти
# ---------------------------------------------------------------------------

@app.route('/clients')
def clients():
    """Сторінка «Клієнти»: список клієнтів із пошуком за прізвищем, імʼям, паспортом або містом."""
    q = (request.query.getunicode('q') or '').strip()
    return page('clients', title='Клієнти', active='clients', q=q,
                clients=svc.list_clients(q))


def client_form(raw, errors, error, action, heading):
    """Показує форму клієнта (створення або зміна) разом із помилками перевірки."""
    return page('client_form', title=heading, active='clients', raw=raw, errors=errors,
                error=error, action=action)


@app.get('/clients/new')
def client_new():
    """GET /clients/new: порожня форма нового клієнта."""
    return client_form({}, {}, '', '/clients/new', 'Новий клієнт')


@app.post('/clients/new')
def client_create():
    """POST /clients/new: перевіряє дані й додає клієнта."""
    raw = form_data()
    return submit(svc.create_client, raw, success_url='/clients',
                  retry=lambda e, m: client_form(raw, e, m, '/clients/new', 'Новий клієнт'))


@app.get('/clients/<client_id:int>')
def client_view(client_id):
    """Картка клієнта: його дані та історія проживань."""
    client = lookup(svc.get_client, client_id, back='/clients')
    return page('client_view', title=svc_name(client), active='clients', client=client,
                stays=svc.client_stays(client_id))


def svc_name(client):
    """Повне імʼя клієнта для заголовка сторінки."""
    return ' '.join(p for p in (client['last_name'], client['first_name'],
                                client['patronymic']) if p)


@app.get('/clients/<client_id:int>/edit')
def client_edit(client_id):
    """GET /clients/<id>/edit: форма зміни даних клієнта."""
    raw = lookup(svc.get_client, client_id, back='/clients')
    return client_form(raw, {}, '', f'/clients/{client_id}/edit', 'Зміна даних клієнта')


@app.post('/clients/<client_id:int>/edit')
def client_update(client_id):
    """POST /clients/<id>/edit: перевіряє дані й змінює клієнта."""
    raw = form_data()
    return submit(svc.update_client, client_id, raw, success_url=f'/clients/{client_id}',
                  retry=lambda e, m: client_form(raw, e, m, f'/clients/{client_id}/edit',
                                                 'Зміна даних клієнта'))


@app.post('/clients/<client_id:int>/delete')
def client_delete(client_id):
    """POST /clients/<id>/delete: видаляє клієнта разом з історією його проживань."""
    act(svc.delete_client, client_id, back='/clients')


# ---------------------------------------------------------------------------
# Проживання
# ---------------------------------------------------------------------------

@app.route('/stays')
def stays():
    """Сторінка «Проживання»: поточні мешканці або вся історія (scope=all), з пошуком."""
    scope = request.query.get('scope', 'current')
    q = (request.query.getunicode('q') or '').strip()
    return page('stays', title='Проживання', active='stays', scope=scope, q=q,
                stays=svc.list_stays(current_only=(scope != 'all'), q=q))


def checkin_form(raw, errors, error):
    """Показує форму заселення разом із помилками перевірки та списком номерів."""
    return page('checkin', title='Заселення', active='stays', raw=raw, errors=errors,
                error=error, rooms=svc.list_rooms())


@app.get('/stays/check-in')
def checkin_new():
    """GET /stays/check-in: порожня форма заселення (номер можна передати в адресі)."""
    # ?room=102 підставляє номер кімнати (посилання зі сторінки номерів)
    return checkin_form({'room_number': request.query.get('room', '')}, {}, '')


@app.post('/stays/check-in')
def checkin_create():
    """POST /stays/check-in: перевіряє дані й заселяє клієнта (процедура check_in)."""
    raw = form_data()
    return submit(svc.check_in, raw, success_url='/stays',
                  retry=lambda e, m: checkin_form(raw, e, m))


@app.post('/stays/<stay_id:int>/check-out')
def checkout(stay_id):
    """POST /stays/<id>/check-out: виселяє клієнта (процедура check_out)."""
    act(svc.check_out, stay_id, form_data(), back=safe_back('/stays'))


def stay_form(stay_id, raw, errors, error):
    """Показує форму зміни проживання разом із помилками перевірки."""
    stay = lookup(svc.get_stay, stay_id, back='/stays')
    return page('stay_form', title='Зміна проживання', active='stays', stay=stay, raw=raw,
                errors=errors, error=error, rooms=svc.list_rooms())


@app.get('/stays/<stay_id:int>/edit')
def stay_edit(stay_id):
    """GET /stays/<id>/edit: форма зміни проживання із поточними значеннями."""
    stay = lookup(svc.get_stay, stay_id, back='/stays')
    raw = {'room_number': stay['room_number'], 'checkin_date': stay['checkin_date'].isoformat(),
           'checkout_date': stay['checkout_date'].isoformat() if stay['checkout_date'] else ''}
    return stay_form(stay_id, raw, {}, '')


@app.post('/stays/<stay_id:int>/edit')
def stay_update(stay_id):
    """POST /stays/<id>/edit: перевіряє дані й змінює проживання (тригери перевіряють місткість)."""
    raw = form_data()
    return submit(svc.update_stay, stay_id, raw, success_url='/stays?scope=all',
                  retry=lambda e, m: stay_form(stay_id, raw, e, m))


@app.post('/stays/<stay_id:int>/delete')
def stay_delete(stay_id):
    """POST /stays/<id>/delete: видаляє запис про проживання."""
    act(svc.delete_stay, stay_id, back=safe_back('/stays?scope=all'))


# ---------------------------------------------------------------------------
# Службовці та графік прибирання
# ---------------------------------------------------------------------------

@app.route('/employees')
def employees():
    """Сторінка «Службовці»: список службовців із графіком прибирання по днях тижня."""
    return page('employees', title='Службовці', active='employees',
                employees=svc.list_employees())


def employee_form(raw, errors, error, action, heading):
    """Показує форму службовця (прийом або зміна) разом із помилками перевірки."""
    return page('employee_form', title=heading, active='employees', raw=raw, errors=errors,
                error=error, action=action)


@app.get('/employees/new')
def employee_new():
    """GET /employees/new: порожня форма прийому службовця на роботу."""
    return employee_form({}, {}, '', '/employees/new', 'Прийняти службовця на роботу')


@app.post('/employees/new')
def employee_create():
    """POST /employees/new: перевіряє дані й приймає службовця (процедура hire_employee)."""
    raw = form_data()
    return submit(svc.hire_employee, raw, success_url='/employees',
                  retry=lambda e, m: employee_form(raw, e, m, '/employees/new',
                                                   'Прийняти службовця на роботу'))


@app.get('/employees/<employee_id:int>/edit')
def employee_edit(employee_id):
    """GET /employees/<id>/edit: форма зміни даних службовця."""
    raw = lookup(svc.get_employee, employee_id, back='/employees')
    return employee_form(raw, {}, '', f'/employees/{employee_id}/edit', 'Зміна даних службовця')


@app.post('/employees/<employee_id:int>/edit')
def employee_update(employee_id):
    """POST /employees/<id>/edit: перевіряє дані й змінює службовця."""
    raw = form_data()
    return submit(svc.update_employee, employee_id, raw, success_url='/employees',
                  retry=lambda e, m: employee_form(raw, e, m,
                                                   f'/employees/{employee_id}/edit',
                                                   'Зміна даних службовця'))


@app.post('/employees/<employee_id:int>/delete')
def employee_fire(employee_id):
    """POST /employees/<id>/delete: звільняє службовця (процедура fire_employee)."""
    act(svc.fire_employee, employee_id, back='/employees')


def schedule_form(employee_id, raw, errors, error):
    """Показує форму графіка прибирання: поверх для кожного дня тижня."""
    employee = lookup(svc.get_employee, employee_id, back='/employees')
    if raw is None:
        raw = {f'floor_{d}': employee['schedule'].get(d, '') for d in range(1, 8)}
    return page('schedule', title='Графік прибирання', active='employees', employee=employee,
                raw=raw, errors=errors, error=error, floors=svc.existing_floors())


@app.get('/employees/<employee_id:int>/schedule')
def schedule_edit(employee_id):
    """GET /employees/<id>/schedule: форма зміни графіка із поточними поверхами."""
    return schedule_form(employee_id, None, {}, '')


@app.post('/employees/<employee_id:int>/schedule')
def schedule_update(employee_id):
    """POST /employees/<id>/schedule: змінює графік (процедура change_schedule)."""
    raw = form_data()
    return submit(svc.change_schedule, employee_id, raw, success_url='/employees',
                  retry=lambda e, m: schedule_form(employee_id, raw, e, m))


# ---------------------------------------------------------------------------
# Запити з варіанта завдання
# ---------------------------------------------------------------------------

@app.route('/queries')
def queries_page():
    """Сторінка «Запити»: параметри з адреси та результати чотирьох запитів варіанта."""
    # значення за замовчуванням ті самі, що в лабораторній роботі 3
    params = {
        'room': (request.query.getunicode('room') or '101').strip(),
        'city': (request.query.getunicode('city') or 'Харків').strip(),
        'passport': (request.query.getunicode('passport') or 'ЕК456789').strip(),
        'weekday': (request.query.getunicode('weekday') or '3').strip(),
    }
    return page('queries', title='Запити', active='queries', params=params,
                result=svc.run_queries(**params))


# ---------------------------------------------------------------------------
# Запуск для розробки. Під uWSGI цей блок не виконується.
# ---------------------------------------------------------------------------

class StripPathMiddleware(object):
    """Прибирає зайвий слеш в кінці адреси (під час розробки)."""

    def __init__(self, a):
        """Запамʼятовує вкладений WSGI-додаток."""
        self.a = a

    def __call__(self, e, h):
        """Прибирає слеш в кінці адреси й передає запит додатку."""
        e['PATH_INFO'] = e['PATH_INFO'].rstrip('/') or '/'
        return self.a(e, h)


if __name__ == '__main__':
    bottle.run(app=StripPathMiddleware(app),
               host=os.environ.get('HOST', 'localhost'),
               port=int(os.environ.get('PORT', '8085')),
               debug=True)
