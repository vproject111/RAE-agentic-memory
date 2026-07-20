import json

import mysql.connector


class ScreenWatcherBridge:
    def __init__(self):
        self.config = {
            "user": "screenwatcher",
            "password": "password",
            "host": "screenwatcher_project-db-1",
            "database": "screenwatcher",
        }

    def execute_query(self, sql):
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql)
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            return results
        except Exception as e:
            return f"SQL_ERROR: {str(e)}"

    def get_company_structure(self):
        return self.execute_query(
            "SELECT code, name, description FROM registry_machine"
        )

    def get_smart_metrics(self, machine_code, date_str):
        """Naprawiona metoda z polem pts."""
        res = self.execute_query(
            f"SELECT id, name FROM registry_machine WHERE code = '{machine_code}'"
        )
        if not res or isinstance(res, str):
            return []
        mid = res[0]["id"]
        mname = res[0]["name"]

        # Szybkie zapytanie o wydajność i punkty (pts)
        sql_speed = f"""
            SELECT 
                '{machine_code}' as code,
                '{mname}' as name,
                AVG(NULLIF(value, 0)) as avg_net_speed_m2h,
                MAX(value) as max_speed_m2h,
                COUNT(*) as pts
            FROM collector_metricreading
            WHERE machine_id = '{mid}' 
              AND name = 'real_speed_m2h' 
              AND DATE(timestamp) = '{date_str}' 
              AND value < 450
        """
        speed_data = self.execute_query(sql_speed)

        # Szybkie zapytanie o przestoje
        sql_stops = f"""
            SELECT COUNT(*) * 11 / 60 as estimated_stop_min
            FROM (
                SELECT value, LAG(value) OVER (ORDER BY timestamp) as prev_value
                FROM collector_metriccontext
                WHERE machine_id = '{mid}' AND `key` = 'ocr_blob_hash' AND DATE(timestamp) = '{date_str}'
            ) as sub
            WHERE value = prev_value
        """
        stop_data = self.execute_query(sql_stops)

        if isinstance(speed_data, list) and len(speed_data) > 0:
            result = speed_data[0]
            result["estimated_stop_min"] = (
                stop_data[0]["estimated_stop_min"]
                if isinstance(stop_data, list) and len(stop_data) > 0
                else 0
            )
            return [result]

        return []


if __name__ == "__main__":
    bridge = ScreenWatcherBridge()
    print(json.dumps(bridge.get_smart_metrics("M01", "2026-02-24"), indent=2))
