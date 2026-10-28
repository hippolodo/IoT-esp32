"""Sensor catalog, measurements and chart history using parameterized SQL."""
from sqlalchemy.orm import Session
from ..contracts import data_dict, execute_sql, paginate, parse_date, sensor_dict, time_range

MEASUREMENTS_SQL = """
    SELECT ds.id, ds.sensor_id, ds.value, ds.recorded_at,
           s.name AS sensor_name, s.type AS sensor_type, s.unit
    FROM datasensors AS ds
    JOIN sensors AS s ON s.id = ds.sensor_id
"""


def sensors(db: Session):
    rows = execute_sql(db, "SELECT * FROM sensors WHERE UPPER(type) IN ('TEMPERATURE', 'HUMIDITY', 'LIGHT') ORDER BY id ASC").mappings().all()
    return [sensor_dict(row) for row in rows]


def latest(db: Session):
    rows = execute_sql(db, MEASUREMENTS_SQL + """
        WHERE UPPER(s.type) IN ('TEMPERATURE', 'HUMIDITY', 'LIGHT') AND ds.id = (
            SELECT newest.id FROM datasensors AS newest
            WHERE newest.sensor_id = s.id
            ORDER BY newest.recorded_at DESC, newest.id DESC LIMIT 1
        )
        ORDER BY ds.recorded_at DESC, ds.id DESC
    """).mappings().all()
    return [data_dict(row) for row in rows]


def sensor_chart(db: Session, limit: int = 30):
    if not 1 <= limit <= 30:
        raise ValueError("limit phải từ 1 đến 30")
    keys = {'TEMPERATURE': 'temperature', 'HUMIDITY': 'humidity',
            'LIGHT': 'light'}
    # One point per second, with up to three readings, oldest to newest.
    rows = execute_sql(db, """
        SELECT ds.value, s.type AS sensor_type,
               SUBSTR(CAST(ds.recorded_at AS CHAR), 1, 19) AS sample_time
        FROM datasensors AS ds
        JOIN sensors AS s ON s.id = ds.sensor_id
        JOIN (
            SELECT SUBSTR(CAST(d.recorded_at AS CHAR), 1, 19) AS sample_time
            FROM datasensors AS d
            JOIN sensors AS sensor ON sensor.id = d.sensor_id
            WHERE d.recorded_at IS NOT NULL
              AND UPPER(sensor.type) IN ('TEMPERATURE', 'HUMIDITY', 'LIGHT')
            GROUP BY SUBSTR(CAST(d.recorded_at AS CHAR), 1, 19)
            ORDER BY sample_time DESC
            LIMIT :limit
        ) AS recent ON recent.sample_time = SUBSTR(CAST(ds.recorded_at AS CHAR), 1, 19)
        WHERE UPPER(s.type) IN ('TEMPERATURE', 'HUMIDITY', 'LIGHT')
        ORDER BY ds.recorded_at ASC, ds.id ASC
    """, {'limit': limit}).mappings().all()
    points = {}
    for row in rows:
        point = points.setdefault(row['sample_time'], {'time': row['sample_time']})
        point[keys[row['sensor_type'].upper()]] = row['value']
    return list(points.values())


def sensor_data(
    db: Session,
    sensorId: int | None = None,
    startTime: str | None = None,
    endTime: str | None = None,
    page: int = 0,
    size: int = 10,
    sensorType: str | None = None,
    value: str | None = None,
):
    start, end = time_range(startTime, endTime)
    sql = MEASUREMENTS_SQL + " WHERE UPPER(s.type) IN ('TEMPERATURE', 'HUMIDITY', 'LIGHT')"
    params = {}
    if sensorId is not None:
        sql += ' AND ds.sensor_id = :sensor_id'
        params['sensor_id'] = sensorId
    if sensorType:
        sql += ' AND UPPER(s.type) = :sensor_type'
        params['sensor_type'] = sensorType.upper()
    if value:
        sql += " AND CAST(ds.value AS CHAR) LIKE :value ESCAPE '!'"
        params['value'] = '%' + value.replace('!', '!!').replace('%', '!%').replace('_', '!_') + '%'
    if start:
        sql += ' AND ds.recorded_at >= :start AND ds.recorded_at < :end'
        params.update(start=start, end=end)
    sql += ' ORDER BY ds.recorded_at DESC, ds.id DESC'
    return paginate(db, sql, params, page, size, data_dict)


def filter_sensors(
    db: Session, type: str, startDate: str, endDate: str, page: int = 0, size: int = 10,
):
    start, end = parse_date(startDate), parse_date(endDate)
    if start > end:
        raise ValueError("startDate phải nhỏ hơn hoặc bằng endDate")
    sql = MEASUREMENTS_SQL + """
        WHERE s.type = :sensor_type AND UPPER(s.type) IN ('TEMPERATURE', 'HUMIDITY', 'LIGHT')
          AND ds.recorded_at >= :start AND ds.recorded_at <= :end
        ORDER BY ds.recorded_at DESC, ds.id DESC
    """
    return paginate(db, sql, {'sensor_type': type, 'start': start, 'end': end}, page, size, data_dict)
