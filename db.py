import sqlite3
import json
from datetime import date, datetime
from pathlib import Path

DB_PATH = Path("reminder.db")

DREAM_TYPES = {
    "HAPPY": "행복한 꿈",
    "FUNNY": "재미있는 꿈",
    "SAD": "슬픈 꿈",
    "NIGHTMARE": "악몽",
    "ANNOYING": "짜증나는 꿈",
    "LUCID": "자각몽",
    "NO_MEMORY": "기억 안 남",
    "OTHER": "기타",
}

TECHNIQUES = ["WBTB", "MILD", "WILD", "FILD", "SSILD", "현실 확인", "수면 일기"]

TECHNIQUE_DESC = {
    "WBTB": "Wake Back To Bed — 5~6시간 수면 후 잠깐 깨어 있다가 다시 잠드는 기법. REM 수면 진입을 노림.",
    "MILD": "Mnemonic Induction of Lucid Dreams — 잠들기 전 드림사인을 떠올리며 '꿈에서 알아차리겠다'는 의도를 반복 각인.",
    "WILD": "Wake Initiated Lucid Dream — 깨어있는 상태에서 의식을 유지하며 곧바로 꿈 속으로 진입하는 고급 기법.",
    "FILD": "Finger Induced Lucid Dream — 반수면 상태에서 손가락을 아주 살짝 두드리며 의식을 꿈으로 끌어들이는 기법.",
    "SSILD": "Senses Initiated Lucid Dream — 눈/귀/몸 감각에 반복적으로 주의를 기울여 자각몽 상태로 유도.",
    "현실 확인": "Reality Check — 낮 동안 '지금 꿈인가?'를 의식적으로 확인 (손 보기, 코 막고 숨쉬기 등). 꿈에서도 같은 행동을 하도록 습관화.",
    "수면 일기": "Sleep Journal — 매일 아침 꿈을 바로 기록하는 습관. 꿈 회상력을 높이고 드림사인 파악에 도움.",
}


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS dreams (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,

                -- 기본 꿈일기 (1단계)
                dream_date      TEXT    NOT NULL,          -- 'YYYY-MM-DD'  꿈을 꾼 날
                title           TEXT    NOT NULL DEFAULT '',
                content         TEXT    NOT NULL,
                dream_type      TEXT    NOT NULL DEFAULT 'OTHER',
                is_lucid        INTEGER NOT NULL DEFAULT 0, -- 자각몽 여부 빠른 필터용

                -- LLM 분석 결과 (1단계)
                analysis_text   TEXT,                       -- 해석/상징 텍스트
                recall_score    INTEGER,                    -- 1~10점
                recurring_people    TEXT DEFAULT '[]',      -- JSON list
                recurring_places    TEXT DEFAULT '[]',
                recurring_emotions  TEXT DEFAULT '[]',

                -- 수면 기법 & 컨디션 (2단계)
                techniques_tried    TEXT DEFAULT '[]',      -- JSON list (WBTB, MILD …)
                sleep_hours         REAL,
                alarm_used          INTEGER,                -- 0/1
                caffeine_prev_day   INTEGER,               -- 0/1  전날 카페인
                alcohol_prev_day    INTEGER,               -- 0/1  전날 알코올

                -- Reality check (2단계)
                reality_check_count INTEGER DEFAULT 0,      -- 그날 한 횟수

                -- 드림사인 클러스터링 / 자연어 검색용 (3단계)
                embedding           TEXT,                   -- JSON float list

                -- 메타
                created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime')),
                updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime'))
            );

            CREATE INDEX IF NOT EXISTS idx_dreams_date     ON dreams(dream_date);
            CREATE INDEX IF NOT EXISTS idx_dreams_type     ON dreams(dream_type);
            CREATE INDEX IF NOT EXISTS idx_dreams_lucid    ON dreams(is_lucid);
            CREATE INDEX IF NOT EXISTS idx_dreams_recall   ON dreams(recall_score);
        """)


# ── Create ──────────────────────────────────────────────────

def add_dream(
    dream_date: str,
    content: str,
    title: str = "",
    dream_type: str = "OTHER",
) -> int:
    is_lucid = 1 if dream_type == "LUCID" else 0
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO dreams (dream_date, title, content, dream_type, is_lucid)
               VALUES (?, ?, ?, ?, ?)""",
            (dream_date, title, content, dream_type, is_lucid),
        )
        return cur.lastrowid


# ── Read ────────────────────────────────────────────────────

def get_dream(dream_id: int) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM dreams WHERE id = ?", (dream_id,)
        ).fetchone()


def list_dreams(limit: int = 50, offset: int = 0) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM dreams ORDER BY dream_date DESC, id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()


def get_dreams_by_date_range(start: str, end: str) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM dreams WHERE dream_date BETWEEN ? AND ? ORDER BY dream_date",
            (start, end),
        ).fetchall()


# ── Update ──────────────────────────────────────────────────

def update_analysis(
    dream_id: int,
    analysis_text: str,
    recall_score: int,
    recurring_people: list[str],
    recurring_places: list[str],
    recurring_emotions: list[str],
):
    with get_conn() as conn:
        conn.execute(
            """UPDATE dreams
               SET analysis_text      = ?,
                   recall_score       = ?,
                   recurring_people   = ?,
                   recurring_places   = ?,
                   recurring_emotions = ?,
                   updated_at         = strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime')
               WHERE id = ?""",
            (
                analysis_text,
                recall_score,
                json.dumps(recurring_people, ensure_ascii=False),
                json.dumps(recurring_places, ensure_ascii=False),
                json.dumps(recurring_emotions, ensure_ascii=False),
                dream_id,
            ),
        )


def update_condition(
    dream_id: int,
    techniques_tried: list[str],
    sleep_hours: float | None,
    alarm_used: bool | None,
    caffeine_prev_day: bool | None,
    alcohol_prev_day: bool | None,
    reality_check_count: int,
):
    with get_conn() as conn:
        conn.execute(
            """UPDATE dreams
               SET techniques_tried   = ?,
                   sleep_hours        = ?,
                   alarm_used         = ?,
                   caffeine_prev_day  = ?,
                   alcohol_prev_day   = ?,
                   reality_check_count = ?,
                   updated_at         = strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime')
               WHERE id = ?""",
            (
                json.dumps(techniques_tried, ensure_ascii=False),
                sleep_hours,
                int(alarm_used) if alarm_used is not None else None,
                int(caffeine_prev_day) if caffeine_prev_day is not None else None,
                int(alcohol_prev_day) if alcohol_prev_day is not None else None,
                reality_check_count,
                dream_id,
            ),
        )


def update_embedding(dream_id: int, embedding: list[float]):
    with get_conn() as conn:
        conn.execute(
            """UPDATE dreams
               SET embedding  = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime')
               WHERE id = ?""",
            (json.dumps(embedding), dream_id),
        )


# ── Delete ──────────────────────────────────────────────────

def delete_dream(dream_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM dreams WHERE id = ?", (dream_id,))


# ── Stats helpers (대시보드용) ──────────────────────────────

def get_recall_trend(days: int = 30) -> list[dict]:
    """최근 N일 날짜별 평균 회상 점수."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT dream_date, AVG(recall_score) AS avg_score, COUNT(*) AS cnt
               FROM dreams
               WHERE recall_score IS NOT NULL
                 AND dream_date >= date('now', ?)
               GROUP BY dream_date
               ORDER BY dream_date""",
            (f"-{days} days",),
        ).fetchall()
    return [dict(r) for r in rows]


def get_type_distribution() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT dream_type, COUNT(*) AS cnt
               FROM dreams
               GROUP BY dream_type
               ORDER BY cnt DESC"""
        ).fetchall()
    return [dict(r) for r in rows]


def get_lucid_trend(months: int = 6) -> list[dict]:
    """월별 자각몽 횟수."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT strftime('%Y-%m', dream_date) AS month,
                      SUM(is_lucid) AS lucid_cnt,
                      COUNT(*) AS total_cnt
               FROM dreams
               WHERE dream_date >= date('now', ?)
               GROUP BY month
               ORDER BY month""",
            (f"-{months} months",),
        ).fetchall()
    return [dict(r) for r in rows]


def get_streak() -> dict:
    """연속 기록 일수 & 전체 기록 일수."""
    with get_conn() as conn:
        dates = [
            r[0]
            for r in conn.execute(
                "SELECT DISTINCT dream_date FROM dreams ORDER BY dream_date DESC"
            ).fetchall()
        ]
    if not dates:
        return {"streak": 0, "total_days": 0, "last_date": None}

    streak = 0
    prev = date.fromisoformat(dates[0])
    today = date.today()
    if (today - prev).days > 1:
        return {"streak": 0, "total_days": len(dates), "last_date": dates[0]}

    for d_str in dates:
        d = date.fromisoformat(d_str)
        if (prev - d).days <= 1:
            streak += 1
            prev = d
        else:
            break

    return {"streak": streak, "total_days": len(dates), "last_date": dates[0]}


def get_activity_calendar(days: int = 365) -> list[dict]:
    """날짜별 기록 수 (GitHub 잔디용)."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT dream_date, COUNT(*) AS cnt
               FROM dreams
               WHERE dream_date >= date('now', ?)
               GROUP BY dream_date
               ORDER BY dream_date""",
            (f"-{days} days",),
        ).fetchall()
    return [dict(r) for r in rows]


def get_lucid_calendar(days: int = 365) -> list[dict]:
    """날짜별 자각몽 여부 (캘린더 히트맵용)."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT dream_date, MAX(is_lucid) AS is_lucid
               FROM dreams
               WHERE dream_date >= date('now', ?)
               GROUP BY dream_date
               ORDER BY dream_date""",
            (f"-{days} days",),
        ).fetchall()
    return [dict(r) for r in rows]


def get_technique_stats() -> list[dict]:
    """기법별 사용 횟수 & 자각몽 연관율."""
    from collections import defaultdict
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT techniques_tried, is_lucid FROM dreams
               WHERE techniques_tried IS NOT NULL AND techniques_tried != '[]'"""
        ).fetchall()
    stats = defaultdict(lambda: {"used": 0, "lucid": 0})
    for row in rows:
        for t in json.loads(row["techniques_tried"] or "[]"):
            stats[t]["used"] += 1
            if row["is_lucid"]:
                stats[t]["lucid"] += 1
    return [
        {
            "technique": k,
            "used": v["used"],
            "lucid": v["lucid"],
            "lucid_rate": round(v["lucid"] / v["used"] * 100, 1) if v["used"] else 0,
        }
        for k, v in stats.items()
    ]


def get_condition_recall_stats() -> list[dict]:
    """컨디션 원시 데이터 (Python 측에서 집계)."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT sleep_hours, alarm_used, caffeine_prev_day, alcohol_prev_day,
                      reality_check_count, recall_score, is_lucid
               FROM dreams
               WHERE recall_score IS NOT NULL
                  OR sleep_hours IS NOT NULL
                  OR reality_check_count > 0"""
        ).fetchall()
    return [dict(r) for r in rows]


def search_dreams(query: str) -> list[dict]:
    """제목/내용/분석 텍스트에서 키워드 검색."""
    terms = [t.strip() for t in query.split() if t.strip()]
    if not terms:
        return []
    conditions = " OR ".join(
        ["(title LIKE ? OR content LIKE ? OR analysis_text LIKE ?)"] * len(terms)
    )
    params = []
    for t in terms:
        p = f"%{t}%"
        params.extend([p, p, p])
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM dreams WHERE {conditions} ORDER BY dream_date DESC LIMIT 50",
            params,
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_recurring_elements() -> list[str]:
    """모든 꿈의 recurring_people/places/emotions 합산."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT recurring_people, recurring_places, recurring_emotions FROM dreams"
        ).fetchall()
    elements = []
    for row in rows:
        for col in ["recurring_people", "recurring_places", "recurring_emotions"]:
            elements.extend(json.loads(row[col] or "[]"))
    return [e for e in elements if e.strip()]


def get_weekly_dreams(offset_days: int = 0) -> list[dict]:
    """최근 7일 꿈 목록 (offset_days=7이면 지난주)."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM dreams
               WHERE dream_date >= date('now', ?)
                 AND dream_date <= date('now', ?)
               ORDER BY dream_date""",
            (f"-{7 + offset_days} days", f"-{offset_days} days"),
        ).fetchall()
    return [dict(r) for r in rows]
