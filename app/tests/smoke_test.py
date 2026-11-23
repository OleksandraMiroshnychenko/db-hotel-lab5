"""Наскрізна перевірка веб-додатку: проходить основні сценарії через HTTP.

Запуск (додаток і база мають працювати):
    python tests/smoke_test.py                       # http://localhost:8088, як у Docker
    APP_URL=http://localhost:8085 python tests/smoke_test.py

Скрипт змінює дані, але наприкінці прибирає за собою (видаляє створені записи),
тож його можна запускати повторно, у тому числі після python -m hotel.seed.
Потрібна база з початковими даними лабораторної роботи 4 (номери 101-302).
"""
import http.cookiejar
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from html import unescape

BASE = os.environ.get('APP_URL', 'http://localhost:8088').rstrip('/')

opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

passed = 0
failed = []


def request(path, data=None):
    """Виконує GET (data=None) або POST; повертає текст сторінки після переходів."""
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    try:
        # кирилицю в адресі потрібно закодувати (%XX), інші символи лишаються як є
        url = BASE + urllib.parse.quote(path, safe="/?=&%:")
        with opener.open(url, body, timeout=20) as response:
            return unescape(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        return unescape(exc.read().decode('utf-8'))


def check(name, condition):
    """Рахує перевірку: ok, якщо умова виконана, інакше запамʼятовує назву невдалої."""
    global passed
    if condition:
        passed += 1
        print(f'  ok   {name}')
    else:
        failed.append(name)
        print(f'  FAIL {name}')


def has(page, text):
    """Чи містить сторінка вказаний текст."""
    return text in page


def flash_ok(page):
    """Чи показано на сторінці повідомлення про успіх."""
    return 'class="flash ok"' in page


def flash_error(page):
    """Чи показано на сторінці повідомлення про помилку."""
    return 'class="flash error"' in page


def row_id(page, pattern):
    """Знаходить у сторінці перше число за шаблоном (наприклад, id запису в посиланні)."""
    found = re.search(pattern, page)
    return int(found.group(1)) if found else None


today = date.today()
iso = lambda d: d.isoformat()

print('Сторінки відкриваються')
for path in ['/', '/rooms', '/room-types', '/clients', '/stays', '/stays?scope=all',
             '/employees', '/queries', '/stays/check-in', '/rooms/new', '/clients/new']:
    check(f'GET {path}', has(request(path), '<main class="page">'))

print('Клієнти: додавання, перевірка даних, унікальність')
page = request('/clients/new', {'passport_number': 'ek 910001', 'last_name': 'смоук',
                                'first_name': 'тест-ірина', 'city': 'київ'})
check('клієнта додано, дані нормалізовано', flash_ok(page) and 'Смоук Тест-Ірина' in page)
page = request('/clients/new', {'passport_number': 'ЕК910001', 'last_name': 'Дубль',
                                'first_name': 'Тест', 'city': 'Київ'})
check('повторний паспорт відхилено', flash_error(page) and 'вже є в базі' in page)
page = request('/clients/new', {'passport_number': '12', 'last_name': 'Х1', 'first_name': '',
                                'city': 'К'})
check('некоректні дані відхилено з поясненнями',
      has(page, 'Паспорт: дві літери') and has(page, 'Прізвище: лише літери')
      and has(page, 'Імʼя: обовʼязкове поле'))
client_id = row_id(request('/clients?q=ЕК910001'), r'/clients/(\d+)"')
check('клієнт знайдений пошуком', client_id is not None)

print('Заселення та виселення (процедури check_in, check_out)')
page = request('/stays/check-in', {'passport_number': 'ЕК910001', 'room_number': '102',
                                   'checkin_date': iso(today)})
check('існуючого клієнта поселено', flash_ok(page) and has(page, 'поселено в номер 102'))
page = request('/stays/check-in', {'passport_number': 'ЕК910002', 'room_number': '102',
                                   'checkin_date': iso(today), 'last_name': 'Другий',
                                   'first_name': 'Гість', 'city': 'Львів'})
check('номер 102 заповнений: тригер місткості відхилив заселення',
      flash_error(page) and has(page, 'заповнений'))
check('при невдалому заселенні новий клієнт не створився',
      not has(request('/clients?q=ЕК910002'), 'Другий'))
page = request('/stays/check-in', {'passport_number': 'ЕК910003', 'room_number': '103',
                                   'checkin_date': iso(today)})
check('новий клієнт без імені відхилено', has(page, 'потрібне для нового клієнта'))
page = request('/stays/check-in', {'passport_number': 'ЕК910003', 'room_number': '999',
                                   'checkin_date': iso(today), 'last_name': 'Тест',
                                   'first_name': 'Тест', 'city': 'Київ'})
check('неіснуючий номер відхилено', flash_error(page) and has(page, 'Номера 999 у готелі немає'))
page = request('/stays/check-in', {'passport_number': 'ЕК910001', 'room_number': '103',
                                   'checkin_date': iso(today + timedelta(days=3))})
check('дата в майбутньому відхилена', has(page, 'не може бути в майбутньому'))
check('запит 1 бачить клієнта в номері 102', has(request('/queries?room=102'), 'Смоук'))

stays_page = request('/stays?q=910001')
stay_id = row_id(stays_page, r'/stays/(\d+)/check-out')
check('проживання з\'явилось у списку', stay_id is not None)
page = request(f'/stays/{stay_id}/check-out', {'checkout_date': iso(today - timedelta(days=5)),
                                                'back': '/stays'})
check('виселення раніше за заселення відхилено', flash_error(page) and has(page, 'раніша'))
page = request(f'/stays/{stay_id}/check-out', {'checkout_date': iso(today), 'back': '/stays'})
check('клієнта виселено', flash_ok(page) and has(page, 'виселено з номера 102'))
page = request(f'/stays/{stay_id}/check-out', {'checkout_date': iso(today), 'back': '/stays'})
check('повторне виселення відхилено', flash_error(page) and has(page, 'вже завершено'))

print('Зміна проживання: тригер перетину періодів')
page = request('/stays?scope=all&q=ЕК456789')
other = row_id(page, r'/stays/(\d+)/edit')
check('знайдено проживання для перевірки', other is not None)
# клієнт 910001 уже має проживання в 102; додаємо ще одне, що перетинається за датами
request('/stays/check-in', {'passport_number': 'ЕК910001', 'room_number': '202',
                            'checkin_date': iso(today - timedelta(days=2))})
page = request('/stays/check-in', {'passport_number': 'ЕК910001', 'room_number': '203',
                                   'checkin_date': iso(today - timedelta(days=1))})
check('перетин періодів проживання відхилено тригером',
      flash_error(page) and has(page, 'перетинається'))

print('Типи номерів і номери')
# у номері 201 (двомісний) уже проживає один клієнт; селимо другого й пробуємо зменшити місткість
request('/stays/check-in', {'passport_number': 'ЕК910001', 'room_number': '201',
                            'checkin_date': iso(today - timedelta(days=30))})
type_id = row_id(request('/room-types'), r'двомісний</strong></td>(?:.|\n)*?/room-types/(\d+)/edit')
page = request(f'/room-types/{type_id}/edit', {'name': 'двомісний', 'capacity': '1',
                                                'price_per_day': '1300'})
check('зменшити місткість нижче кількості мешканців не можна (тригер)',
      flash_error(page) and has(page, 'Не можна зменшити місткість'))
page = request(f'/room-types/{type_id}/edit', {'name': 'двомісний', 'capacity': '2',
                                                'price_per_day': '1350.50'})
check('ціну типу змінено', flash_ok(page) and has(page, '1 350.50 грн'))
request(f'/room-types/{type_id}/edit', {'name': 'двомісний', 'capacity': '2',
                                         'price_per_day': '1300'})
page = request('/room-types/new', {'name': 'тест', 'capacity': '5', 'price_per_day': '-1'})
check('некоректний тип відхилено', has(page, 'Місткість: число від 1 до 3')
      and has(page, 'Ціна за добу'))
page = request('/rooms/new', {'room_number': '401', 'floor': '3', 'phone': '123',
                              'room_type_id': '1'})
check('номер на неправильному поверсі відхилено',
      has(page, 'має бути на поверсі 4') and has(page, 'Телефон: формат'))
page = request('/rooms/new', {'room_number': '401', 'floor': '4', 'phone': '044 123-45-99',
                              'room_type_id': '1'})
check('номер 401 додано', flash_ok(page) and has(page, '401'))
page = request('/rooms/new', {'room_number': '401', 'floor': '4', 'phone': '+380441234599',
                              'room_type_id': '1'})
check('дубль номера кімнати відхилено', has(page, 'вже існує'))
room_401 = row_id(request('/rooms'), r'/rooms/(\d+)/edit">Змінити</a>\s*<form[^>]*delete[^>]*onsubmit="return confirm\(\'Видалити номер 401')
check('знайдено id номера 401', room_401 is not None)
page = request('/rooms/1/delete', {})
check('номер з історією не видаляється', flash_error(page) and has(page, 'історія проживань'))
page = request(f'/rooms/{room_401}/delete', {})
check('номер 401 видалено', flash_ok(page))

print('Службовці та графік (процедури hire_employee, change_schedule, fire_employee)')
page = request('/employees/new', {'last_name': 'смоук', 'first_name': 'службовець'})
check('службовця прийнято', flash_ok(page) and has(page, 'прийнято на роботу'))
emp = row_id(request('/employees'), r'Смоук Службовець</strong></td>(?:.|\n)*?/employees/(\d+)/schedule')
check('службовця знайдено', emp is not None)
page = request(f'/employees/{emp}/schedule', {'floor_1': '1', 'floor_2': '9'})
check('неіснуючий поверх відхилено тригером', flash_error(page) and has(page, 'немає поверху 9'))
check('графік не змінився (транзакція скасована)',
      'value="1"' not in request(f'/employees/{emp}/schedule').split('floor_1')[1][:80])
page = request(f'/employees/{emp}/schedule', {'floor_1': '1', 'floor_3': '2'})
check('графік змінено', flash_ok(page) and has(page, 'змінено днів: 2'))
page = request(f'/employees/{emp}/delete', {})
check('службовця звільнено, графік видалено', flash_ok(page) and has(page, 'видалено записів графіка: 2'))

print('Запити з варіанта')
page = request('/queries?room=101&city=Харків&passport=ЕК456789&weekday=3')
check('запит 1: у номері 101 проживає Мельник', has(page, 'Мельник Дмитро'))
check('запит 2: із Харкова', has(page, 'Коваленко Олена'))
check('запит 3: прибирала Даниленко', has(page, 'Даниленко Юлія'))
check('запит 4: вільні номери та місця', has(page, 'вільних номерів') and has(page, 'вільних місць'))
page = request('/queries?room=abc&weekday=9')
check('некоректні параметри запитів пояснені', has(page, 'потрібне ціле число')
      and has(page, 'число від 1 до 7'))

print('Прибирання')
request(f'/clients/{client_id}/delete', {})
check('клієнта видалено разом з історією',
      not has(request('/clients?q=ЕК910001'), 'Смоук'))

print()
print(f'Пройдено перевірок: {passed}, не пройдено: {len(failed)}')
for name in failed:
    print('  -', name)
sys.exit(1 if failed else 0)
