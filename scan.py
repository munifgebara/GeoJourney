#!/usr/bin/env python3
"""
scan.py
---------------------------------
Scanner de fotos/vídeos usando NudeNet + SQLite.
Atende aos requisitos:
- Varre diretório recursivamente (imagens e vídeos)
- Usa NudeNet (GPU se TF-GPU estiver instalado)
- Banco de dados SQLite (stdlib, sem instalar nada extra)
- Incremental (só reanalisa se arquivo mudou)
- **DB padrão é criado/aberto em <root>/media_scan.sqlite**
- Suporte a **lista de labels ignoradas** (default inclui "FEET_COVERED")

Requisitos:
    pip install nudenet opencv-python
    # Instale também TensorFlow (CPU ou GPU) conforme sua máquina.

Uso:
    # Sem argumentos -> usa 'scan' com defaults
    python scan.py

    # Scan explícito (root default abaixo) e DB default <root>/media_scan.sqlite
    python scan.py scan

    # Informando outro root e adicionando labels a ignorar
    python scan.py scan /minhas/midias --ignore-label HAND --ignore-label ELBOW

    # Listar detecções (filtro opcional)
    python scan.py list --label F_BREAST --min-score 0.8

    # Ver mídias registradas
    python scan.py show-media --limit 20
"""

import argparse
import hashlib
import os
import sqlite3
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

# -------------------------------
# Configurações básicas
# -------------------------------

DEFAULT_ROOT = "/media/munif/DADOSMUNIF/out"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}

# Labels para ignorar por padrão
IGNORED_LABELS_DEFAULT = {
    "FEET_COVERED",
    "FEET_EXPOSED",
    "FACE_FEMALE",
    "FACE_MALE",
    "FEMALE_BREAST_COVERED",
    "MALE_BREAST_COVERED",
    "MALE_BREAST_EXPOSED",
    "BELLY_COVERED",
    "BELLY_EXPOSED",
    "ARMPITS_COVERED",
    "ARMPITS_EXPOSED"
}

# -------------------------------
# Dependências opcionais (em runtime)
# -------------------------------
try:
    from nudenet import NudeDetector
except Exception:
    NudeDetector = None

try:
    import cv2
except Exception:
    cv2 = None


# -------------------------------
# Utilitários
# -------------------------------

def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def infer_media_type(path: Path) -> Optional[str]:
    ext = path.suffix.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    return None


def human_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts).isoformat(timespec="seconds")


# -------------------------------
# Banco de Dados (SQLite)
# -------------------------------

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    sha256 TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    mtime REAL NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('image','video')),
    width INTEGER,
    height INTEGER,
    duration REAL,
    analyzed_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS detections (
    id INTEGER PRIMARY KEY,
    media_id INTEGER NOT NULL REFERENCES media(id) ON DELETE CASCADE,
    frame_time REAL, -- em segundos; NULL para imagens
    box_x1 INTEGER, box_y1 INTEGER, box_x2 INTEGER, box_y2 INTEGER,
    score REAL,
    label TEXT
);
CREATE INDEX IF NOT EXISTS idx_media_type ON media(type);
CREATE INDEX IF NOT EXISTS idx_det_media ON detections(media_id);
CREATE INDEX IF NOT EXISTS idx_det_label_score ON detections(label, score);
"""

@dataclass
class DB:
    path: Path

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def ensure_schema(self):
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    def get_media_by_path(self, path: Path) -> Optional[Tuple]:
        with self.connect() as conn:
            cur = conn.execute("SELECT * FROM media WHERE path = ?", (str(path),))
            return cur.fetchone()

    def upsert_media(
        self,
        path: Path,
        sha256: str,
        size_bytes: int,
        mtime: float,
        mtype: str,
        width: Optional[int],
        height: Optional[int],
        duration: Optional[float],
    ) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO media (path, sha256, size_bytes, mtime, type, width, height, duration, analyzed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    sha256=excluded.sha256,
                    size_bytes=excluded.size_bytes,
                    mtime=excluded.mtime,
                    type=excluded.type,
                    width=excluded.width,
                    height=excluded.height,
                    duration=excluded.duration,
                    analyzed_at=excluded.analyzed_at
                """,
                (
                    str(path), sha256, size_bytes, mtime, mtype,
                    width, height, duration, time.time()
                )
            )
            media_id = cur.lastrowid
            if media_id == 0:
                cur = conn.execute("SELECT id FROM media WHERE path = ?", (str(path),))
                row = cur.fetchone()
                media_id = row[0]
            return media_id

    def delete_detections_for_media(self, media_id: int):
        with self.connect() as conn:
            conn.execute("DELETE FROM detections WHERE media_id = ?", (media_id,))

    def insert_detections(self, media_id: int, rows: List[Tuple]):
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO detections
                (media_id, frame_time, box_x1, box_y1, box_x2, box_y2, score, label)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows
            )


# -------------------------------
# NudeNet Detector wrapper
# -------------------------------

class NudeNetWrapper:
    def __init__(self):
        if NudeDetector is None:
            raise RuntimeError(
                "NudeNet não encontrado. Instale com: pip install nudenet\n"
                "E lembre-se do TensorFlow (CPU ou GPU)."
            )
        self.detector = NudeDetector()

    def detect_image_path(self, path: Path) -> List[dict]:
        return self.detector.detect(str(path))

    def detect_image_array(self, bgr_image) -> List[dict]:
        try:
            return self.detector.detect(bgr_image)
        except Exception:
            # fallback via arquivo temporário
            import tempfile
            import cv2 as _cv2
            fd, tmp = tempfile.mkstemp(suffix=".jpg")
            os.close(fd)
            try:
                _cv2.imwrite(tmp, bgr_image)
                return self.detector.detect(tmp)
            finally:
                try:
                    os.remove(tmp)
                except Exception:
                    pass


# -------------------------------
# Varredura / Análise
# -------------------------------

def scan_paths(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if infer_media_type(p) is None:
            continue
        yield p


def get_image_size(path: Path) -> Tuple[Optional[int], Optional[int]]:
    if cv2 is None:
        return None, None
    try:
        img = cv2.imread(str(path))
        if img is None:
            return None, None
        h, w = img.shape[:2]
        return w, h
    except Exception:
        return None, None


def get_video_meta(path: Path) -> Tuple[Optional[int], Optional[int], Optional[float]]:
    if cv2 is None:
        return None, None, None
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return None, None, None
    try:
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
        duration = float(frame_count / fps) if fps > 0 else None
        return width, height, duration
    finally:
        cap.release()


def analyze_image(detector: NudeNetWrapper, path: Path, ignored: set) -> List[Tuple]:
    detections = detector.detect_image_path(path)
    rows: List[Tuple] = []
    for d in detections:
        box = d.get("box") or [None, None, None, None]
        score = float(d.get("score", 0.0))
        raw_label = d.get("label") or d.get("class") or d.get("name") or d.get("title") or ""
        label = str(raw_label).upper()
        if label and label in ignored:
            continue

        rows.append((None,
                     None,
                     int(box[0]) if box[0] is not None else None,
                     int(box[1]) if box[1] is not None else None,
                     int(box[2]) if box[2] is not None else None,
                     int(box[3]) if box[3] is not None else None,
                     score, label))
    return rows


def analyze_video(detector: NudeNetWrapper, path: Path, interval_s: float, ignored: set) -> List[Tuple]:
    if cv2 is None:
        raise RuntimeError("OpenCV não está instalado. Instale com: pip install opencv-python")

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        print(f"[WARN] Não foi possível abrir o vídeo: {path}", file=sys.stderr)
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    duration = (cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0) / fps if fps > 0 else None

    rows: List[Tuple] = []
    t = 0.0
    try:
        while True:
            if duration is not None and t > duration:
                break
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
            ok, frame = cap.read()
            if not ok or frame is None:
                break

            dets = detector.detect_image_array(frame)
            for d in dets:
                box = d.get("box") or [None, None, None, None]
                score = float(d.get("score", 0.0))
                raw_label = d.get("label") or d.get("class") or d.get("name") or d.get("title") or ""
                label = str(raw_label).upper()
                if label and label in ignored:
                    continue

                rows.append((None,
                             float(t),
                             int(box[0]) if box[0] is not None else None,
                             int(box[1]) if box[1] is not None else None,
                             int(box[2]) if box[2] is not None else None,
                             int(box[3]) if box[3] is not None else None,
                             score, label))
            t += max(0.001, interval_s)
    finally:
        cap.release()

    return rows


def needs_reanalysis(db: DB, path: Path, sha: str, size: int, mtime: float) -> bool:
    row = db.get_media_by_path(path)
    if row is None:
        return True
    _, _, sha_db, size_db, mtime_db, *_ = row
    return (sha_db != sha) or (size_db != size) or (abs(mtime_db - mtime) > 1e-6)


# -------------------------------
# Comandos
# -------------------------------

def cmd_scan(args):
    root = Path(args.root).expanduser().resolve()
    if not root.exists():
        print(f"[ERRO] Pasta não existe: {root}", file=sys.stderr)
        sys.exit(2)

    # Define o DB: se não passar --db, usa <root>/media_scan.sqlite
    db_path = Path(args.db).expanduser().resolve() if args.db else (root / "media_scan.sqlite")
    db = DB(db_path)
    db.ensure_schema()

    if NudeDetector is None:
        print("[ERRO] NudeNet não instalado. Rode: pip install nudenet", file=sys.stderr)
        sys.exit(3)
    detector = NudeNetWrapper()

    # Conjunto de labels ignoradas
    ignored = set(s.upper() for s in IGNORED_LABELS_DEFAULT)
    if getattr(args, "ignore_label", None):
        ignored.update(s.upper() for s in args.ignore_label)

    total_files = 0
    new_or_updated = 0
    skipped = 0

    for path in scan_paths(root):
        total_files += 1
        media_type = infer_media_type(path)
        size = path.stat().st_size
        mtime = path.stat().st_mtime
        sha = sha256_file(path)

        if not needs_reanalysis(db, path, sha, size, mtime):
            skipped += 1
            continue

        width = height = None
        duration = None

        try:
            if media_type == "image":
                width, height = get_image_size(path)
                det_rows = analyze_image(detector, path, ignored)
            else:
                width, height, duration = get_video_meta(path)
                det_rows = analyze_video(detector, path, args.video_interval, ignored)
        except Exception as e:
            print(f"[WARN] Falha ao analisar {path}: {e}", file=sys.stderr)
            continue

        media_id = db.upsert_media(
            path=path,
            sha256=sha,
            size_bytes=size,
            mtime=mtime,
            mtype=media_type,
            width=width,
            height=height,
            duration=duration
        )

        db.delete_detections_for_media(media_id)
        if det_rows:
            rows = [(media_id, *row[1:]) for row in det_rows]
            db.insert_detections(media_id, rows)

        new_or_updated += 1
        if (len(det_rows)>0):
           print(f"{path}")

    print(f"\nResumo: analisados/atualizados={new_or_updated}, pulados={skipped}, total_encontrados={total_files}")
    print(f"DB: {db_path}")


def cmd_list(args):
    db_path = Path(args.db).expanduser().resolve()
    if not db_path.exists():
        print(f"[ERRO] Banco inexistente: {db_path}", file=sys.stderr)
        sys.exit(2)

    sql = """
    SELECT m.path, m.type, d.frame_time, d.box_x1, d.box_y1, d.box_x2, d.box_y2, d.score, d.label
    FROM detections d
    JOIN media m ON m.id = d.media_id
    WHERE 1=1
    """
    params: List = []

    if args.label:
        sql += " AND d.label = ?"
        params.append(args.label.upper())
    if args.min_score is not None:
        sql += " AND d.score >= ?"
        params.append(float(args.min_score))
    if args.type:
        sql += " AND m.type = ?"
        params.append(args.type)

    sql += " ORDER BY d.score DESC LIMIT ?"
    params.append(int(args.limit))

    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(sql, tuple(params))
        rows = cur.fetchall()

    import json
    for r in rows:
        path, mtype, frame_time, x1, y1, x2, y2, score, label = r
        record = {
            "path": path,
            "type": mtype,
            "frame_time": frame_time,
            "detection": {
                "box": [x1, y1, x2, y2],
                "score": float(score),
                "label": label
            }
        }
        print(json.dumps(record, ensure_ascii=False))


def cmd_show_media(args):
    db_path = Path(args.db).expanduser().resolve()
    if not db_path.exists():
        print(f"[ERRO] Banco inexistente: {db_path}", file=sys.stderr)
        sys.exit(2)

    sql = """
    SELECT id, path, type, width, height, duration, analyzed_at
    FROM media
    ORDER BY analyzed_at DESC
    LIMIT ?
    """
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(sql, (int(args.limit),))
        rows = cur.fetchall()

    for (mid, path, mtype, w, h, dur, ts) in rows:
        print(f"[{mid}] {mtype.upper()} {path}")
        print(f"    size: {w}x{h}  duration: {dur if dur is not None else '-'}  analyzed_at: {human_ts(ts)}")


# -------------------------------
# CLI
# -------------------------------

def build_argparser():
    p = argparse.ArgumentParser(description="Scanner de fotos/vídeos com NudeNet + SQLite")
    sub = p.add_subparsers(dest="cmd")  # não-required; default será 'scan'

    # scan
    ps = sub.add_parser("scan", help="Escanear diretório e atualizar banco")
    ps.add_argument(
        "root",
        nargs="?",
        default=DEFAULT_ROOT,
        help=f"Pasta raiz a escanear (default: {DEFAULT_ROOT})"
    )
    ps.add_argument("--db", default=None, help="Arquivo SQLite; default: <root>/media_scan.sqlite")
    ps.add_argument("--video-interval", type=float, default=1.0, help="Intervalo (s) entre frames no vídeo (default: 1.0s)")
    ps.add_argument("--ignore-label", action="append", default=[], help="Adicionar rótulos a ignorar (pode repetir)")
    ps.set_defaults(func=cmd_scan)

    # list
    pl = sub.add_parser("list", help="Listar detecções filtrando por label/score")
    pl.add_argument("--db", required=True, help="Caminho do arquivo SQLite")
    pl.add_argument("--label", help="Rótulo exato (será uppercased)")
    pl.add_argument("--min-score", type=float, default=None, help="Pontuação mínima (ex.: 0.7)")
    pl.add_argument("--type", choices=["image","video"], help="Filtrar pelo tipo de mídia")
    pl.add_argument("--limit", type=int, default=100, help="Máximo de linhas (default: 100)")
    pl.set_defaults(func=cmd_list)

    # show-media
    pm = sub.add_parser("show-media", help="Mostrar resumo das mídias no banco")
    pm.add_argument("--db", required=True, help="Caminho do arquivo SQLite")
    pm.add_argument("--limit", type=int, default=50)
    pm.set_defaults(func=cmd_show_media)

    return p


def main():
    parser = build_argparser()
    args = parser.parse_args()
    # default para 'scan' se nenhum subcomando informado
    if not hasattr(args, "func"):
        from argparse import Namespace
        args = Namespace(cmd="scan", root=DEFAULT_ROOT, db=None, video_interval=1.0, ignore_label=[])
        return cmd_scan(args)
    args.func(args)


if __name__ == "__main__":
    main()