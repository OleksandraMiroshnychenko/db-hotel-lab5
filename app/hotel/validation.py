"""Перевірка та нормалізація даних, які вводить користувач.

Перевірки відповідають специфікації предметної області, а не лише технічним
обмеженням бази даних: формат паспорта, імен, телефону, відповідність номера
кімнати поверху, коректність дат проживання. Усі помилки збираються разом, щоб
користувач бачив їх одразу, а не по одній.
"""
import re
from datetime import date
from decimal import Decimal, InvalidOperation

# найраніша дата проживання, яку приймає додаток
MIN_DATE = date(2000, 1, 1)

LETTERS = "A-Za-zА-Яа-яІіЇїЄєҐґ"
APOSTROPHES = "'ʼ’`"

NAME_RE = re.compile(rf"^[{LETTERS}{APOSTROPHES}\- ]{{1,50}}$")
CITY_RE = re.compile(rf"^[{LETTERS}{APOSTROPHES}.\- ]{{2,50}}$")
TYPE_NAME_RE = re.compile(rf"^[{LETTERS}0-9][{LETTERS}0-9{APOSTROPHES}\- ]{{1,29}}$")
PASSPORT_BOOK_RE = re.compile(r"^[А-ЯІЇЄҐ]{2}\d{6}$")   # паспорт-книжка: серія + 6 цифр
PASSPORT_ID_RE = re.compile(r"^\d{9}$")                  # ID-картка: 9 цифр
PHONE_RE = re.compile(r"^\+380\d{9}$")

# латинські літери, схожі на українські: у серії паспорта їх замінюють на українські
LATIN_TO_CYRILLIC = str.maketrans("ABCEHIKMOPTXY", "АВСЕНІКМОРТХУ")


class ValidationError(Exception):
    """Помилки введених даних: словник «поле -> повідомлення»."""

    def __init__(self, errors):
        """Зберігає словник помилок «поле -> повідомлення»."""
        super().__init__('; '.join(errors.values()))
        self.errors = errors


class Checker:
    """Збирає очищені значення полів форми та повідомлення про помилки."""

    def __init__(self, raw):
        """Приймає сирі значення форми; clean і errors заповнюються під час перевірки."""
        self.raw = raw
        self.clean = {}
        self.errors = {}

    def _value(self, field):
        """Значення поля без пробілів по краях (порожній рядок, якщо поля немає)."""
        return (self.raw.get(field) or '').strip()

    def fail(self, field, message):
        """Записує помилку поля (лише перше повідомлення для кожного поля)."""
        # для поля зберігається лише перше повідомлення
        self.errors.setdefault(field, message)

    # ---- текстові поля -------------------------------------------------------

    def name(self, field, label, required=True):
        """Імʼя, прізвище або по батькові: літери, дефіс, апостроф; кожна частина з великої літери."""
        value = re.sub(r'\s+', ' ', self._value(field))
        if not value:
            if required:
                self.fail(field, f'{label}: обовʼязкове поле.')
            self.clean[field] = None
            return
        if not NAME_RE.match(value) or not re.search(f'[{LETTERS}]', value):
            self.fail(field, f'{label}: лише літери, дефіс і апостроф, до 50 символів.')
            return
        for ch in APOSTROPHES:
            value = value.replace(ch, 'ʼ')
        self.clean[field] = capitalize_parts(value)

    def type_name(self, field, label):
        """Назва типу номера: малими літерами, як у наявних типах (одномісний, тримісний)."""
        value = re.sub(r'\s+', ' ', self._value(field))
        if not value:
            self.fail(field, f'{label}: обовʼязкове поле.')
            return
        if not TYPE_NAME_RE.match(value) or not re.search(f'[{LETTERS}]', value):
            self.fail(field, f'{label}: літери, цифри, дефіс і апостроф, від 2 до 30 символів.')
            return
        for ch in APOSTROPHES:
            value = value.replace(ch, 'ʼ')
        self.clean[field] = value.lower()

    def city(self, field, label, required=True):
        """Місто: літери, дефіс, апостроф і крапка; кожна частина з великої літери."""
        value = re.sub(r'\s+', ' ', self._value(field))
        if not value:
            if required:
                self.fail(field, f'{label}: обовʼязкове поле.')
            self.clean[field] = None
            return
        if not CITY_RE.match(value) or not re.search(f'[{LETTERS}]', value):
            self.fail(field, f'{label}: лише літери, дефіс, апостроф і крапка, від 2 до 50 символів.')
            return
        for ch in APOSTROPHES:
            value = value.replace(ch, 'ʼ')
        self.clean[field] = capitalize_parts(value)

    def passport(self, field, label='Паспорт'):
        """Паспорт: серія з двох літер і 6 цифр або 9 цифр ID-картки; приводить до великих літер."""
        # прибираємо пробіли й дефіси, робимо літери великими й замінюємо схожі латинські на українські
        value = re.sub(r'[\s\-]', '', self._value(field)).upper().translate(LATIN_TO_CYRILLIC)
        if not value:
            self.fail(field, f'{label}: обовʼязкове поле.')
            return
        if not (PASSPORT_BOOK_RE.match(value) or PASSPORT_ID_RE.match(value)):
            self.fail(field, f'{label}: дві літери серії й шість цифр (наприклад, ЕК123456) '
                             f'або дев’ять цифр ID-картки.')
            return
        self.clean[field] = value

    def phone(self, field, label='Телефон'):
        """Телефон: приводить до вигляду +380XXXXXXXXX і перевіряє формат."""
        value = re.sub(r'[\s\-()]', '', self._value(field))
        # номери 0XXXXXXXXX і 380XXXXXXXXX приводимо до єдиного вигляду +380XXXXXXXXX
        if re.fullmatch(r'0\d{9}', value):
            value = '+38' + value
        elif re.fullmatch(r'380\d{9}', value):
            value = '+' + value
        if not value:
            self.fail(field, f'{label}: обовʼязкове поле.')
            return
        if not PHONE_RE.match(value):
            self.fail(field, f'{label}: формат +380XXXXXXXXX.')
            return
        self.clean[field] = value

    # ---- числа ---------------------------------------------------------------

    def integer(self, field, label, low, high, required=True):
        """Ціле число в межах від low до high; повертає число або None."""
        text = self._value(field)
        if not text:
            if required:
                self.fail(field, f'{label}: обовʼязкове поле.')
            self.clean[field] = None
            return None
        try:
            number = int(text)
        except ValueError:
            self.fail(field, f'{label}: потрібне ціле число.')
            return None
        if not low <= number <= high:
            self.fail(field, f'{label}: число від {low} до {high}.')
            return None
        self.clean[field] = number
        return number

    def money(self, field, label):
        """Сума: більше нуля, менше 100000, не більше двох знаків після коми."""
        text = self._value(field).replace(',', '.').replace(' ', '')
        if not text:
            self.fail(field, f'{label}: обовʼязкове поле.')
            return
        try:
            amount = Decimal(text)
        except InvalidOperation:
            self.fail(field, f'{label}: потрібне число (наприклад, 1200 або 1200.50).')
            return
        if not amount.is_finite() or amount <= 0 or amount >= Decimal('100000'):
            self.fail(field, f'{label}: більше нуля й менше 100000.')
            return
        if amount != amount.quantize(Decimal('0.01')):
            self.fail(field, f'{label}: не більше двох знаків після коми.')
            return
        self.clean[field] = amount.quantize(Decimal('0.01'))

    # ---- дати ----------------------------------------------------------------

    def date(self, field, label, required=True, default=None):
        """Дата РРРР-ММ-ДД: не раніше 2000 року й не в майбутньому; є значення за замовчуванням."""
        text = self._value(field)
        if not text:
            if default is not None:
                self.clean[field] = default
                return default
            if required:
                self.fail(field, f'{label}: обовʼязкове поле.')
            self.clean[field] = None
            return None
        try:
            value = date.fromisoformat(text)
        except ValueError:
            self.fail(field, f'{label}: потрібна дата у форматі РРРР-ММ-ДД.')
            return None
        if value < MIN_DATE:
            self.fail(field, f'{label}: не раніше {MIN_DATE.isoformat()}.')
            return None
        if value > date.today():
            self.fail(field, f'{label}: дата не може бути в майбутньому.')
            return None
        self.clean[field] = value
        return value

    def done(self):
        """Повертає очищені значення або кидає ValidationError з усіма помилками."""
        if self.errors:
            raise ValidationError(self.errors)
        return self.clean


def capitalize_parts(value):
    """Робить великою першу літеру кожного слова й частини після дефіса."""
    return re.sub(r"(^|[ \-])([^ \-])", lambda m: m.group(1) + m.group(2).upper(), value)


# ---- перевірка кожної форми --------------------------------------------------

def validate_client(raw):
    """Перевіряє форму клієнта: паспорт, прізвище, імʼя, по батькові, місто."""
    c = Checker(raw)
    c.passport('passport_number')
    c.name('last_name', 'Прізвище')
    c.name('first_name', 'Імʼя')
    c.name('patronymic', 'По батькові', required=False)
    c.city('city', 'Місто')
    return c.done()


def validate_room_type(raw):
    """Перевіряє форму типу номера: назва, місткість 1-3, ціна за добу."""
    c = Checker(raw)
    c.type_name('name', 'Назва типу')
    c.integer('capacity', 'Місткість', 1, 3)
    c.money('price_per_day', 'Ціна за добу')
    return c.done()


def validate_room(raw):
    """Перевіряє форму номера; номер кімнати має починатися з номера поверху."""
    c = Checker(raw)
    number = c.integer('room_number', 'Номер кімнати', 101, 9999)
    floor = c.integer('floor', 'Поверх', 1, 99)
    c.phone('phone')
    c.integer('room_type_id', 'Тип номера', 1, 2_147_483_647)
    # прийнята в готелі нумерація: перша частина номера - це поверх (101 -> 1, 302 -> 3)
    if number is not None and floor is not None and number // 100 != floor:
        c.fail('floor', f'Номер {number} має бути на поверсі {number // 100}: '
                        f'номер кімнати починається з номера поверху.')
    return c.done()


def validate_checkin(raw):
    """Перевіряє форму заселення; дані клієнта потрібні лише для нового клієнта."""
    c = Checker(raw)
    c.passport('passport_number')
    c.integer('room_number', 'Номер кімнати', 101, 9999)
    c.date('checkin_date', 'Дата заселення', default=date.today())
    # дані клієнта потрібні лише для нового клієнта, тут перевіряється тільки їхній формат
    c.name('last_name', 'Прізвище', required=False)
    c.name('first_name', 'Імʼя', required=False)
    c.name('patronymic', 'По батькові', required=False)
    c.city('city', 'Місто', required=False)
    return c.done()


def validate_checkout(raw):
    """Перевіряє форму виселення: дата (за замовчуванням сьогодні)."""
    c = Checker(raw)
    c.date('checkout_date', 'Дата виселення', default=date.today())
    return c.done()


def validate_stay(raw):
    """Перевіряє зміну проживання: номер, дати, виселення не раніше заселення."""
    c = Checker(raw)
    c.integer('room_number', 'Номер кімнати', 101, 9999)
    checkin = c.date('checkin_date', 'Дата заселення')
    checkout = c.date('checkout_date', 'Дата виселення', required=False)
    if checkin and checkout and checkout < checkin:
        c.fail('checkout_date', 'Дата виселення не може бути раніше за дату заселення.')
    return c.done()


def validate_employee(raw):
    """Перевіряє форму службовця: прізвище, імʼя, по батькові."""
    c = Checker(raw)
    c.name('last_name', 'Прізвище')
    c.name('first_name', 'Імʼя')
    c.name('patronymic', 'По батькові', required=False)
    return c.done()


def validate_schedule(raw):
    """Графік прибирання: для кожного дня тижня поверх (порожнє поле - день вільний)."""
    c = Checker(raw)
    floors = {}
    for weekday in range(1, 8):
        field = f'floor_{weekday}'
        floors[weekday] = c.integer(field, 'Поверх', 1, 99, required=False)
    if c.errors:
        raise ValidationError(c.errors)
    return floors
