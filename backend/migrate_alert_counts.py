"""Create the persistent counter table without changing existing measurements."""
from app.config import Settings
from app.database import make_database
from app.models import AlertCount, AlertHistoryDetail
from app.contracts import now, execute_sql
from sqlalchemy import inspect, text


# Tạo bảng cần thiết và dựng lại tổng từ lịch sử đã ghi, không xóa lịch sử hoặc số đo.
def migrate(settings=None):
    settings = settings or Settings()
    engine, sessions = make_database(settings.database_url)
    try:
        AlertCount.__table__.create(engine, checkfirst=True)
        AlertHistoryDetail.__table__.create(engine, checkfirst=True)
        columns = {row['name'] for row in inspect(engine).get_columns('alert_history_details')}
        with engine.begin() as connection:
            for name in ('trigger_value', 'trigger_threshold'):
                if name not in columns:
                    connection.execute(text(f'ALTER TABLE alert_history_details ADD COLUMN {name} DOUBLE NULL'))
        # Không giữ các lần đếm offline không có lịch sử của firmware cũ.
        with sessions.begin() as db:
            for device_id, led in settings.device_map.items():
                row = execute_sql(db, """
                    SELECT COALESCE(SUM(a.occurrence_count), 0) AS total
                    FROM histories AS h
                    JOIN alert_history_details AS a ON a.history_id = h.id
                    WHERE h.device_id = :device_id AND h.action = 'ALERT' AND h.status = 'RECORDED'
                """, {'device_id': device_id}).mappings().one()
                params = {'led': led, 'total': int(row['total']), 'updated_at': now()}
                if db.bind.dialect.name == 'mysql':
                    sql = """INSERT INTO alert_counts (led, total, updated_at)
                             VALUES (:led, :total, :updated_at)
                             ON DUPLICATE KEY UPDATE total = VALUES(total), updated_at = VALUES(updated_at)"""
                else:
                    sql = """INSERT INTO alert_counts (led, total, updated_at)
                             VALUES (:led, :total, :updated_at)
                             ON CONFLICT(led) DO UPDATE SET total = excluded.total, updated_at = excluded.updated_at"""
                execute_sql(db, sql, params)
        print('Alert tables are ready; totals rebuilt from recorded history.')
    finally:
        engine.dispose()


if __name__ == '__main__':
    migrate()
