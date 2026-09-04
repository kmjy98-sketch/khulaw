"""VAULT_ROOT 단일 리졸버 — 경로 하드코딩 디커플(2026-06-21 신설).

목적: 워크스페이스 루트(현재 'E:\\법학볼트', 2026-06-23 H:→E: 컷오버)를 한 곳에서만
정의해, 드라이브 이전·문자변경·미러전환 시 .agent/config/vault.json 한 줄만 고치면
모든 스크립트가 따라오게 한다. (일회성·레거시 스크립트엔 H:\\내 드라이브 하드코딩 잔존 — 쓸 때 그때 전환)

우선순위: 환경변수 VAULT_ROOT > .agent/config/vault.json > 기본값.
기본값이 현 경로와 같으므로 도입만으로는 어떤 동작도 바뀌지 않는다(안전).

사용:
    from _vault import VAULT_ROOT, vp
    idx = vp("sync", "wiki", "_index.md")          # -> 루트\\sync\\wiki\\_index.md
    print(VAULT_ROOT)

신규 스크립트는 루트 경로(E:\\법학볼트 등)를 직접 쓰지 말고 반드시 vp()/VAULT_ROOT 사용.
"""
import os
import json
from pathlib import Path

_DEFAULT = r"E:\법학볼트"


def _resolve_root() -> str:
    env = os.environ.get("VAULT_ROOT")
    if env:
        return env
    cfg = Path(__file__).resolve().parent.parent / "config" / "vault.json"
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
        root = data.get("vault_root")
        if root:
            return root
    except Exception:
        pass
    return _DEFAULT


VAULT_ROOT = _resolve_root()


def vp(*parts: str) -> str:
    """VAULT_ROOT 기준 경로 결합."""
    return os.path.join(VAULT_ROOT, *parts)


if __name__ == "__main__":
    print("VAULT_ROOT =", VAULT_ROOT)
    print("example    =", vp("sync", "wiki", "_index.md"))
