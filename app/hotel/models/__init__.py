"""Моделі ORM: по одній на таблицю бази даних «Готель»."""
from .base import myBase
from .room_type import RoomType
from .room import Room
from .client import Client
from .stay import Stay
from .employee import Employee
from .cleaning_schedule import CleaningSchedule

__all__ = ['myBase', 'RoomType', 'Room', 'Client', 'Stay', 'Employee', 'CleaningSchedule']
