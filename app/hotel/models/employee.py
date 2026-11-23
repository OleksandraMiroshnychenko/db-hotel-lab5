import sqlalchemy as sa
from sqlalchemy import orm

from .base import myBase


class Employee(myBase):
    """Службовець готелю."""

    __tablename__ = 'employees'

    employee_id = sa.Column(sa.Integer, sa.Identity(always=True), primary_key=True)
    last_name = sa.Column(sa.Text, nullable=False)
    first_name = sa.Column(sa.Text, nullable=False)
    patronymic = sa.Column(sa.Text)

    cleaning_days = orm.relationship('CleaningSchedule', back_populates='employee',
                                     passive_deletes=True,
                                     order_by='CleaningSchedule.weekday')

    @property
    def full_name(self):
        """Повне імʼя службовця: прізвище, імʼя, по батькові."""
        parts = [self.last_name, self.first_name, self.patronymic]
        return ' '.join(p for p in parts if p)
