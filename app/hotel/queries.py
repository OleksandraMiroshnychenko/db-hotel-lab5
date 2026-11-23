"""Запити з варіанта завдання (ті самі, що в лабораторній роботі 3), виконані засобами ORM.

Запит 1. Клієнти, які проживають у заданому номері.
Запит 2. Клієнти, які прибули із заданого міста.
Запит 3. Службовець, який прибирав номер вказаного клієнта у заданий день тижня.
Запит 4. Чи є вільні номери й вільні місця, і скільки.
"""
from sqlalchemy import and_, func, select

from .models import Client, CleaningSchedule, Employee, Room, RoomType, Stay


def room_clients(session, room_number):
    """Запит 1: клієнти, які проживають у номері зараз (дата виселення порожня)."""
    stmt = (
        select(Client, Stay.checkin_date)
        .join(Client.stays)
        .join(Stay.room)
        .where(Room.room_number == room_number,
               Stay.checkout_date.is_(None))
        .order_by(Client.last_name)
    )
    return [{'client': c, 'checkin_date': d} for c, d in session.execute(stmt).all()]


def city_clients(session, city):
    """Запит 2: клієнти із заданого міста."""
    stmt = select(Client).where(Client.city == city).order_by(Client.last_name)
    return list(session.scalars(stmt).all())


def room_cleaner(session, passport_number, weekday):
    """Запит 3: хто зі службовців прибирав номер клієнта у заданий день тижня.

    Прямого звʼязку між номером і графіком прибирання немає: вони збігаються за
    поверхом. Ланцюжок: клієнт -> проживання -> номер -> (той самий поверх) ->
    графік прибирання -> службовець. Береться номер, у якому клієнт проживає зараз.
    """
    stmt = (
        select(Employee, CleaningSchedule.floor, Room.room_number)
        .select_from(Client)
        .join(Client.stays)
        .join(Stay.room)
        .join(CleaningSchedule, CleaningSchedule.floor == Room.floor)
        .join(Employee, Employee.employee_id == CleaningSchedule.employee_id)
        .where(Client.passport_number == passport_number,
               CleaningSchedule.weekday == weekday,
               Stay.checkout_date.is_(None))
        .distinct()
    )
    return [{'employee': e, 'floor': f, 'room_number': n}
            for e, f, n in session.execute(stmt).all()]


def availability(session):
    """Запит 4: кількість вільних номерів і вільних місць, а також заповненість номерів.

    Номер вільний, якщо в ньому немає поточних проживань. Вільні місця - різниця
    між місткістю й кількістю тих, хто проживає зараз, тому враховуються й
    частково зайняті номери. Заповненість рахує підзапит (CTE occupancy);
    outerjoin зберігає порожні номери.
    """
    occupancy = (
        select(Room.room_number,
               RoomType.name.label('type_name'),
               RoomType.capacity,
               func.count(Stay.stay_id).label('occupied'))
        .select_from(Room)
        .join(Room.room_type)
        .outerjoin(Stay, and_(Stay.room_id == Room.room_id,
                              Stay.checkout_date.is_(None)))
        .group_by(Room.room_number, RoomType.name, RoomType.capacity)
        .cte('occupancy')
    )
    summary = select(
        func.count().filter(occupancy.c.occupied == 0).label('free_rooms'),
        func.coalesce(func.sum(occupancy.c.capacity - occupancy.c.occupied), 0)
        .label('free_places'),
    )
    row = session.execute(summary).one()
    rooms = session.execute(
        select(occupancy).order_by(occupancy.c.room_number)).mappings().all()
    return {'free_rooms': int(row.free_rooms), 'free_places': int(row.free_places),
            'rooms': [dict(r) for r in rooms]}
