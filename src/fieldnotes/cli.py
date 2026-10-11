"""CLI: fieldnotes analyze | journal | web | wipe."""
from __future__ import annotations

import argparse
import sys

from .config import load_config
from .store import db as _db


def _cfg(args) -> dict:
    try:
        return load_config(args.config)
    except ValueError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


def cmd_analyze(args) -> None:
    from . import service as _svc

    cfg = _cfg(args)
    try:
        summary = _svc.analyze_walk(
            args.wav, cfg, lat=args.lat, lon=args.lon, date=args.date,
            weather_note=args.weather or "", own_recording=args.own)
    except ValueError as exc:
        print(f"analyze failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"walk {summary['walk_id']}: {summary['n_detections']} detections "
          f"in {summary['n_windows']} windows ({summary['n_gated']} gated as silence)")
    if summary.get("date_warning"):
        print(summary["date_warning"])
    for s in summary["species"]:
        print(f"  {s['start_s']:7.1f}s  {s['common']} ({s['sci']})  "
              f"conf={s['confidence']:.2f}  [{s['novelty']}]")
    if not summary["species"]:
        print("  (no calls above the confidence threshold — quiet walks are data too)")


def cmd_journal(args) -> None:
    from . import service as _svc

    cfg = _cfg(args)
    try:
        md, prov, model = _svc.journal_for_walk(cfg, args.walk_id, args.weather or "")
    except ValueError as exc:
        print(f"journal failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"--- journal for walk {args.walk_id} [{prov}] ---\n")
    print(md)


def cmd_wipe(args) -> None:
    cfg = _cfg(args)
    if not args.yes:
        print("This deletes the database and all saved clips. Re-run with --yes to confirm.",
              file=sys.stderr)
        raise SystemExit(2)
    _db.wipe_all(cfg["database"], cfg["clips_dir"])
    print("deleted all local data (database + clips).")


def cmd_web(args) -> None:
    from .web.app import serve

    serve(_cfg(args), port=args.port)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="fieldnotes", description="Offline outdoor companion.")
    ap.add_argument("--config", default="config.yaml")
    sub = ap.add_subparsers(required=True)

    a = sub.add_parser("analyze", help="analyze a recorded WAV file")
    a.add_argument("wav")
    a.add_argument("--lat", type=float, default=None)
    a.add_argument("--lon", type=float, default=None)
    a.add_argument("--date", default=None, help="walk date YYYY-MM-DD (sets season filter)")
    a.add_argument("--own", action="store_true",
                   help="this is my own walk recording (changes journal wording)")
    a.add_argument("--weather", default=None, help="optional weather note for the journal")
    a.set_defaults(func=cmd_analyze)

    j = sub.add_parser("journal", help="write the field journal for a walk")
    j.add_argument("walk_id", type=int)
    j.add_argument("--weather", default=None)
    j.set_defaults(func=cmd_journal)

    w = sub.add_parser("wipe", help="delete all local data")
    w.add_argument("--yes", action="store_true")
    w.set_defaults(func=cmd_wipe)

    s = sub.add_parser("web", help="start the local recap page (localhost only)")
    s.add_argument("--port", type=int, default=8765)
    s.set_defaults(func=cmd_web)

    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
