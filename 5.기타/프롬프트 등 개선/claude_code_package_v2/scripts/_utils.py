"""
공통 유틸리티 모듈.
- API key 로드
- 로깅
- 비용 추적
- 출력 검증
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# 패키지 루트 경로
PACKAGE_ROOT = Path(__file__).parent.parent.resolve()

# .env 로드
load_dotenv(PACKAGE_ROOT / ".env")


def get_anthropic_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key or key.startswith("sk-ant-api03-여기"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY가 설정되지 않았습니다.\n"
            ".env 파일에서 실제 키를 입력하세요. (.env.example 참고)"
        )
    return key


def get_google_key() -> str:
    """[DEPRECATED v3.6 Phase 1.1] Gemini/AI Studio 미사용 결정으로 사용 안 함.
    01번 OCR은 Claude로 교체됨. 이 함수는 호환을 위해 남겨두지만 호출 시 안내만."""
    raise RuntimeError(
        "Gemini/AI Studio는 v3.6 Phase 1.1에서 제거됨. 01_ocr.py는 Claude API 사용.\n"
        "이 함수가 호출됐다면 스크립트가 오래된 버전입니다."
    )


def setup_logger(name: str) -> logging.Logger:
    """timestamp별 로그 파일 + console 출력"""
    log_dir = PACKAGE_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    log_file = log_dir / f"{name}_{timestamp}.log"
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 파일 핸들러
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.INFO)
    
    # 콘솔 핸들러
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s - %(message)s",
        datefmt="%H:%M:%S"
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger


def read_prompt(prompt_filename: str) -> str:
    """prompts/ 폴더에서 프롬프트 파일 읽기"""
    prompt_path = PACKAGE_ROOT / "prompts" / prompt_filename
    if not prompt_path.exists():
        raise FileNotFoundError(f"프롬프트 파일 없음: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def log_cost(model: str, input_tokens: int, output_tokens: int):
    """월별 비용 누적 추적 — logs/cost_YYYY-MM.json"""
    # 대략적 단가 (USD per 1M tokens) — 정확한 가격은 공식 문서 확인
    # Phase 2: 01 OCR·02-wiki는 안티그래비티 앱(Gemini 3.5 Flash). 카드화는 claude-opus-4-8.
    pricing = {
        "claude-opus-4-8": {"input": 15.0, "output": 75.0},
        "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
        "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.0},
        # gemini-3.5-flash 단가는 공식 문서에서 확인 후 입력 (미확정)
        "gemini-3.5-flash": {"input": None, "output": None},
        "gemini-3.1-pro": {"input": 1.25, "output": 5.0},  # NotebookLM(04) 내장
    }
    
    if model not in pricing:
        return

    # 단가 미확정(None) 모델은 비용 계산 건너뜀 (예: gemini-3.5-flash)
    if pricing[model]["input"] is None or pricing[model]["output"] is None:
        return

    cost = (
        input_tokens / 1_000_000 * pricing[model]["input"]
        + output_tokens / 1_000_000 * pricing[model]["output"]
    )
    
    cost_file = PACKAGE_ROOT / "logs" / f"cost_{datetime.now().strftime('%Y-%m')}.json"
    
    if cost_file.exists():
        data = json.loads(cost_file.read_text(encoding="utf-8"))
    else:
        data = {"total_usd": 0.0, "by_model": {}, "calls": []}
    
    data["total_usd"] += cost
    data["by_model"][model] = data["by_model"].get(model, 0.0) + cost
    data["calls"].append({
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost, 4),
    })
    
    cost_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    
    # 월 한도 체크
    budget = float(os.getenv("MONTHLY_BUDGET_USD", "50"))
    if data["total_usd"] > budget:
        raise RuntimeError(
            f"월 누적 비용 ${data['total_usd']:.2f}이 한도 ${budget}를 초과했습니다.\n"
            f"작업 중단. .env에서 MONTHLY_BUDGET_USD를 늘리거나 다음 달 대기."
        )


def verify_tsv(tsv_text: str) -> dict:
    """TSV 출력 자동 검증"""
    issues = []
    lines = [l for l in tsv_text.strip().split("\n") if l.strip()]
    
    if not lines:
        return {"valid": False, "issues": ["TSV 비어있음"]}
    
    header_cols = len(lines[0].split("\t"))
    
    for i, line in enumerate(lines[1:], 1):
        cols = len(line.split("\t"))
        if cols != header_cols:
            issues.append(f"행 {i}: 컬럼 수 불일치 ({cols} vs {header_cols})")
    
    # 필수 태그 체크 (마지막 컬럼이 태그라 가정) — v3.6 태그 2축
    required_tag_prefixes = ["과목::", "속성::", "난이도::"]
    # 주제::는 사례집(06a/06b)에서 필수, 02-card에서는 카드별로 다를 수 있어 별도 체크
    for i, line in enumerate(lines[1:], 1):
        tag_field = line.split("\t")[-1] if "\t" in line else ""
        missing = [t for t in required_tag_prefixes if t not in tag_field]
        if missing:
            issues.append(f"행 {i}: 필수 태그 누락 {missing}")
        # 구버전 태그 잔존 체크
        if "유형::" in tag_field:
            issues.append(f"행 {i}: 구버전 '유형::' 태그 잔존 → '속성::'로 마이그레이션 필요")
        if "쟁점::" in tag_field:
            issues.append(f"행 {i}: 구버전 '쟁점::' 태그 잔존 → '주제::'로 마이그레이션 필요")
    
    # {불명} / [불명] 토큰 비율 체크 (v3.6은 {불명} 사용, legacy [불명]도 호환)
    bulmyeong_count = tsv_text.count("{불명}") + tsv_text.count("[불명]")
    if bulmyeong_count > len(lines) * 0.5:
        issues.append(f"{{불명}}/[불명] 토큰 과다: {bulmyeong_count}개 (행 {len(lines)}개 대비 50% 초과)")
    
    # legacy [불명] 잔존 경고 (v3.6에서는 {불명} 사용 권장)
    legacy_count = tsv_text.count("[불명]")
    if legacy_count > 0:
        issues.append(f"legacy '[불명]' 토큰 {legacy_count}개 잔존 → v3.6은 '{{불명}}' 사용 권장")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "card_count": len(lines) - 1,
        "bulmyeong_count": bulmyeong_count,
    }


def save_output(content: str, subdir: str, filename: str) -> Path:
    """outputs/{subdir}/{filename}에 저장"""
    out_dir = PACKAGE_ROOT / "outputs" / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    out_path.write_text(content, encoding="utf-8")
    return out_path


def estimate_pages(pdf_path: Path) -> int:
    """PDF 페이지 수"""
    from pypdf import PdfReader
    return len(PdfReader(str(pdf_path)).pages)
