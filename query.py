import sqlite3

DB_PATH = "media_scan.sqlite"

SQL = """
SELECT label, COUNT(*) AS qtd
FROM detections
GROUP BY label
ORDER BY qtd DESC
LIMIT 10;
"""
PARAMS = {}


SQL = """
SELECT m.path, m.type, d.frame_time, d.box_x1, d.box_y1, d.box_x2, d.box_y2, d.score, d.label
FROM detections d
JOIN media m ON m.id = d.media_id
WHERE d.score >= :minscore
AND 

ORDER BY d.score DESC
LIMIT 50;
"""
PARAMS = {"minscore": 0.85}




def is_select(sql: str) -> bool:
    s = sql.lstrip().upper()
    return s.startswith("SELECT") or s.startswith("WITH")

def print_table(headers, rows):
    # Impressão simples em tabela (sem libs externas)
    data = [headers] + [[("" if v is None else str(v)) for v in r] for r in rows]
    widths = [max(len(row[i]) for row in data) for i in range(len(headers))] if headers else []
    sep = "+{}+".format("+".join("-" * (w + 2) for w in widths)) if widths else ""
    if headers:
        print(sep)
        print("| " + " | ".join(h.ljust(w) for h, w in zip(headers, widths)) + " |")
        print(sep)
    for r in data[1:]:
        print("| " + " | ".join(c.ljust(w) for c, w in zip(r, widths)) + " |")
    if headers:
        print(sep)

def main():
    if not is_select(SQL):
        raise ValueError("Este script só executa SELECT (ou WITH ...).")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(SQL, PARAMS)
        rows = cur.fetchall()
        headers = [d[0] for d in cur.description] if cur.description else []
        print_table(headers, [tuple(r) for r in rows])
        print(f"\n{len(rows)} linha(s).")
    finally:
        conn.close()

if __name__ == "__main__":
    main()