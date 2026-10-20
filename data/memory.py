"""Data слој: трајна меморија на чудовиштата (SQLite).

Идеја (инспирирано од Nemesis системот во Shadow of Mordor):
чудовиштата ТЕ ПАМЕТАТ меѓу игрите. Ги паметат местата каде најчесто
минуваш и правиш бучава, и следниот пат почесто патролираат таму.
Ако секогаш одиш по истиот ходник, наскоро таму ќе те чекаат.

Табели:
  heat(level, col, row, weight)
      „топлинска мапа“ по ниво: колку често играчот бил / правел звук на секоја плочка.
  games(id, level, result, duration, stones_used, hits, played_at)
      историја на одиграни партии (за статистика и за одбраната).

Заборавање: по секоја партија старите тежини се множат со MEMORY_DECAY (<1),
па меморијата се прилагодува: ако го смениш стилот, со време и тие ќе „научат“.

SQLite е вграден во Python (модул sqlite3): не бара инсталација ни сервер.
Базата е една датотека: echo_memory.db во коренот на проектот.
"""

import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path

from settings import MEMORY_DECAY, MEMORY_MIN_WEIGHT

SCHEMA = """
CREATE TABLE IF NOT EXISTS heat (
    level   INTEGER NOT NULL,
    col     INTEGER NOT NULL,
    row     INTEGER NOT NULL,
    weight  REAL    NOT NULL,
    PRIMARY KEY (level, col, row)
);
CREATE TABLE IF NOT EXISTS games (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    level       INTEGER NOT NULL,
    result      TEXT    NOT NULL,          -- 'won', 'lost', 'quit'
    duration    REAL    NOT NULL,
    stones_used INTEGER NOT NULL,
    hits        INTEGER NOT NULL,
    played_at   TEXT    NOT NULL
);
"""


class MonsterMemory:
    def __init__(self, db_path: str | Path):
        self.path = Path(db_path)
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(SCHEMA)

    # ================= Читање =================

    def load_heat(self, level: int) -> dict[tuple[int, int], float]:
        rows = self.conn.execute(
            "SELECT col, row, weight FROM heat WHERE level = ?", (level,)
        ).fetchall()
        return {(c, r): w for c, r, w in rows}

    def games_played(self, level: int) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM games WHERE level = ?", (level,)).fetchone()[0]

    def stats(self) -> list[tuple]:
        """(ниво, партии, победи, просечно време) за секое ниво."""
        return self.conn.execute(
            """SELECT level, COUNT(*), SUM(result = 'won'), ROUND(AVG(duration), 1)
               FROM games GROUP BY level ORDER BY level"""
        ).fetchall()

    # ================= Запишување =================

    def save_game(self, level: int, new_heat: Counter, result: str, duration: float,
                  stones_used: int, hits: int) -> None:
        """Една трансакција: заборави малку од старото, додај го новото, запиши ја партијата."""
        with self.conn:   # автоматски COMMIT (или ROLLBACK ако нешто падне)
            self.conn.execute("UPDATE heat SET weight = weight * ? WHERE level = ?", (MEMORY_DECAY, level))
            self.conn.execute("DELETE FROM heat WHERE level = ? AND weight < ?", (level, MEMORY_MIN_WEIGHT))
            self.conn.executemany(
                """INSERT INTO heat (level, col, row, weight) VALUES (?, ?, ?, ?)
                   ON CONFLICT (level, col, row) DO UPDATE SET weight = weight + excluded.weight""",
                [(level, c, r, w) for (c, r), w in new_heat.items()],
            )
            self.conn.execute(
                """INSERT INTO games (level, result, duration, stones_used, hits, played_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (level, result, round(duration, 2), stones_used, hits, datetime.now().isoformat(timespec="seconds")),
            )

    def reset(self) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM heat")
            self.conn.execute("DELETE FROM games")

    def close(self) -> None:
        self.conn.close()


def open_memory(db_path) -> "MonsterMemory | None":
    """Ако базата не може да се отвори (на пр. нема дозвола), играта работи без меморија."""
    try:
        return MonsterMemory(db_path)
    except sqlite3.Error as e:
        print(f"[memory] исклучена: {e}")
        return None
