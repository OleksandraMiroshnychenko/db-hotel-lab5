"""Операції додатку: читання даних і зміни в базі.

Кожна зміна виконується в одній транзакції (db.transaction): вона або
фіксується повністю, або не змінює нічого. Складні операції адміністратора
(заселення, виселення, найм, звільнення, зміна графіка) виконують збережені
процедури бази даних; прості зміни довідників виконує ORM. Правила цілісності,
специфічні для готелю, перевіряють тригери бази: їхні повідомлення додаток
показує користувачеві як є.
"""
from collections import namedtuple

from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import DBAPIError

from . import queries
from . import validation as v
from .db import Session, transaction
from .models import Client, CleaningSchedule, Employee, Room, RoomType, Stay


class UserError(Exception):
    """Помилка, яку зрозуміло показати користувачеві (текст українською)."""


# message - що показати про успіх; warnings - попередження (наприклад, недоступний кеш)
Outcome = namedtuple('Outcome', 'message warnings value')

WEEKDAYS = ['понеділок', 'вівторок', 'середа', 'четвер', 'пʼятниця', 'субота', 'неділя']
WEEKDAYS_SHORT = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд']


# ---------------------------------------------------------------------------
# Переклад помилок бази даних
# ---------------------------------------------------------------------------

CONSTRAINT_MESSAGES = {
    # унікальність
    'clients_passport_number_key': 'Клієнт із таким номером паспорта вже є в базі.',
    'rooms_room_number_key': 'Номер із таким номером кімнати вже існує.',
    'room_types_name_key': 'Тип номера з такою назвою вже існує.',
    # перевірки CHECK
    'room_types_capacity_check': 'Місткість типу номера — від 1 до 3 осіб.',
    'room_types_price_per_day_check': 'Ціна за добу має бути більшою за нуль.',
    'rooms_floor_check': 'Поверх має бути додатним числом.',
    'stays_check': 'Дата виселення не може бути раніше за дату заселення.',
    'cleaning_schedule_floor_check': 'Поверх має бути додатним числом.',
    'cleaning_schedule_weekday_check': 'День тижня — від 1 (понеділок) до 7 (неділя).',
}

# зовнішні ключі: повідомлення, коли видаляють запис, на який посилаються
FK_ON_DELETE = {
    'rooms_room_type_id_fkey': 'Тип номера використовують номери, тому його не можна видалити.',
    'stays_room_id_fkey': 'У номері є історія проживань, тому його не можна видалити.',
}
# зовнішні ключі: повідомлення, коли вказують неіснуючий запис
FK_ON_INSERT = {
    'rooms_room_type_id_fkey': 'Вказаного типу номера не існує.',
    'stays_room_id_fkey': 'Вказаного номера не існує.',
    'stays_client_id_fkey': 'Вказаного клієнта не існує.',
    'cleaning_schedule_employee_id_fkey': 'Вказаного службовця не існує.',
}


def translate_error(exc, deleting=False):
    """Перетворює помилку PostgreSQL на повідомлення, зрозуміле користувачеві.

    Повідомлення тригерів і процедур (RAISE EXCEPTION) уже написані українською
    й описують порушене правило, тому показуються без змін.
    """
    orig = exc.orig
    diag = getattr(orig, 'diag', None)
    pgcode = getattr(orig, 'pgcode', None)
    constraint = getattr(diag, 'constraint_name', None)
    table = getattr(diag, 'table_name', None)
    primary = (getattr(diag, 'message_primary', None) or str(orig)).strip()

    if constraint in CONSTRAINT_MESSAGES:
        return CONSTRAINT_MESSAGES[constraint]
    if pgcode == '23503':   # порушення зовнішнього ключа
        if deleting and constraint in FK_ON_DELETE:
            return FK_ON_DELETE[constraint]
        if constraint in FK_ON_INSERT:
            return FK_ON_INSERT[constraint]
        return 'Дію не можна виконати: порушено звʼязок із іншими записами.'
    if pgcode == '23502':   # порожнє значення в обовʼязковому полі
        column = getattr(diag, 'column_name', None) or 'поле'
        return f'Не заповнено обовʼязкове поле ({column}).'
    if pgcode == '22001':
        return 'Занадто довге значення.'
    if table and pgcode == '23505':
        return 'Запис із такими даними вже існує.'
    return primary


def split_notices(notices):
    """Ділить повідомлення бази на інформаційні та попередження."""
    infos, warnings = [], []
    for notice in notices:
        first_line = notice.splitlines()[0] if notice else ''
        kind, _, body = first_line.partition(':')
        body = body.strip()
        if not body:
            continue
        if kind.strip() == 'WARNING':
            warnings.append(body)
        else:
            infos.append(body)
    return infos, warnings


def run(work, success, deleting=False):
    """Виконує work(tx) в одній транзакції та формує результат.

    work - функція, яка робить зміни; success - повідомлення про успіх за
    замовчуванням (якщо процедура не повернула власного); deleting - це видалення
    (від цього залежить повідомлення про порушення зовнішнього ключа). Помилки
    бази перетворюються на UserError зі зрозумілим текстом.
    """
    # holder передає результат work() назовні: він потрібен уже після виходу з блоку with
    holder = {}
    try:
        with transaction() as tx:
            holder['value'] = work(tx)
        # tx.notices заповнює transaction() після commit, тому читаємо їх поза блоком with
        infos, warnings = split_notices(tx.notices)
    except DBAPIError as exc:
        raise UserError(translate_error(exc, deleting)) from exc
    return Outcome(' '.join(infos) or success, warnings, holder.get('value'))


def _like(q):
    """Шаблон LIKE для пошуку підрядка (спецсимволи екрануються)."""
    escaped = q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    return f'%{escaped}%'


def _require(count, what):
    """Кидає UserError, якщо запис не знайдено (count порожній або дорівнює нулю)."""
    if not count:
        raise UserError(f'{what} не знайдено (можливо, запис уже видалено).')


# ---------------------------------------------------------------------------
# Читання
# ---------------------------------------------------------------------------

def get_dashboard():
    """Дані головної сторінки: лічильники, вільні місця й поточні мешканці."""
    with Session() as s:
        counts = s.execute(text(
            "SELECT (SELECT count(*) FROM rooms) AS rooms,"
            "       (SELECT count(*) FROM stays WHERE checkout_date IS NULL) AS guests,"
            "       (SELECT count(*) FROM clients) AS clients,"
            "       (SELECT count(*) FROM employees) AS employees")).mappings().one()
        return {
            'availability': queries.availability(s),
            'counts': dict(counts),
            'current': _stays(s, current_only=True, q='')[:8],
        }


def list_rooms():
    """Усі номери зі станом із представлення room_status, за номером кімнати."""
    with Session() as s:
        return [dict(r) for r in s.execute(
            text('SELECT * FROM room_status ORDER BY room_number')).mappings()]


def get_room(room_id):
    """Один номер за ідентифікатором (для форми зміни); UserError, якщо не знайдено."""
    with Session() as s:
        room = s.get(Room, room_id)
        _require(room, 'Номер')
        return {'room_id': room.room_id, 'room_number': room.room_number,
                'floor': room.floor, 'phone': room.phone, 'room_type_id': room.room_type_id}


def list_room_types():
    """Типи номерів із кількістю номерів кожного типу."""
    with Session() as s:
        return [dict(r) for r in s.execute(text(
            "SELECT t.room_type_id, t.name, t.capacity, t.price_per_day,"
            "       (SELECT count(*) FROM rooms r WHERE r.room_type_id = t.room_type_id) AS rooms"
            "  FROM room_types t ORDER BY t.capacity, t.name")).mappings()]


def get_room_type(type_id):
    """Один тип номера за ідентифікатором (для форми зміни)."""
    with Session() as s:
        t = s.get(RoomType, type_id)
        _require(t, 'Тип номера')
        return {'room_type_id': t.room_type_id, 'name': t.name, 'capacity': t.capacity,
                'price_per_day': t.price_per_day}


def list_clients(q=''):
    """Клієнти з поточним номером і кількістю проживань; q - пошук за підрядком."""
    with Session() as s:
        rows = s.execute(text(
            "SELECT c.client_id, c.passport_number, c.last_name, c.first_name, c.patronymic,"
            "       c.city,"
            "       (SELECT r.room_number FROM stays st JOIN rooms r ON r.room_id = st.room_id"
            "         WHERE st.client_id = c.client_id AND st.checkout_date IS NULL) AS current_room,"
            "       (SELECT count(*) FROM stays st WHERE st.client_id = c.client_id) AS stays_count"
            "  FROM clients c"
            " WHERE :q = '' OR c.last_name ILIKE :like OR c.first_name ILIKE :like"
            "    OR c.passport_number ILIKE :like OR c.city ILIKE :like"
            " ORDER BY c.last_name, c.first_name"), {'q': q, 'like': _like(q)}).mappings()
        return [dict(r) for r in rows]


def get_client(client_id):
    """Один клієнт за ідентифікатором (для картки й форми зміни)."""
    with Session() as s:
        c = s.get(Client, client_id)
        _require(c, 'Клієнта')
        return {'client_id': c.client_id, 'passport_number': c.passport_number,
                'last_name': c.last_name, 'first_name': c.first_name,
                'patronymic': c.patronymic or '', 'city': c.city}


def _stays(s, current_only, q, client_id=None):
    """Проживання з іменем клієнта, номером і тривалістю; фільтри: поточні, пошук, клієнт."""
    rows = s.execute(text(
        "SELECT st.stay_id, st.checkin_date, st.checkout_date,"
        "       c.client_id, c.passport_number,"
        "       concat_ws(' ', c.last_name, c.first_name, c.patronymic) AS client_name,"
        "       r.room_id, r.room_number, rt.name AS room_type,"
        "       (COALESCE(st.checkout_date, CURRENT_DATE) - st.checkin_date) AS days"
        "  FROM stays st"
        "  JOIN clients c ON c.client_id = st.client_id"
        "  JOIN rooms r ON r.room_id = st.room_id"
        "  JOIN room_types rt ON rt.room_type_id = r.room_type_id"
        " WHERE (NOT :current_only OR st.checkout_date IS NULL)"
        "   AND (CAST(:client_id AS INTEGER) IS NULL OR st.client_id = CAST(:client_id AS INTEGER))"
        "   AND (:q = '' OR c.last_name ILIKE :like OR c.passport_number ILIKE :like"
        "        OR CAST(r.room_number AS TEXT) = :q)"
        " ORDER BY (st.checkout_date IS NULL) DESC, st.checkin_date DESC, st.stay_id DESC"),
        {'current_only': current_only, 'q': q, 'like': _like(q), 'client_id': client_id}
    ).mappings()
    return [dict(r) for r in rows]


def list_stays(current_only=False, q=''):
    """Список проживань для сторінки «Проживання» (лише поточні або всі)."""
    with Session() as s:
        return _stays(s, current_only, q)


def client_stays(client_id):
    """Уся історія проживань одного клієнта."""
    with Session() as s:
        return _stays(s, False, '', client_id)


def get_stay(stay_id):
    """Одне проживання за ідентифікатором (для форми зміни)."""
    with Session() as s:
        rows = s.execute(text(
            "SELECT st.stay_id, st.checkin_date, st.checkout_date, r.room_number,"
            "       c.passport_number,"
            "       concat_ws(' ', c.last_name, c.first_name, c.patronymic) AS client_name"
            "  FROM stays st JOIN rooms r ON r.room_id = st.room_id"
            "  JOIN clients c ON c.client_id = st.client_id"
            " WHERE st.stay_id = :id"), {'id': stay_id}).mappings().all()
        _require(rows, 'Проживання')
        return dict(rows[0])


def _employees(s, employee_id=None):
    """Службовці з графіком прибирання {день тижня: поверх}; за потреби лише один."""
    employees = s.execute(
        select(Employee).order_by(Employee.last_name, Employee.first_name)).scalars().all()
    schedule = {}
    for row in s.execute(select(CleaningSchedule)).scalars():
        schedule.setdefault(row.employee_id, {})[row.weekday] = row.floor
    result = []
    for e in employees:
        if employee_id is not None and e.employee_id != employee_id:
            continue
        result.append({'employee_id': e.employee_id, 'last_name': e.last_name,
                       'first_name': e.first_name, 'patronymic': e.patronymic or '',
                       'full_name': e.full_name,
                       'schedule': schedule.get(e.employee_id, {})})
    return result


def list_employees():
    """Усі службовці з їхніми графіками."""
    with Session() as s:
        return _employees(s)


def get_employee(employee_id):
    """Один службовець із графіком (для форм зміни та графіка)."""
    with Session() as s:
        found = _employees(s, employee_id)
        _require(found, 'Службовця')
        return found[0]


def existing_floors():
    """Поверхи, які є в готелі (для підказок у формі графіка)."""
    with Session() as s:
        return list(s.scalars(select(Room.floor).distinct().order_by(Room.floor)))


# ---------------------------------------------------------------------------
# Запити з варіанта завдання
# ---------------------------------------------------------------------------

def run_queries(room, city, passport, weekday):
    """Виконує чотири запити з варіанта. Помилки введення повертаються разом із результатом."""
    checker = v.Checker({'room': room, 'city': city, 'passport': passport, 'weekday': weekday})
    room_number = checker.integer('room', 'Номер кімнати', 1, 9999)
    checker.city('city', 'Місто')
    checker.passport('passport')
    weekday_number = checker.integer('weekday', 'День тижня', 1, 7)
    clean = checker.clean
    result = {'errors': dict(checker.errors)}
    with Session() as s:
        if 'room' not in checker.errors:
            result['q1'] = queries.room_clients(s, room_number)
        if 'city' not in checker.errors:
            result['q2'] = queries.city_clients(s, clean['city'])
        if 'passport' not in checker.errors and 'weekday' not in checker.errors:
            result['q3'] = queries.room_cleaner(s, clean['passport'], weekday_number)
        result['q4'] = queries.availability(s)
    return result


# ---------------------------------------------------------------------------
# Клієнти
# ---------------------------------------------------------------------------

def create_client(raw):
    """Додає клієнта після перевірки даних."""
    data = v.validate_client(raw)

    def work(tx):
        """Тіло транзакції: створює клієнта й повертає його ідентифікатор."""
        client = Client(**data)
        tx.session.add(client)
        tx.session.flush()
        return client.client_id

    return run(work, f'Клієнта {data["last_name"]} {data["first_name"]} додано.')


def update_client(client_id, raw):
    """Змінює дані клієнта після перевірки."""
    data = v.validate_client(raw)

    def work(tx):
        """Тіло транзакції: записує нові значення полів клієнта."""
        client = tx.session.get(Client, client_id)
        _require(client, 'Клієнта')
        for field, value in data.items():
            setattr(client, field, value)
        tx.session.flush()

    return run(work, 'Дані клієнта змінено.')


def delete_client(client_id):
    """Видаляє клієнта; його проживання видаляє сама база (ON DELETE CASCADE)."""
    def work(tx):
        """Тіло транзакції: видаляє клієнта."""
        result = tx.session.execute(delete(Client).where(Client.client_id == client_id))
        _require(result.rowcount, 'Клієнта')

    # проживання клієнта видаляє сама база (ON DELETE CASCADE)
    return run(work, 'Клієнта видалено разом з історією його проживань.')


# ---------------------------------------------------------------------------
# Типи номерів і номери
# ---------------------------------------------------------------------------

def create_room_type(raw):
    """Додає тип номера після перевірки даних."""
    data = v.validate_room_type(raw)

    def work(tx):
        """Тіло транзакції: додає тип номера."""
        tx.session.add(RoomType(**data))
        tx.session.flush()

    return run(work, f'Тип номера «{data["name"]}» додано.')


def update_room_type(type_id, raw):
    """Змінює тип номера (назву, місткість, ціну) після перевірки."""
    data = v.validate_room_type(raw)

    def work(tx):
        """Тіло транзакції: записує нові значення; місткість і ціну перевіряють тригери."""
        room_type = tx.session.get(RoomType, type_id)
        _require(room_type, 'Тип номера')
        for field, value in data.items():
            setattr(room_type, field, value)
        # місткість і ціна перевіряються тригером: не можна зменшити місткість нижче
        # кількості мешканців, що проживають зараз
        tx.session.flush()

    return run(work, 'Тип номера змінено. Ціни номерів у кеші оновлено.')


def delete_room_type(type_id):
    """Видаляє тип номера, якщо його не використовують номери."""
    def work(tx):
        """Тіло транзакції: видаляє тип номера."""
        result = tx.session.execute(delete(RoomType).where(RoomType.room_type_id == type_id))
        _require(result.rowcount, 'Тип номера')

    return run(work, 'Тип номера видалено.', deleting=True)


def create_room(raw):
    """Додає номер після перевірки даних."""
    data = v.validate_room(raw)

    def work(tx):
        """Тіло транзакції: додає номер."""
        tx.session.add(Room(**data))
        tx.session.flush()

    return run(work, f'Номер {data["room_number"]} додано.')


def update_room(room_id, raw):
    """Змінює дані номера після перевірки."""
    data = v.validate_room(raw)

    def work(tx):
        """Тіло транзакції: записує нові значення полів номера."""
        room = tx.session.get(Room, room_id)
        _require(room, 'Номер')
        for field, value in data.items():
            setattr(room, field, value)
        tx.session.flush()

    return run(work, 'Дані номера змінено.')


def delete_room(room_id):
    """Видаляє номер, якщо в ньому немає історії проживань."""
    def work(tx):
        """Тіло транзакції: видаляє номер."""
        result = tx.session.execute(delete(Room).where(Room.room_id == room_id))
        _require(result.rowcount, 'Номер')

    return run(work, 'Номер видалено.', deleting=True)


# ---------------------------------------------------------------------------
# Проживання
# ---------------------------------------------------------------------------

def check_in(raw):
    """Заселення: процедура check_in створює клієнта (якщо його ще немає) і проживання."""
    data = v.validate_checkin(raw)

    def work(tx):
        """Тіло транзакції: перевіряє наявність клієнта й викликає процедуру check_in."""
        session = tx.session
        client_id = session.scalar(
            select(Client.client_id).where(Client.passport_number == data['passport_number']))
        if client_id is None:
            # новий клієнт: потрібні прізвище, імʼя й місто
            missing = {}
            for field, label in (('last_name', 'Прізвище'), ('first_name', 'Імʼя'),
                                 ('city', 'Місто')):
                if not data[field]:
                    missing[field] = (f'{label}: потрібне для нового клієнта '
                                      f'(клієнта з таким паспортом ще немає в базі).')
            if missing:
                raise v.ValidationError(missing)
            names = data
        else:
            # клієнт уже є: його дані з форми ігноруються
            names = {'last_name': None, 'first_name': None, 'patronymic': None, 'city': None}
        session.execute(
            text('CALL check_in(:passport, :room, :date, :last_name, :first_name, '
                 ':patronymic, :city)'),
            {'passport': data['passport_number'], 'room': data['room_number'],
             'date': data['checkin_date'], 'last_name': names['last_name'],
             'first_name': names['first_name'], 'patronymic': names['patronymic'],
             'city': names['city']})

    return run(work, 'Клієнта поселено.')


def check_out(stay_id, raw):
    """Виселення: процедура check_out закриває поточне проживання клієнта."""
    data = v.validate_checkout(raw)

    def work(tx):
        """Тіло транзакції: знаходить клієнта проживання й викликає процедуру check_out."""
        stay = tx.session.get(Stay, stay_id)
        _require(stay, 'Проживання')
        if stay.checkout_date is not None:
            raise UserError('Це проживання вже завершено.')
        passport = tx.session.scalar(
            select(Client.passport_number).where(Client.client_id == stay.client_id))
        tx.session.execute(text('CALL check_out(:passport, :date)'),
                           {'passport': passport, 'date': data['checkout_date']})

    return run(work, 'Клієнта виселено.')


def update_stay(stay_id, raw):
    """Змінює номер і дати проживання після перевірки."""
    data = v.validate_stay(raw)

    def work(tx):
        """Тіло транзакції: переносить проживання; місткість і періоди перевіряють тригери."""
        session = tx.session
        stay = session.get(Stay, stay_id)
        _require(stay, 'Проживання')
        room_id = session.scalar(
            select(Room.room_id).where(Room.room_number == data['room_number']))
        if room_id is None:
            raise v.ValidationError({'room_number': f'Номера {data["room_number"]} у готелі немає.'})
        stay.room_id = room_id
        stay.checkin_date = data['checkin_date']
        stay.checkout_date = data['checkout_date']
        # місткість і неперетин періодів перевіряють тригери
        session.flush()

    return run(work, 'Проживання змінено.')


def delete_stay(stay_id):
    """Видаляє запис про проживання."""
    def work(tx):
        """Тіло транзакції: видаляє проживання."""
        result = tx.session.execute(delete(Stay).where(Stay.stay_id == stay_id))
        _require(result.rowcount, 'Проживання')

    return run(work, 'Запис про проживання видалено.')


# ---------------------------------------------------------------------------
# Службовці та графік прибирання
# ---------------------------------------------------------------------------

def hire_employee(raw):
    """Приймає службовця на роботу (процедура hire_employee)."""
    data = v.validate_employee(raw)

    def work(tx):
        """Тіло транзакції: викликає процедуру й повертає ідентифікатор нового службовця."""
        # INOUT-параметр: передаємо NULL, процедура повертає employee_id
        return tx.session.execute(
            text('CALL hire_employee(:last_name, :first_name, :patronymic, NULL)'),
            {'last_name': data['last_name'], 'first_name': data['first_name'],
             'patronymic': data['patronymic']}).scalar_one()

    return run(work, 'Службовця прийнято на роботу.')


def update_employee(employee_id, raw):
    """Змінює імʼя службовця після перевірки."""
    data = v.validate_employee(raw)

    def work(tx):
        """Тіло транзакції: записує нові значення полів службовця."""
        employee = tx.session.get(Employee, employee_id)
        _require(employee, 'Службовця')
        for field, value in data.items():
            setattr(employee, field, value)
        tx.session.flush()

    return run(work, 'Дані службовця змінено.')


def fire_employee(employee_id):
    """Звільняє службовця (процедура fire_employee)."""
    def work(tx):
        """Тіло транзакції: викликає процедуру fire_employee."""
        tx.session.execute(text('CALL fire_employee(:id)'), {'id': employee_id})

    return run(work, 'Службовця звільнено.')


def change_schedule(employee_id, raw):
    """Змінює графік за одну транзакцію: або всі зміни, або жодної."""
    floors = v.validate_schedule(raw)

    def work(tx):
        """Тіло транзакції: викликає change_schedule лише для днів, де поверх справді змінився."""
        current = {row.weekday: row.floor for row in tx.session.scalars(
            select(CleaningSchedule).where(CleaningSchedule.employee_id == employee_id))}
        changed = 0
        for weekday, floor in floors.items():
            if current.get(weekday) == floor:
                continue
            tx.session.execute(text('CALL change_schedule(:emp, :weekday, :floor)'),
                               {'emp': employee_id, 'weekday': weekday, 'floor': floor})
            changed += 1
        return changed

    outcome = run(work, 'Графік змінено.')
    if outcome.value == 0:
        return Outcome('Змін у графіку немає.', [], 0)
    return Outcome(f'Графік змінено (змінено днів: {outcome.value}).', outcome.warnings,
                   outcome.value)
