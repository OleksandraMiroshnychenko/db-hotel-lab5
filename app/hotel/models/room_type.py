import sqlalchemy as sa
from sqlalchemy import orm

from .base import myBase


class RoomType(myBase):
    """Тип номера: одномісний / двомісний / тримісний."""

    __tablename__ = 'room_types'

    room_type_id = sa.Column(sa.Integer, sa.Identity(always=True), primary_key=True)
    name = sa.Column(sa.Text, nullable=False)
    capacity = sa.Column(sa.Integer, nullable=False)
    price_per_day = sa.Column(sa.Numeric(10, 2), nullable=False)

    rooms = orm.relationship('Room', back_populates='room_type')
