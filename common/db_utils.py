from __future__ import annotations

from typing import Any

try:
    import pymysql
except ModuleNotFoundError:  # pragma: no cover - DB checks are optional
    pymysql = None


class DBUtils:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.enabled = bool(config.get("enabled", False))
        self.conn: Any | None = None

    def connect(self) -> Any:
        if not self.enabled:
            raise RuntimeError("Database validation is disabled in current config.")
        if pymysql is None:
            raise RuntimeError("pymysql is not installed. Install requirements.txt before enabling DB checks.")
        if self.conn is None:
            self.conn = pymysql.connect(
                host=self.config["host"],
                port=int(self.config.get("port", 3306)),
                user=self.config["user"],
                password=self.config["password"],
                database=self.config["database"],
                charset="utf8mb4",
                autocommit=True,
                cursorclass=pymysql.cursors.DictCursor,
            )
        return self.conn

    def query_one(self, sql: str, params: list[Any] | tuple[Any, ...] | None = None) -> dict[str, Any] | None:
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()

    def query_all(self, sql: str, params: list[Any] | tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return list(cursor.fetchall())

    def execute(self, sql: str, params: list[Any] | tuple[Any, ...] | None = None) -> int:
        conn = self.connect()
        with conn.cursor() as cursor:
            return cursor.execute(sql, params)

    def cleanup_ota_test_data(self, prefix: str = "TEST_") -> None:
        if not self.enabled:
            return
        self.execute("delete from operation_log where device_id like %s", [f"{prefix}%"])
        self.execute("delete from ota_task where device_id like %s", [f"{prefix}%"])

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None
