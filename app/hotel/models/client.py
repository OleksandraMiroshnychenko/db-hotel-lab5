import sqlalchemy as sa
from sqlalchemy import orm

from .base import myBase


class Client(myBase):
    """Клієнт готелю."""

    __tablename__ = 'clients'

    client_id = sa.Column(sa.Integer, sa.Identity(always=True), primary_key=True)
    passport_number = sa.Column(sa.Text, nullable=False)
    last_name = sa.Column(sa.Text, nullable=False)
    first_name = sa.Column(sa.Text, nullable=False)
    patronymic = sa.Column(sa.Text)
    city = sa.Column(sa.Text, nullable=False)

    # passive_deletes: каскадне видалення проживань виконує сама база (ON DELETE CASCADE)
    stays = orm.relationship('Stay', back_populates='client', passive_deletes=True)

    @property
    def full_name(self):
        """Повне імʼя клієнта: прізвище, імʼя, по батькові."""
        parts = [self.last_name, self.first_name, self.patronymic]
        return ' '.join(p for p in parts if p)
