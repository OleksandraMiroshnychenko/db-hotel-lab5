import sqlalchemy as sa
from sqlalchemy import orm

from .base import myBase


class Stay(myBase):
    """Проживання клієнта в номері. Порожня дата виселення: клієнт проживає зараз."""

    __tablename__ = 'stays'

    stay_id = sa.Column(sa.Integer, sa.Identity(always=True), primary_key=True)
    client_id = sa.Column(sa.Integer, sa.ForeignKey('clients.client_id', ondelete='CASCADE'),
                          nullable=False)
    room_id = sa.Column(sa.Integer, sa.ForeignKey('rooms.room_id'), nullable=False)
    checkin_date = sa.Column(sa.Date, nullable=False)
    checkout_date = sa.Column(sa.Date)

    client = orm.relationship('Client', back_populates='stays')
    room = orm.relationship('Room', back_populates='stays')
