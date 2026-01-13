"""Market data management module."""

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List

from apps.logger import logger


class MarketDataManager:
    """Market data metadata management."""

    db_path: str

    def save_market_data_metadata(self, data: Dict[str, Any]) -> int:
        """
        Save metadata for a downloaded market dataset.

        Args:
            data: Dictionary containing:
                - symbol: str
                - timeframe: str
                - source: str
                - start_date: datetime or str
                - end_date: datetime or str
                - record_count: int
                - validation_report: dict (will be json serialized)
                - file_path: str

        Returns:
            ID of the inserted record
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            # Serialize validation report if it's a dict
            validation_report = data.get("validation_report")
            if isinstance(validation_report, dict):
                validation_report = json.dumps(validation_report)

            query = """
            INSERT INTO market_data (
                symbol, timeframe, source, start_date, end_date,
                record_count, validation_report, file_path, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            cursor.execute(
                query,
                (
                    data["symbol"],
                    data["timeframe"],
                    data["source"],
                    data.get("start_date"),
                    data.get("end_date"),
                    data.get("record_count", 0),
                    validation_report,
                    data["file_path"],
                    datetime.now(),
                ),
            )

            market_data_id = cursor.lastrowid
            conn.commit()
            logger.info(
                f"Saved market data metadata for {data['symbol']} ({market_data_id})"
            )
            return int(market_data_id) if market_data_id is not None else 0

        except Exception as e:
            logger.error(f"Error saving market data metadata: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_market_data_list(self) -> List[Dict[str, Any]]:
        """
        Get all market data records.

        Returns:
            List of dictionaries containing market data metadata
        """
        conn = sqlite3.connect(self.db_path)
        try:
            # Row factory is likely set in base, but to be sure we can just fetch tuples and map
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, symbol, timeframe, source, start_date, end_date,
                       record_count, validation_report, file_path, created_at
                FROM market_data
                ORDER BY created_at DESC
            """
            )

            rows = cursor.fetchall()
            results = []

            for row in rows:
                results.append(
                    {
                        "id": row[0],
                        "symbol": row[1],
                        "timeframe": row[2],
                        "source": row[3],
                        "start_date": row[4],
                        "end_date": row[5],
                        "record_count": row[6],
                        "validation_report": json.loads(row[7]) if row[7] else {},
                        "file_path": row[8],
                        "created_at": row[9],
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Error getting market data list: {e}")
            return []
        finally:
            conn.close()

    def delete_market_data(self, data_id: int) -> bool:
        """
        Delete a market data record by ID.

        Args:
            data_id: ID of the record to delete

        Returns:
            True if deleted, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM market_data WHERE id = ?", (data_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting market data {data_id}: {e}")
            return False
        finally:
            conn.close()
