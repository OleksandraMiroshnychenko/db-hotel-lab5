"""Підключення до бази даних і керування транзакціями."""
import logging
import os
import threading
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# рядок підключення береться зі змінної середовища (у Docker її задає docker-compose);
# значення за замовчуванням - база з docker-compose, відкрита на порту 8432
DATABASE_URL = os.environ.get(
    'DATABASE_URL', 'postgresql+psycopg2://root:password@localhost:8432/hotel')

# pool_pre_ping перевіряє зʼєднання перед використанням: після перезапуску бази
# додаток не падає, а відкриває нове зʼєднання
engine = create_engine(DATABASE_URL, pool_pre_ping=True,
                       echo=bool(os.environ.get('SQL_ECHO')))

# expire_on_commit=False: обʼєкти лишаються придатними для читання після commit
Session = sessionmaker(bind=engine, expire_on_commit=False)


class NoticeCollector(logging.Handler):
    """Збирає повідомлення бази (RAISE NOTICE, RAISE WARNING).

    Драйвер psycopg2 отримує їх у списку connection.notices, але SQLAlchemy після
    кожного запиту очищає цей список, пересилаючи повідомлення в журнал
    sqlalchemy.dialects.postgresql. Цей обробник перехоплює їх там.
    """

    def __init__(self):
        """Створює обробник; список повідомлень зберігається окремо для кожного потоку."""
        super().__init__(level=logging.INFO)
        self._local = threading.local()

    def start(self):
        """Починає збирати повідомлення поточного потоку."""
        self._local.items = []

    def stop(self):
        """Припиняє збір і повертає зібрані повідомлення."""
        items = getattr(self._local, 'items', None) or []
        self._local.items = None
        return items

    def emit(self, record):
        """Додає повідомлення до списку, якщо збір у цьому потоці почато."""
        items = getattr(self._local, 'items', None)
        if items is not None:
            items.append(record.getMessage())


_collector = NoticeCollector()
_pg_logger = logging.getLogger('sqlalchemy.dialects.postgresql')
_pg_logger.setLevel(logging.INFO)
_pg_logger.addHandler(_collector)
_pg_logger.propagate = False   # у консоль ці повідомлення не виводяться


class Transaction:
    """Одна транзакція: сесія SQLAlchemy та повідомлення (NOTICE/WARNING) від бази."""

    def __init__(self, session):
        """Запамʼятовує сесію; notices заповнюються після commit."""
        self.session = session
        self.notices = []


@contextmanager
def transaction():
    """Виконує блок коду в одній транзакції.

    Усе, що зроблено всередині блоку, або фіксується разом (commit), або
    скасовується повністю (rollback), якщо виникла будь-яка помилка. Важливо, що
    commit виконується тут, а не пізніше: відкладені тригери оновлення кешу
    спрацьовують саме під час commit, і їхні помилки теж потрапляють у цей блок.
    """
    session = Session()
    # connection() відкриває транзакцію й повертає зʼєднання з базою
    dbapi = session.connection().connection.dbapi_connection
    # повідомлення, що лишились від попередніх запитів на цьому зʼєднанні, не потрібні
    del dbapi.notices[:]
    _collector.start()
    tx = Transaction(session)
    try:
        yield tx
        session.commit()
        # повідомлення, які база надіслала під час самого COMMIT (відкладені тригери кешу),
        # SQLAlchemy не очищає, тому їх беремо напряму
        commit_notices = list(dbapi.notices)
        del dbapi.notices[:]
        tx.notices = _collector.stop() + commit_notices
    except Exception:
        _collector.stop()
        session.rollback()
        raise
    finally:
        session.close()
