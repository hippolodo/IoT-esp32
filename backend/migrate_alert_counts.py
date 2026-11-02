"""Create the persistent counter table without changing existing measurements."""
from app.config import Settings
from app.database import make_database
from app.models import AlertCount, AlertHistoryDetail
from sqlalchemy import inspect, text


def migrate():
    engine, _ = make_database(Settings().database_url)
    try:
        AlertCount.__table__.create(engine, checkfirst=True)
        AlertHistoryDetail.__table__.create(engine, checkfirst=True)
        columns = {row['name'] for row in inspect(engine).get_columns('alert_history_details')}
        with engine.begin() as connection:
            for name in ('trigger_value', 'trigger_threshold'):
                if name not in columns:
                    connection.execute(text(f'ALTER TABLE alert_history_details ADD COLUMN {name} DOUBLE NULL'))
        print('Persistent alert counter and history tables are ready.')
    finally:
        engine.dispose()


if __name__ == '__main__':
    migrate()
