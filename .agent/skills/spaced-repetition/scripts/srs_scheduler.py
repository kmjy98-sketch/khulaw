#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spaced Repetition Scheduler (SM-2 Algorithm)
복습 주기 관리 스크립트
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Windows 콘솔 인코딩
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

STATE_DIR = Path(__file__).resolve().parents[3] / "state"
STATE_FILE = STATE_DIR / "srs_log.json"
LEARNING_FILE = STATE_DIR / "learning.json"
PRIORITY_LEVELS = {
    'low': 0,
    'normal': 1,
    'high': 2,
}


def load_data():
    """SRS 데이터 로드"""
    if not STATE_FILE.exists():
        return {"items": []}
    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_data(data):
    """SRS 데이터 저장"""
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    sync_learning_srs(data)


def load_learning_data():
    """학습 상태 파일 로드"""
    if not LEARNING_FILE.exists():
        return {}
    with open(LEARNING_FILE, 'r', encoding='utf-8-sig') as f:
        return json.load(f)


def sync_learning_srs(data):
    """learning.json의 SRS 스냅샷과 마지막 세션 날짜를 함께 갱신"""
    learning = load_learning_data()
    if not learning:
        return

    learning.setdefault('srs', {})
    learning['srs']['items'] = data.get('items', [])
    learning['last_session'] = datetime.now().strftime('%Y-%m-%d')

    with open(LEARNING_FILE, 'w', encoding='utf-8') as f:
        json.dump(learning, f, ensure_ascii=False, indent=4)


def normalize_priority(value):
    """우선순위 라벨 정규화"""
    if isinstance(value, str):
        lowered = value.lower()
        if lowered in PRIORITY_LEVELS:
            return lowered
    return 'normal'


def normalize_content(value):
    """중복 비교용 텍스트 정규화"""
    if not isinstance(value, str):
        return ''
    return ' '.join(value.split()).strip().lower()


def priority_from_score(score):
    """오답일수록 높은 복습 우선순위 부여"""
    if score is None:
        return 'normal'
    if score <= 2:
        return 'high'
    if score == 3:
        return 'normal'
    return 'low'


def priority_label(item):
    """항목의 표시용 우선순위"""
    explicit = item.get('priority')
    if explicit:
        return normalize_priority(explicit)
    return priority_from_score(item.get('last_score'))


def calculate_next_review(item, score):
    """SM-2 알고리즘으로 다음 복습일 계산"""
    ef = item.get('ef', 2.5)
    interval = item.get('interval', 1)
    repetitions = item.get('repetitions', 0)
    
    if score >= 3:
        # 정답: 간격 증가
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = int(interval * ef)
        repetitions += 1
    else:
        # 오답: 처음부터
        repetitions = 0
        interval = 1
    
    # EF 조정 (0.8 ~ 2.5 범위)
    ef = max(1.3, ef + (0.1 - (5 - score) * (0.08 + (5 - score) * 0.02)))
    
    next_date = (datetime.now() + timedelta(days=interval)).strftime('%Y-%m-%d')
    
    return {
        'ef': round(ef, 2),
        'interval': interval,
        'repetitions': repetitions,
        'next_review': next_date,
        'last_reviewed': datetime.now().strftime('%Y-%m-%d'),
        'last_score': score,
        'priority': priority_from_score(score),
    }


def get_today_items(data):
    """오늘 복습할 항목 반환"""
    today = datetime.now().strftime('%Y-%m-%d')
    due_items = []
    
    for item in data['items']:
        next_review = item.get('next_review', today)
        if next_review <= today:
            due_items.append(item)
    
    return sorted(
        due_items,
        key=lambda item: (
            -PRIORITY_LEVELS[priority_label(item)],
            item.get('next_review', today),
            item.get('repetitions', 0),
            item.get('last_score', 5),
            item.get('id', 0),
        ),
    )


def add_item(data, content, topic, priority, source='manual'):
    """새 항목 추가"""
    new_id = max([i.get('id', 0) for i in data['items']], default=0) + 1
    today = datetime.now().strftime('%Y-%m-%d')
    
    new_item = {
        'id': new_id,
        'content': content,
        'topic': topic,
        'ef': 2.5,
        'interval': 1,
        'repetitions': 0,
        'next_review': today,
        'created': today,
        'priority': normalize_priority(priority),
        'source': source,
    }
    
    data['items'].append(new_item)
    return new_item


def sync_weak_points(data):
    """learning.json의 weak_points를 SRS에 동기화"""
    learning = load_learning_data()
    weak_points = learning.get('weak_points', [])
    topic = learning.get('current_scope', '일반')
    existing_items = {
        normalize_content(item.get('content')): item
        for item in data.get('items', [])
        if item.get('content')
    }

    added_items = []
    promoted_items = []

    for weak_point in weak_points:
        normalized = normalize_content(weak_point)
        if not normalized:
            continue

        existing = existing_items.get(normalized)
        if existing is None:
            item = add_item(data, weak_point, topic, 'high', source='weak_points')
            added_items.append(item)
            existing_items[normalized] = item
            continue

        current_priority = priority_label(existing)
        if PRIORITY_LEVELS[current_priority] < PRIORITY_LEVELS['high']:
            existing['priority'] = 'high'
            promoted_items.append(existing)

        existing.setdefault('source', 'weak_points')

    return added_items, promoted_items


def review_item(data, item_id, score):
    """항목 복습 결과 기록"""
    for item in data['items']:
        if item.get('id') == item_id:
            updates = calculate_next_review(item, score)
            item.update(updates)
            return item
    return None


def main():
    parser = argparse.ArgumentParser(description="Spaced Repetition Scheduler")
    parser.add_argument('--today', action='store_true', help='오늘 복습할 항목')
    parser.add_argument('--add', type=str, help='새 항목 추가')
    parser.add_argument('--topic', type=str, default='일반', help='주제')
    parser.add_argument('--priority', choices=['high', 'normal', 'low'], default='normal', help='복습 우선순위')
    parser.add_argument('--sync-weak-points', action='store_true', help='learning.json의 약점을 SRS에 동기화')
    parser.add_argument('--review', type=int, help='복습할 항목 ID')
    parser.add_argument('--score', type=int, choices=[0,1,2,3,4,5], help='복습 점수 (0-5)')
    parser.add_argument('--status', action='store_true', help='전체 상태')
    
    args = parser.parse_args()
    data = load_data()
    
    if args.today:
        items = get_today_items(data)
        print(f"=== 오늘 복습할 항목: {len(items)}개 ===\n")
        for item in items:
            print(f"[{item['id']}] {item['content']} ({item['topic']}) [{priority_label(item)}]")
            print(f"    EF: {item.get('ef', 2.5)}, 간격: {item.get('interval', 1)}일")
        if not items:
            print("오늘 복습할 항목이 없습니다.")
    
    elif args.add:
        item = add_item(data, args.add, args.topic, args.priority)
        save_data(data)
        print(f"항목 추가됨: [{item['id']}] {item['content']} [{item['priority']}]")

    elif args.sync_weak_points:
        added_items, promoted_items = sync_weak_points(data)
        save_data(data)
        print(f"약점 동기화 완료: 추가 {len(added_items)}개, 우선순위 상향 {len(promoted_items)}개")
        for item in added_items:
            print(f"  + [{item['id']}] {item['content']} [{item['priority']}]")
        for item in promoted_items:
            print(f"  ^ [{item['id']}] {item['content']} [{item['priority']}]")
    
    elif args.review is not None and args.score is not None:
        item = review_item(data, args.review, args.score)
        if item:
            save_data(data)
            print(f"복습 기록됨: [{item['id']}] {item['content']}")
            print(f"  다음 복습: {item['next_review']} ({item['interval']}일 후)")
        else:
            print(f"항목을 찾을 수 없습니다: {args.review}")
    
    elif args.status:
        print(f"=== SRS 상태 ===")
        print(f"총 항목: {len(data['items'])}개")
        today_count = len(get_today_items(data))
        print(f"오늘 복습: {today_count}개")
        
        # 주제별 통계
        topics = {}
        for item in data['items']:
            t = item.get('topic', '일반')
            topics[t] = topics.get(t, 0) + 1
        print(f"\n주제별:")
        for t, c in topics.items():
            print(f"  {t}: {c}개")

        priorities = {'high': 0, 'normal': 0, 'low': 0}
        for item in data['items']:
            priorities[priority_label(item)] += 1
        print(f"\n우선순위별:")
        for label in ['high', 'normal', 'low']:
            print(f"  {label}: {priorities[label]}개")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
