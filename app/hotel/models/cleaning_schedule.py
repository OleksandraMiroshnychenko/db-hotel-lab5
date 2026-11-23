import sqlalchemy as sa
from sqlalchemy import orm

from .base import myBase


class CleaningSchedule(myBase):
    """Графік прибирання: який поверх службовець прибирає у вказаний день тижня."""

    __tablename__ = 'cleaning_schedule'

    employee_id = sa.Column(sa.Integer,
                            sa.ForeignKey('employees.employee_id', ondelete='CASCADE'),
                            primary_key=True)
    weekday = sa.Column(sa.SmallInteger, primary_key=True)
    floor = sa.Column(sa.Integer, nullable=False)

    employee = orm.relationship('Employee', back_populates='cleaning_days')
