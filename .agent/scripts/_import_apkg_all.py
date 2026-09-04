# -*- coding: utf-8 -*-
"""v37 apkg 31개를 Anki 컬렉션('사용자 1')에 일괄 임포트 (공식 anki 라이브러리).
Anki 앱이 닫혀 있어야 함. --pilot 이면 첫 파일 1개만."""
import glob, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from anki.collection import Collection, ImportAnkiPackageRequest
from anki.import_export_pb2 import ImportAnkiPackageOptions, ImportAnkiPackageUpdateCondition as UC

COL = os.path.join(os.environ["APPDATA"], "Anki2", "사용자 1", "collection.anki2")
APKG_ROOT = r"E:\법학볼트\outputs\anki\v37\apkg"

files = sorted(glob.glob(os.path.join(APKG_ROOT, "*", "*.apkg")))
if "--pilot" in sys.argv:
    files = files[:1]
print(f"대상 {len(files)}개 / 컬렉션 {COL}")

col = Collection(COL)
try:
    total_new = 0
    for f in files:
        rel = os.path.relpath(f, APKG_ROOT)
        try:
            req = ImportAnkiPackageRequest(
                package_path=f,
                options=ImportAnkiPackageOptions(
                    merge_notetypes=True,
                    update_notes=UC.IMPORT_ANKI_PACKAGE_UPDATE_CONDITION_IF_NEWER,
                    update_notetypes=UC.IMPORT_ANKI_PACKAGE_UPDATE_CONDITION_IF_NEWER,
                    with_scheduling=False,
                ),
            )
            log = col.import_anki_package(req)
            n_new = len([r for r in log.log.new]) if hasattr(log.log, "new") else -1
            n_dup = len([r for r in log.log.duplicate]) if hasattr(log.log, "duplicate") else -1
            total_new += max(n_new, 0)
            print(f"  [OK] {rel}: 신규 {n_new} / 중복 {n_dup}")
        except Exception as e:
            print(f"  [실패] {rel}: {repr(e)[:120]}")
    print(f"합계 신규 {total_new}")
    print("카드 총수(컬렉션):", col.card_count())
finally:
    col.close()
print("완료")
