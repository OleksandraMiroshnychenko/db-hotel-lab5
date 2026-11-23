import sqlalchemy as sa
from sqlalchemy import orm

from .base import myBase


class Room(myBase):
    """Фізичний номер готелю."""

    __tablename__ = 'rooms'

    room_id = sa.Column(sa.Integer, sa.Identity(always=True), primary_key=True)
    room_number = sa.Column(sa.Integer, nullable=False)
    floor = sa.Column(sa.Integer, nullable=False)
    phone = sa.Column(sa.Text, nullable=False)
    room_type_id = sa.Column(sa.Integer, sa.ForeignKey('room_types.room_type_id'),
                             nullable=False)

    room_type = orm.relationship('RoomType', back_populates='rooms')
    stays = orm.relationship('Stay', back_populates='room')
