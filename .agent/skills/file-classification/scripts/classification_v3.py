#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File-classification v3 entrypoint.

Key guarantees:
- Domain separation: legal vs admission
- Global protected-root guard
- Dry-run by default
- Lock registry support:
  - mark complete (relative_path + mtime)
  - unlock-file only
"""

from __future__ import annotations

import argparse
import datetime as dt
import getpass
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

_p = os.path.abspath(__file__)
while os.path.basename(_p) != ".agent" and os.path.dirname(_p) != _p:
    _p = os.path.dirname(_p)
sys.path.insert(0, os.path.join(_p, "scripts"))
from _vault import VAULT_ROOT, vp  # noqa: E402


LEGAL_ROOTS = ["1.민사", "2.형사", "3.공법", "4.선택법"]
OTHER_ARCHIVE_ROOT_PRIMARY = "5.기타"
OTHER_ARCHIVE_ROOT_FALLBACK = "기타"
OTHER_ARCHIVE_TOKEN = "__OTHER_ARCHIVE__"
ADMISSION_ROOT = "9.로스쿨입시"
INBOX_ROOT = Path("5.기타") / "_inbox"
RAG_DATA_ROOT = Path("5.기타") / "_RAG_데이터"
TRASH_ROOT = Path("5.기타") / "_trash"
TEXTBOOK_ONLY_DIR = "교재"
ROOT_EXAM_DIR = "90.기출"
ROOT_ARCHIVE_DIR = "91.보관"
ROOT_CONCEPT_DIR = "92.개념"
ROOT_REFERENCE_DIR = "93.참고"
ROOT_TEXTBOOK_DIR = "94.교재"
HWP_ORIGINAL_DIR = Path("_원본보관") / "hwp_전체"

# "6.원본" is an alias used in policy docs.
ALIAS_ROOTS = {"6.원본": "_원본보관"}

GLOBAL_PROTECTED_ROOTS = [
    "0.공유드라이브",
    "공유드라이브",
    ".agent",
    TRASH_ROOT.as_posix(),
    RAG_DATA_ROOT.as_posix(),
    "_원본보관",
]

LOCK_FILE_REL = Path(".agent") / "state" / "classification_lock.json"


LEGAL_KEYWORDS = {
    "1.민사": [
        "민법",
        "민사",
        "민소",
        "채권",
        "물권",
        "가족법",
        "송영곤",
        "강혜림",
        "전경운",
    ],
    "2.형사": ["형사", "형법", "형소", "범죄", "김기용", "서보학"],
    "3.공법": ["공법", "헌법", "헌1", "헌법원리", "행정법", "강성민", "이진", "헌마", "헌가", "헌다", "헌나"],
    "4.선택법": ["선택법", "국제법", "노동법", "조세법", "지재권", "법조윤리"],
}

LEET_KEYWORDS = [
    "leet",
    "리트",
    "언어이해",
    "추리논증",
    "논리",
]

ADMISSION_KEYWORDS = LEET_KEYWORDS + [
    "입시",
    "자소서",
    "자기소개서",
    "면접",
    "학업계획서",
    "지원동기",
    "로스쿨 입시",
]

LEGAL_EXCLUDE_ADMISSION_KEYWORDS = tuple(ADMISSION_KEYWORDS)

COMMON_EXAM_KEYWORDS = {
    "변호사시험",
    "변시",
    "모의시험",
}

# 5.기타/_inbox is temporary workspace (especially transcription pipeline).
INBOX_TEMP_TOP_DIRS = {"녹음", "transcribe", "transcription", "whisper"}
INBOX_TEMP_DIRS = {"processed", "output", "cache", "tmp", "temp"}
INBOX_TEMP_EXTS = {".m4a", ".mp3", ".wav", ".json", ".txt"}

# Files that look like standalone textbook materials are routed to
# "{subject}/94.교재/" rather than "{subject}/91.보관/".
TEXTBOOK_ONLY_EXTS = {".pdf", ".zip"}
TEXTBOOK_ONLY_KEYWORDS = {
    "교재",
    "교안",
    "강의자료",
    "보충자료",
    "기본서",
    "기본편",
    "사례연습",
    "논점",
    "목차",
    "요론",
    "반반형법",
    "민법의맥",
}
NON_TEXTBOOK_HINTS = {
    "기출",
    "중간",
    "기말",
    "모의",
    "모답",
    "답안",
    "정리",
    "요약",
    "노트",
    "전사",
    "transcript",
    "_part",
}

# Instructor-specific routing overrides for ongoing tracks.
SEOBOTOK_ONGOING_TOKENS = {"형1", "기초이론_1", "형법총론"}
SEOBOTOK_ARCHIVE_TOKENS = {"형2", "기초이론_2", "형법각론", "형소", "형사소송법"}
KIMGIYONG_ONGOING_TOKENS = {"김기용"}
HONGHYEONGCHEOL_ONGOING_TOKENS = {"홍형철"}
KIMSEONGDON_ONGOING_TOKENS = {"김성돈"}
KANGSEONGMIN_ONGOING_TOKENS = {"강성민"}
IJIN_ONGOING_TOKENS = {"이진", "헌법1", "헌법원리1", "헌1"}
LAW_ETHICS_ONGOING_TOKENS = {"법조윤리"}
INTL_LAW_ONGOING_TOKENS = {"국제법총론", "국제법"}
CONSTITUTIONAL_CASE_RE = re.compile(r"\d{4}헌(?:마|가|다|나)\d+", re.IGNORECASE)
EXTRACT_MD_RE = re.compile(r"_p\d{3}-\d{3}(?:_\d{2})?\.md$", re.IGNORECASE)

TEXTBOOK_ROUTE_RULES = [
    {
        "tokens": ("논점민법강의_",),
        "target": Path("1.민사") / "30.송영곤_기본민법",
    },
    {
        "tokens": ("basic민법_daily_test_",),
        "target": Path("1.민사") / "30.송영곤_기본민법",
    },
    {
        "tokens": ("민사법쟁점노트_",),
        "target": Path("1.민사") / "33.송영곤_쟁노",
    },
    {
        "tokens": ("송영곤_사례연습_",),
        "target": Path("1.민사") / "31.송영곤_사례",
    },
    {
        "tokens": ("민사법사례연습2_", "송영곤_사례연습2_", "송영곤_민사법사례연습2_"),
        "target": Path("1.민사") / "32.송영곤_사례연습2",
    },
    {
        "tokens": ("민법강의_",),
        "target": Path("1.민사") / "10.강혜림_민법1",
    },
    {
        "tokens": ("전경운_민법_물총_", "민법의_기초이론_3_전경운_교재_"),
        "target": Path("1.민사") / "20.전경운_민법3",
    },
    {
        "tokens": ("민법의_기초이론_2_전경운_교재_",),
        "target": Path("1.민사") / ROOT_ARCHIVE_DIR / "전경운_민법2",
    },
    {
        "tokens": ("곽낙규_민법사례연습_", "민법사례연습_", "2025_곽낙규_민사례_ocr_"),
        "target": Path("1.민사") / ROOT_ARCHIVE_DIR / "곽낙규_사례연습",
    },
    {
        "tokens": ("기본사례의맥_",),
        "target": Path("1.민사") / ROOT_ARCHIVE_DIR / "윤동환_민법의맥",
    },
    {
        "tokens": ("민법의맥_",),
        "target": Path("1.민사") / ROOT_ARCHIVE_DIR / "윤동환_민법의맥",
    },
    {
        "tokens": ("민법의해석_",),
        "target": Path("1.민사") / ROOT_ARCHIVE_DIR / "참고",
    },
    {
        "tokens": (
            "박승수_민법기본사례_",
            "박승수_기본사례_민법기본사례_",
            "민법기본사례_",
            "talkfile_민법사례연습_박승수.pdf_",
        ),
        "target": Path("1.민사") / ROOT_ARCHIVE_DIR / "박승수_민법기본사례",
    },
]

EXAM_ROUTE_RULES = [
    {
        "tokens": ("민법의_기초이론_3_전경운_", "민3_전경운_"),
        "target": Path("1.민사") / "20.전경운_민법3" / "기출",
    },
    {
        "tokens": ("민법의_기초이론_2_전경운_", "민2_전경운_"),
        "target": Path("1.민사") / ROOT_ARCHIVE_DIR / "전경운_민법2" / "기출",
    },
    {
        "tokens": ("민법의_기초이론_2_강혜림교수님_", "민2_강혜림교수님_"),
        "target": Path("1.민사") / ROOT_ARCHIVE_DIR / "강혜림_민법2" / "기출",
    },
    {
        "tokens": ("민법의_기초이론_2_박수곤_", "민2_박수곤_"),
        "target": Path("1.민사") / ROOT_ARCHIVE_DIR / "박수곤_민법2" / "기출",
    },
    {
        "tokens": ("민법의_기초이론_2_박설아_", "민2_박설아_"),
        "target": Path("1.민사") / ROOT_ARCHIVE_DIR / "채담_박설아" / "기출",
    },
    {
        "tokens": ("민법의_기초이론_1_박수곤_", "민법1_박수곤_"),
        "target": Path("1.민사") / ROOT_ARCHIVE_DIR / "박수곤_민법1" / "기출",
    },
    {
        "tokens": ("민법의_기초이론_1_최광준_", "민법1_최광준_"),
        "target": Path("1.민사") / ROOT_ARCHIVE_DIR / "최광준_민법1" / "기출",
    },
    {
        "tokens": ("민법의_기초이론_3_서인겸_", "민3_서인겸_"),
        "target": Path("1.민사") / ROOT_ARCHIVE_DIR / "서인겸_민법3" / "기출",
    },
    {
        "tokens": ("민사소송법_종합_이수진_",),
        "target": Path("1.민사") / ROOT_ARCHIVE_DIR / "이수진_민사소송법_종합" / "기출",
    },
    {
        "tokens": ("민소기_범경철_",),
        "target": Path("1.민사") / ROOT_ARCHIVE_DIR / "민소_범경철" / "기출",
    },
    {
        "tokens": ("민사법_변시모의_",),
        "target": Path("1.민사") / ROOT_EXAM_DIR,
    },
]

SPECIAL_MATERIAL_ROUTE_RULES = [
    {
        "tokens": ("민법의맥_", "윤동환_민법의맥_"),
        "markers": ("필기노트", "회차_필기"),
        "target": Path("1.민사") / ROOT_ARCHIVE_DIR / "윤동환_민법의맥" / "필기",
    },
    {
        "tokens": ("민법의맥_", "윤동환_민법의맥_"),
        "markers": ("선행학습_가이드", "선행학습가이드", "강의계획서"),
        "target": Path("1.민사") / ROOT_ARCHIVE_DIR / "윤동환_민법의맥" / "강의자료",
    },
    {
        "tokens": ("민법의맥_", "민법_윤동환_", "3-2_민법_윤동환_", "3-3_민법_윤동환_", "3-4_민법_윤동환_"),
        "markers": ("모의", "채점평", "해설"),
        "target": Path("1.민사") / ROOT_ARCHIVE_DIR / "윤동환_민법의맥" / "기출",
    },
]


@dataclass(frozen=True)
class Policy:
    root: Path
    legal_roots: Tuple[Path, ...]
    other_archive_root: Path
    admission_root: Path
    inbox_root: Path
    global_protected_roots: Tuple[Path, ...]
    lock_file: Path


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def resolve_path(raw: str, root: Path) -> Path:
    p = Path(raw)
    if not p.is_absolute():
        p = (root / p).resolve()
    else:
        p = p.resolve()
    return p


def to_rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def load_policy(root_raw: str) -> Policy:
    root = Path(root_raw).resolve()
    legal_roots = tuple((root / name).resolve() for name in LEGAL_ROOTS)
    protected = sorted(set(list(GLOBAL_PROTECTED_ROOTS) + list(ALIAS_ROOTS.values())))
    global_protected_roots = tuple((root / name).resolve() for name in protected)
    other_primary = (root / OTHER_ARCHIVE_ROOT_PRIMARY).resolve()
    other_fallback = (root / OTHER_ARCHIVE_ROOT_FALLBACK).resolve()
    if other_primary.exists():
        other_archive_root = other_primary
    elif other_fallback.exists():
        other_archive_root = other_fallback
    else:
        other_archive_root = other_primary
    return Policy(
        root=root,
        legal_roots=legal_roots,
        other_archive_root=other_archive_root,
        admission_root=(root / ADMISSION_ROOT).resolve(),
        inbox_root=(root / INBOX_ROOT).resolve(),
        global_protected_roots=global_protected_roots,
        lock_file=(root / LOCK_FILE_REL).resolve(),
    )


def load_lock_registry(path: Path) -> Dict[str, dict]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    locks = data.get("locks", [])
    out: Dict[str, dict] = {}
    for entry in locks:
        rel = entry.get("relative_path")
        if isinstance(rel, str) and rel:
            out[rel] = entry
    return out


def save_lock_registry(path: Path, locks: Dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated_at": now_iso(),
        "locks": [locks[k] for k in sorted(locks.keys())],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def current_mtime(path: Path) -> float:
    return path.stat().st_mtime


def is_global_protected(path: Path, policy: Policy) -> bool:
    rp = path.resolve()
    return any(is_relative_to(rp, base) for base in policy.global_protected_roots if base.exists())


def in_domain_scope(path: Path, domain: str, policy: Policy) -> bool:
    rp = path.resolve()
    if domain == "legal":
        if is_relative_to(rp, policy.inbox_root):
            return True
        if is_relative_to(rp, policy.other_archive_root):
            return True
        return any(is_relative_to(rp, base) for base in policy.legal_roots if base.exists())
    if domain == "admission":
        return is_relative_to(rp, policy.inbox_root) or is_relative_to(rp, policy.admission_root)
    return False


def has_any_keyword(filename: str, keywords: Iterable[str]) -> bool:
    lower = filename.lower()
    return any(k.lower() in lower for k in keywords)


def is_textbook_only_file(filename: str) -> bool:
    lower = filename.lower()
    suffix = Path(filename).suffix.lower()
    if suffix not in TEXTBOOK_ONLY_EXTS:
        return False
    if any(hint in lower for hint in NON_TEXTBOOK_HINTS):
        return False
    return any(hint in lower for hint in TEXTBOOK_ONLY_KEYWORDS)


def is_common_exam_file(filename: str) -> bool:
    lower = filename.lower()
    return any(token in lower for token in COMMON_EXAM_KEYWORDS)


def is_extract_markdown_file(src: Path) -> bool:
    return src.suffix.lower() == ".md" and EXTRACT_MD_RE.search(src.name) is not None


def compute_textbook_route_destination(src: Path, root_name: str, policy: Policy) -> Optional[Path]:
    lower = src.name.lower()
    if root_name != "1.민사":
        return None

    subdir: Optional[str] = None
    if is_extract_markdown_file(src):
        subdir = "교재_추출"
    elif src.suffix.lower() in TEXTBOOK_ONLY_EXTS:
        subdir = TEXTBOOK_ONLY_DIR
    else:
        return None

    for rule in TEXTBOOK_ROUTE_RULES:
        if any(token in lower for token in rule["tokens"]):
            return (policy.root / rule["target"] / subdir / src.name).resolve()
    return None


def compute_exam_route_destination(src: Path, root_name: str, policy: Policy) -> Optional[Path]:
    if root_name != "1.민사":
        return None
    lower = src.name.lower()
    exam_markers = ("중간", "기말", "고사", "모답", "답안", "채점기준표", "해설", "변시모의")
    if not any(marker in lower for marker in exam_markers):
        return None
    for rule in EXAM_ROUTE_RULES:
        if any(token in lower for token in rule["tokens"]):
            return (policy.root / rule["target"] / src.name).resolve()
    return None


def compute_special_material_destination(src: Path, root_name: str, policy: Policy) -> Optional[Path]:
    if root_name != "1.민사":
        return None
    lower = src.name.lower()
    for rule in SPECIAL_MATERIAL_ROUTE_RULES:
        if any(token in lower for token in rule["tokens"]) and any(marker in lower for marker in rule["markers"]):
            return (policy.root / rule["target"] / src.name).resolve()
    return None


def compute_legal_override_destination(filename: str, root_name: str, policy: Policy) -> Optional[Path]:
    lower = filename.lower()

    if root_name == "2.형사" and any(t in lower for t in KIMGIYONG_ONGOING_TOKENS):
        return (policy.root / root_name / "10.김기용_형법교안" / filename).resolve()

    # 서보학 자료는 형법1/형법2를 분리 관리.
    # 형법1은 루트 진행 강의, 형법2는 보관으로 라우팅.
    if root_name == "2.형사" and "서보학" in lower:
        if any(t in lower for t in SEOBOTOK_ONGOING_TOKENS):
            return (policy.root / root_name / "20.서보학_형법1" / filename).resolve()
        if any(t in lower for t in SEOBOTOK_ARCHIVE_TOKENS):
            return (policy.root / root_name / ROOT_ARCHIVE_DIR / "서보학_형법2" / filename).resolve()

    # 홍형철 기본형법은 루트 진행 강의 폴더로 분류.
    if root_name == "2.형사" and any(t in lower for t in HONGHYEONGCHEOL_ONGOING_TOKENS):
        return (policy.root / root_name / "30.홍형철_기본형법" / filename).resolve()

    if root_name == "2.형사" and any(t in lower for t in KIMSEONGDON_ONGOING_TOKENS):
        return (policy.root / root_name / "40.김성돈_형법총론" / filename).resolve()

    # 헌마/헌가/헌다/헌나는 이진 교수님 헌법원리 1 판례로 분류.
    if root_name == "3.공법" and CONSTITUTIONAL_CASE_RE.search(filename):
        return (policy.root / root_name / "10.이진_헌법원리1" / "판례" / filename).resolve()

    # 강성민 교수님 행정법 자료는 루트 진행 강의 폴더로 분류.
    if root_name == "3.공법" and any(t in lower for t in KANGSEONGMIN_ONGOING_TOKENS):
        return (policy.root / root_name / "20.강성민_행정법" / filename).resolve()

    # 이진 교수님 헌법원리 1 자료는 루트 진행 강의 폴더로 분류.
    if root_name == "3.공법" and any(t in lower for t in IJIN_ONGOING_TOKENS):
        return (policy.root / root_name / "10.이진_헌법원리1" / filename).resolve()

    if root_name == "4.선택법" and any(t in lower for t in LAW_ETHICS_ONGOING_TOKENS):
        return (policy.root / root_name / "10.법조윤리" / filename).resolve()

    if root_name == "4.선택법" and any(t in lower for t in INTL_LAW_ONGOING_TOKENS):
        return (policy.root / root_name / "20.국제법총론" / filename).resolve()

    return None


def classify_legal(filename: str) -> Optional[str]:
    # Admission-specific files are out of legal domain.
    if has_any_keyword(filename, LEGAL_EXCLUDE_ADMISSION_KEYWORDS):
        return None
    lower = filename.lower()
    for root_name, keywords in LEGAL_KEYWORDS.items():
        if any(k.lower() in lower for k in keywords):
            return root_name
    return OTHER_ARCHIVE_TOKEN


def classify_admission(filename: str) -> Optional[str]:
    # Admission domain only accepts explicit admission/LEET hints.
    if not has_any_keyword(filename, ADMISSION_KEYWORDS):
        return None
    lower = filename.lower()
    if any(k in lower for k in LEET_KEYWORDS):
        return "LEET"
    return "입시"


def is_inbox_temp_file(src: Path, policy: Policy) -> bool:
    rp = src.resolve()
    if not is_relative_to(rp, policy.inbox_root):
        return False
    rel = rp.relative_to(policy.inbox_root)
    parts = [p.lower() for p in rel.parts]
    if not parts:
        return False
    if parts[0] in INBOX_TEMP_TOP_DIRS:
        return True
    if any(p in INBOX_TEMP_DIRS for p in parts):
        return True
    if src.suffix.lower() in INBOX_TEMP_EXTS and any(p in INBOX_TEMP_TOP_DIRS for p in parts):
        return True
    return False


def ensure_unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    idx = 1
    candidate = parent / f"{stem}_{idx}{suffix}"
    while candidate.exists():
        idx += 1
        candidate = parent / f"{stem}_{idx}{suffix}"
    return candidate


def log_status(code: str, source: str = "-", target: str = "-", note: str = "") -> None:
    print(f"{code}\t{source}\t{target}\t{note}")


def apply_unlocks(
    unlock_files: Iterable[str],
    locks: Dict[str, dict],
    policy: Policy,
    domain: str,
    execute: bool,
) -> Tuple[int, int]:
    planned = 0
    done = 0
    for raw in unlock_files:
        target = resolve_path(raw, policy.root)
        if not target.exists():
            log_status("SKIP_NOT_FOUND", raw, "-", "unlock target not found")
            continue
        if not in_domain_scope(target, domain, policy):
            log_status("SKIP_DOMAIN", raw, "-", f"{domain} scope only")
            continue
        if is_global_protected(target, policy):
            log_status("SKIP_PROTECTED", raw, "-", "global protected root")
            continue
        rel = to_rel(target, policy.root)
        if rel not in locks:
            log_status("SKIP_UNLOCK_MISSING", rel, "-", "not locked")
            continue
        planned += 1
        if execute:
            locks.pop(rel, None)
            done += 1
            log_status("UNLOCKED", rel, "-", "explicit unlock")
        else:
            log_status("PLAN_UNLOCK", rel, "-", "dry-run")
    return planned, done


def apply_marks(
    mark_files: Iterable[str],
    locks: Dict[str, dict],
    policy: Policy,
    domain: str,
    execute: bool,
    note: str,
) -> Tuple[int, int]:
    planned = 0
    done = 0
    user = getpass.getuser()
    for raw in mark_files:
        target = resolve_path(raw, policy.root)
        if not target.exists() or not target.is_file():
            log_status("SKIP_NOT_FOUND", raw, "-", "mark target not found")
            continue
        if not in_domain_scope(target, domain, policy):
            log_status("SKIP_DOMAIN", raw, "-", f"{domain} scope only")
            continue
        if is_global_protected(target, policy):
            log_status("SKIP_PROTECTED", raw, "-", "global protected root")
            continue
        rel = to_rel(target, policy.root)
        entry = {
            "relative_path": rel,
            "mtime": current_mtime(target),
            "domain": domain,
            "completed_at": now_iso(),
            "completed_by": user,
            "note": note or "",
        }
        planned += 1
        if execute:
            locks[rel] = entry
            done += 1
            log_status("LOCKED", rel, "-", "mark-complete")
        else:
            log_status("PLAN_LOCK", rel, "-", "dry-run")
    return planned, done


def compute_destination(src: Path, domain: str, policy: Policy) -> Optional[Path]:
    if src.suffix.lower() in {".hwp", ".hwpx"}:
        return (policy.root / HWP_ORIGINAL_DIR / src.name).resolve()
    if domain == "legal":
        root_name = classify_legal(src.name)
        if root_name is None:
            return None
        special_route_dst = compute_special_material_destination(src, root_name, policy)
        if special_route_dst is not None:
            return special_route_dst
        textbook_route_dst = compute_textbook_route_destination(src, root_name, policy)
        if textbook_route_dst is not None:
            return textbook_route_dst
        exam_route_dst = compute_exam_route_destination(src, root_name, policy)
        if exam_route_dst is not None:
            return exam_route_dst
        override_dst = compute_legal_override_destination(src.name, root_name, policy)
        if override_dst is not None:
            return override_dst
        if root_name == OTHER_ARCHIVE_TOKEN:
            return (policy.other_archive_root / "보관" / src.name).resolve()
        if is_common_exam_file(src.name):
            return (policy.root / root_name / ROOT_EXAM_DIR / src.name).resolve()
        if is_textbook_only_file(src.name):
            return (policy.root / root_name / ROOT_TEXTBOOK_DIR / src.name).resolve()
        return (policy.root / root_name / ROOT_ARCHIVE_DIR / src.name).resolve()
    bucket = classify_admission(src.name)
    if bucket is None:
        return None
    return (policy.admission_root / bucket / "보관" / src.name).resolve()


def plan_classification(
    policy: Policy,
    domain: str,
    execute: bool,
    respect_lock: bool,
    include_inbox_temp: bool,
    locks: Dict[str, dict],
) -> Tuple[int, int, int]:
    if not policy.inbox_root.exists():
        log_status("SKIP_NO_INBOX", "-", "-", str(policy.inbox_root))
        return 0, 0, 0

    planned = 0
    moved = 0
    skipped = 0
    candidates = sorted([p for p in policy.inbox_root.rglob("*") if p.is_file()])

    for src in candidates:
        if is_global_protected(src, policy):
            log_status("SKIP_PROTECTED", to_rel(src, policy.root), "-", "global protected root")
            skipped += 1
            continue

        if not include_inbox_temp and is_inbox_temp_file(src, policy):
            log_status("SKIP_INBOX_TEMP", to_rel(src, policy.root), "-", "temporary transcription/inbox file")
            skipped += 1
            continue

        rel = to_rel(src, policy.root)
        lock = locks.get(rel)
        if respect_lock and lock:
            mtime = current_mtime(src)
            if float(lock.get("mtime", -1)) == float(mtime):
                log_status("SKIP_LOCKED", rel, "-", f"domain={lock.get('domain', '')}")
                skipped += 1
                continue
            log_status("REVIEW_REQUIRED(mtime_changed)", rel, "-", "lock invalidated by mtime")

        dst = compute_destination(src, domain, policy)
        if dst is None:
            log_status("SKIP_DOMAIN", rel, "-", f"{domain} keyword mismatch")
            skipped += 1
            continue
        dst = ensure_unique_path(dst)
        if src.resolve() == dst.resolve():
            log_status("SKIP_SAME", rel, rel, "")
            skipped += 1
            continue
        if is_global_protected(dst, policy):
            log_status("SKIP_PROTECTED", rel, to_rel(dst, policy.root), "target in protected root")
            skipped += 1
            continue

        planned += 1
        if execute:
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(src), str(dst))
                moved += 1
                log_status("MOVED", rel, to_rel(dst, policy.root), f"domain={domain}")
                # moving a path invalidates existing lock by source rel
                locks.pop(rel, None)
            except Exception as exc:
                skipped += 1
                log_status("ERROR_MOVE", rel, to_rel(dst, policy.root), str(exc))
        else:
            log_status("PLAN_MOVE", rel, to_rel(dst, policy.root), f"domain={domain}")

    return planned, moved, skipped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="file-classification v3")
    parser.add_argument("--root", default=VAULT_ROOT, help="workspace root")
    parser.add_argument("--domain", choices=["legal", "admission"], default="legal")
    parser.add_argument("--execute", action="store_true", help="apply changes")
    parser.add_argument("--dry-run", action="store_true", help="explicit dry-run")
    parser.add_argument("--mark-complete", action="append", default=[], help="mark file as completed/locked")
    parser.add_argument("--mark-complete-note", default="", help="note for lock entry")
    parser.add_argument("--unlock-file", action="append", default=[], help="unlock file path")
    parser.add_argument("--respect-lock", dest="respect_lock", action="store_true", default=True)
    parser.add_argument("--no-respect-lock", dest="respect_lock", action="store_false")
    parser.add_argument(
        "--include-inbox-temp",
        action="store_true",
        help="include temporary inbox/transcription pipeline files",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    policy = load_policy(args.root)
    execute = bool(args.execute)

    print("=== file-classification v3 ===")
    print(f"mode={'EXECUTE' if execute else 'DRY-RUN'}")
    print(f"root={policy.root}")
    print(f"domain={args.domain}")
    print(f"respect_lock={args.respect_lock}")
    print(f"include_inbox_temp={args.include_inbox_temp}")
    print(f"legal_roots={[p.name for p in policy.legal_roots]}")
    print(f"other_archive_root={policy.other_archive_root.name}/보관")
    print(f"admission_root={policy.admission_root.name}")
    print(f"global_protected_roots={[p.name for p in policy.global_protected_roots]}")
    print(f"lock_file={policy.lock_file}")
    print("status\tsource\ttarget\tnote")

    locks = load_lock_registry(policy.lock_file)
    initial_lock_count = len(locks)

    unlock_planned, unlock_done = apply_unlocks(
        unlock_files=args.unlock_file,
        locks=locks,
        policy=policy,
        domain=args.domain,
        execute=execute,
    )

    mark_planned, mark_done = apply_marks(
        mark_files=args.mark_complete,
        locks=locks,
        policy=policy,
        domain=args.domain,
        execute=execute,
        note=args.mark_complete_note,
    )

    planned, moved, skipped = plan_classification(
        policy=policy,
        domain=args.domain,
        execute=execute,
        respect_lock=args.respect_lock,
        include_inbox_temp=args.include_inbox_temp,
        locks=locks,
    )

    if execute and (unlock_done > 0 or mark_done > 0 or len(locks) != initial_lock_count):
        save_lock_registry(policy.lock_file, locks)
    elif execute and not policy.lock_file.exists() and len(locks) > 0:
        save_lock_registry(policy.lock_file, locks)

    print("\n=== summary ===")
    print(f"planned_moves={planned}")
    print(f"moved={moved}")
    print(f"skipped={skipped}")
    print(f"unlock_planned={unlock_planned}")
    print(f"unlock_done={unlock_done}")
    print(f"mark_planned={mark_planned}")
    print(f"mark_done={mark_done}")
    print(f"locks_before={initial_lock_count}")
    print(f"locks_after={len(locks)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
