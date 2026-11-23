"""Додаткові тестові дані для демонстрації додатку.

Запуск (з папки app):   python -m hotel.seed
У Docker:               docker exec -it lab5-app-1 python -m hotel.seed

Скрипт додає клієнтів, їхні проживання в різні періоди й нових службовців з
графіком прибирання. Усе робиться тими самими збереженими процедурами, що й
у додатку (check_in, check_out, hire_employee, change_schedule), тож тригери
цілісності й кешу перевіряють ці дані так само, як дані користувача.

Дати рахуються від сьогоднішнього дня, тому «поточні» проживання завжди свіжі.
Повторний запуск нічого не дублює. Кімнати й паспорти, які використовують
демонстраційні скрипти лабораторної роботи 4 (номери 101, 102, 201, 203, 401),
не чіпаються.
"""
from datetime import date, timedelta

from sqlalchemy import text

from .db import transaction

# (паспорт, прізвище, імʼя, по батькові, місто)
NEW_CLIENTS = {
    'ЕК810001': ('Петренко', 'Оксана', 'Миколаївна', 'Київ'),
    'ЕК810002': ('Мазур', 'Богдан', 'Іванович', 'Львів'),
    'ЕК810003': ('Яценко', 'Ірина', 'Андріївна', 'Одеса'),
    'ЕК810004': ('Руденко', 'Тарас', 'Олегович', 'Харків'),
    'ЕК810005': ('Остапенко', 'Лілія', 'Сергіївна', 'Київ'),
    'ЕК810006': ('Кузьменко', 'Артем', 'Вікторович', 'Дніпро'),
    'ЕК810007': ('Левченко', 'Марина', 'Олексіївна', 'Харків'),
    'ЕК810008': ('Гриценко', 'Павло', 'Андрійович', 'Київ'),
    'ЕК810009': ('Савчук', 'Оксана', 'Тарасівна', 'Львів'),
    'ЕК810010': ('Ковальчук', 'Дмитро', 'Ігорович', 'Харків'),
    'ЕК810011': ('Бойко', 'Наталія', 'Василівна', 'Дніпро'),
}

# (паспорт, номер кімнати, днів тому заселено, днів тому виселено або None, якщо живе зараз)
STAYS = [
    ('ЕК810001', 103, 58, 54),
    ('ЕК810002', 302, 50, 46),
    ('ЕК810003', 202, 44, 41),
    ('ЕК810004', 301, 40, 37),
    ('ЕК810005', 103, 35, 30),
    ('ЕК810006', 302, 28, 24),
    ('ЕК810007', 103, 22, 19),
    ('ЕК234567', 302, 15, 12),      # існуючий клієнт приїздить повторно
    ('ЕК810008', 302, 6, None),
    ('ЕК810009', 103, 3, None),
    ('ЕК810010', 103, 2, None),
    ('ЕК810011', 301, 1, None),
]

# (прізвище, імʼя, по батькові, {день тижня: поверх})
NEW_EMPLOYEES = [
    ('Іваненко', 'Галина', 'Петрівна', {1: 1, 3: 3, 5: 2}),
    ('Бондар', 'Микола', 'Степанович', {2: 2, 4: 3, 6: 1}),
    ('Ткачук', 'Світлана', 'Юріївна', {1: 3, 3: 2, 7: 1}),
]


def exists(session, sql, params):
    """Чи повертає запит хоча б один рядок."""
    return session.execute(text(sql), params).first() is not None


def seed():
    """Додає демонстраційні дані (клієнтів, проживання, службовців); повторний запуск нічого не змінює."""
    today = date.today()

    with transaction() as tx:
        if exists(tx.session, 'SELECT 1 FROM clients WHERE passport_number = :p',
                  {'p': 'ЕК810001'}):
            print('Демо-дані вже додано, нічого не змінено.')
            return

    for passport, room, came, left in STAYS:
        names = NEW_CLIENTS.get(passport)
        # кожне заселення й виселення - окрема транзакція, як і в додатку
        with transaction() as tx:
            tx.session.execute(
                text('CALL check_in(:passport, :room, :date, :last_name, :first_name, '
                     ':patronymic, :city)'),
                {'passport': passport, 'room': room, 'date': today - timedelta(days=came),
                 'last_name': names[0] if names else None,
                 'first_name': names[1] if names else None,
                 'patronymic': names[2] if names else None,
                 'city': names[3] if names else None})
        if left is not None:
            with transaction() as tx:
                tx.session.execute(text('CALL check_out(:passport, :date)'),
                                   {'passport': passport, 'date': today - timedelta(days=left)})
        print(f'Проживання: {passport}, номер {room}, '
              f'{"виселено" if left is not None else "проживає зараз"}')

    for last_name, first_name, patronymic, schedule in NEW_EMPLOYEES:
        with transaction() as tx:
            employee_id = tx.session.execute(
                text('CALL hire_employee(:l, :f, :p, NULL)'),
                {'l': last_name, 'f': first_name, 'p': patronymic}).scalar_one()
        for weekday, floor in schedule.items():
            with transaction() as tx:
                tx.session.execute(text('CALL change_schedule(:e, :d, :f)'),
                                   {'e': employee_id, 'd': weekday, 'f': floor})
        print(f'Службовець: {last_name} {first_name}, графік з {len(schedule)} днів')

    print('Демо-дані додано.')


if __name__ == '__main__':
    seed()
