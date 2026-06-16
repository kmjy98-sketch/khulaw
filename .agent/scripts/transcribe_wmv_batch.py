"""법조윤리 2024 wmv 배치 전사 스크립트 (whisper)"""
import whisper
import os
import glob

MODEL_SIZE = "small"
WMV_DIR = r"H:\내 드라이브\4.선택법\10.법조윤리\2024 법조윤리\2024 법조윤리"
OUT_DIR = r"H:\내 드라이브\4.선택법\10.법조윤리\전사문\2024_wmv"

os.makedirs(OUT_DIR, exist_ok=True)

print(f"[모델 로드] whisper {MODEL_SIZE}")
model = whisper.load_model(MODEL_SIZE)

wmv_files = sorted(glob.glob(os.path.join(WMV_DIR, "*.wmv")))
print(f"[발견] {len(wmv_files)}개 wmv 파일")

done = 0
skipped = 0

for wmv_path in wmv_files:
    basename = os.path.splitext(os.path.basename(wmv_path))[0]
    out_path = os.path.join(OUT_DIR, f"{basename}_transcript.md")

    if os.path.exists(out_path):
        print(f"[건너뜀] {basename}")
        skipped += 1
        continue

    print(f"\n[전사] {basename}")
    try:
        result = model.transcribe(wmv_path, language="ko")

        lines = [f"# 전사문: {basename}\n"]
        lines.append(f"- **원본**: {os.path.basename(wmv_path)}")
        lines.append(f"- **모델**: whisper-{MODEL_SIZE}\n")
        lines.append("---\n")

        for seg in result["segments"]:
            h = int(seg["start"] // 3600)
            m = int(seg["start"] % 3600 // 60)
            s = int(seg["start"] % 60)
            lines.append(f"[{h:02d}:{m:02d}:{s:02d}] {seg['text'].strip()}")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"[완료] {out_path}")
        done += 1
    except Exception as e:
        print(f"[오류] {basename}: {e}")

print(f"\n=== 완료: {done}개 / 건너뜀: {skipped}개 / 총: {len(wmv_files)}개 ===")
