"""Wind alert statistics and per-day queries using parameterized SQL."""
import calendar
import re
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..contracts import date_string, execute_sql, paginate


def wind_summary(db: Session, month: str):
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        raise ValueError("Tháng phải theo YYYY-MM")
    start = datetime.strptime(month, "%Y-%m")
    count_days = calendar.monthrange(start.year, start.month)[1]
    end = start + timedelta(days=count_days)
    rows = execute_sql(db, """
        SELECT DATE(recorded_at) AS day, COUNT(*) AS total
        FROM WindSpeed
        WHERE recorded_at >= :start AND recorded_at < :end
        GROUP BY DATE(recorded_at)
    """, {'start': start, 'end': end}).mappings().all()
    counts = {str(row['day']): row['total'] for row in rows}
    days = [{"date": (start + timedelta(days=i)).strftime("%Y-%m-%d"),
             "count": counts.get((start + timedelta(days=i)).strftime("%Y-%m-%d"), 0)}
            for i in range(count_days)]
    return {"month": month, "threshold": 300, "total": sum(d["count"] for d in days), "days": days}


def wind_alerts(db: Session, date: str, page: int = 0, size: int = 10):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise ValueError("Ngày phải theo YYYY-MM-DD")
    start = datetime.strptime(date, "%Y-%m-%d")
    sql = """
        SELECT id, speed, recorded_at FROM WindSpeed
        WHERE recorded_at >= :start AND recorded_at < :end
        ORDER BY recorded_at DESC, id DESC
    """
    return paginate(db, sql, {'start': start, 'end': start + timedelta(days=1)}, page, size, lambda row: {
        "id": row['id'], "speed": row['speed'], "recordedAt": date_string(row['recorded_at']),
    })
