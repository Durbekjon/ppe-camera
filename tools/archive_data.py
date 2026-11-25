"""Start a demo with an empty incident list, keeping the old data in data/archive/.

Usage (stop the app first):
  .venv/bin/python -m tools.archive_data                  shows what would move, changes nothing
  .venv/bin/python -m tools.archive_data --apply          archives
  .venv/bin/python -m tools.archive_data --list
  .venv/bin/python -m tools.archive_data --restore NAME   (only while there are no incidents)
"""
import argparse
import socket
import sys

from app import archive, config, dataset, db


def app_is_running():
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", config.PORT)) == 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--apply", action="store_true")
    group.add_argument("--list", action="store_true")
    group.add_argument("--restore", metavar="NAME")
    args = parser.parse_args()
    if args.list:
        names = sorted(p.name for p in dataset.ARCHIVE.iterdir() if p.is_dir()) if dataset.ARCHIVE.is_dir() else []
        print("\n".join(names) or "Arxiv yo'q.")
        return
    if (args.apply or args.restore) and app_is_running():
        sys.exit(f"{config.PORT}-portda ilova ishlab turibdi. Avval uni to'xtating (Ctrl+C).")
    db.init()
    if args.restore:
        try:
            print(f"Qaytarildi: {archive.restore(args.restore)} ta hodisa.")
        except (ValueError, FileExistsError) as e:
            sys.exit(str(e))
        return
    s = archive.summary()
    print(f"Hodisalar: {s['incidents']} · suratlar: {s['snapshots']} · asl kadrlar: {s['raw']} · "
          f"eksport fayllari: {s['exports']} · yuborilmagan Telegram xabarlari: {s['unsent']}")
    print(f"O'z joyida qoladi: foydalanuvchilar ({s['users']}), zonalar, .env sozlamalari.")
    if not args.apply:
        print("Hech narsa o'zgartirilmadi. Arxivlash uchun: --apply")
        return
    folder = archive.create()
    if folder is None:
        print("Arxivlanadigan narsa yo'q.")
        return
    print(f"Arxivlandi: {folder}\nQaytarish: .venv/bin/python -m tools.archive_data --restore {folder.name}")
    if s["unsent"]:
        print("Yuborilmagan xabarlar endi yuborilmaydi (ular arxiv bazasida saqlangan).")


if __name__ == "__main__":
    main()
