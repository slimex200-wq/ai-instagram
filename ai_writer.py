"""AI 카드뉴스 콘텐츠 생성 모듈 — Instagram 캐러셀 전용."""

import json
import re
from datetime import date
import anthropic
from config import ANTHROPIC_API_KEY, MODEL


def build_prompt(articles, select_count=None, used_titles=None):
    """Instagram 카드뉴스 프롬프트."""
    articles_text = _format_articles(articles)

    selection_instruction = ""
    if select_count and len(articles) > select_count:
        selection_instruction = f"""
먼저 아래 {len(articles)}개 기사 중 가장 중요하고 흥미로운 {select_count}개를 선별해주세요.
선별 기준: AI 업계에 미치는 영향력, 독자 관심도, 정보의 신선도
선별된 {select_count}개 기사만 카드뉴스로 변환해주세요.
"""

    history_instruction = _build_history_instruction(used_titles)

    return f"""{selection_instruction}{history_instruction}당신은 AI/테크 업계 시니어 에디터입니다. 아래 기사들을 한국어 인스타그램 카드뉴스로 변환해주세요.
이 카드뉴스는 **AI Daily** — 매일 발행되는 일간 뉴스레터입니다.

## 톤 & 스타일
- 업계 전문가가 동료에게 브리핑하는 느낌
- 반드시 구체적 수치, 금액, 날짜, 인물명을 포함할 것
- "폭발적 증가", "절호의 기회" 같은 빈 수식어 금지
- "한 주", "이번 주", "this week" 등 주간 표현 절대 금지 — "오늘", "최근" 등 일간 표현만 사용
- 마지막 포인트는 반드시 "왜 중요한지" 분석 (So What)으로 마무리

## 각 기사에 대해:
- title: 임팩트 있는 제목 (15자 이내, 한국어)
- subtitle: 핵심 맥락 한 줄 (25자 이내, 한국어)
- points: 핵심 포인트 5개 (각 35자 이내, 한국어)
  - 1~3번째: 구체적 팩트 (수치, 인물, 날짜 포함)
  - 4번째: 업계 영향 또는 파급 효과
  - 5번째: "왜 주목해야 하는가" 에디터 관점 분석
- insight: 에디터 한줄평 (30자 이내, 독자에게 시사점)
- source: 출처명
- link: 원문 URL (기사의 Link 필드 그대로 사용)
- keywords: 이 기사의 핵심 키워드 1~2개 (표지에 사용)
- original_title: 원본 기사의 Title 필드를 그대로 복사 (이미지 매칭에 사용, 절대 수정 금지)

## 추가 생성 항목:
- cover_headline: 이번 회차의 핵심 트렌드를 담은 표지 헤드라인 (20자 이내, 한국어, 예: "AI가 제조업을 삼킨다")
- trend_summary: 선별된 기사들을 관통하는 공통 트렌드 한 문장 (40자 이내)
- caption: Instagram 캐러셀 캡션. 아래 규칙을 반드시 따를 것:
  - 첫 1~2줄: 오늘 뉴스 중 가장 임팩트 있는 팩트로 시작 (호기심 유발)
  - 중간: 오늘 다룬 주요 뉴스 2~3개를 "- " 불릿으로 한 줄씩 요약
  - 마무리: "저장해두고 나중에 다시 보세요" 또는 저장/공유 유도 문구
  - 맨 끝 3줄: 관련 해시태그 5~8개 (예: #AI뉴스 #인공지능 #ChatGPT #테크트렌드 #AIDaily)
  - 톤: 전문가가 동료에게 브리핑하는 ~합니다/~입니다 존댓말
  - 총 400~600자 이내 (해시태그 포함)
  - 원문 링크 포함하지 말 것

JSON 형식으로 응답해주세요:
{{
  "cover_headline": "표지 헤드라인",
  "cover_date": "{date.today().isoformat()}",
  "trend_summary": "오늘의 AI 트렌드 한 줄 요약",
  "cards": [
    {{
      "number": 1, "original_title": "원문 기사 Title 그대로 복사",
      "title": "...",
      "subtitle": "...",
      "points": ["팩트1", "팩트2", "팩트3", "영향", "So What"],
      "insight": "에디터 한줄평",
      "source": "...",
      "link": "https://...",
      "keywords": ["키워드1"]
    }}
  ],
  "closing_message": "읽어주셔서 감사합니다",
  "caption": "첫줄 후킹\\n\\n- 뉴스1 요약\\n- 뉴스2 요약\\n\\n저장해두고 나중에 다시 보세요\\n\\n#AI뉴스 #인공지능 #ChatGPT #테크트렌드 #AIDaily"
}}

기사들:
{articles_text}"""


def _format_articles(articles):
    text = ""
    for i, a in enumerate(articles, 1):
        text += f"\n### Article {i}\n"
        text += f"Title: {a['title']}\n"
        text += f"Summary: {a['summary']}\n"
        if a.get('body'):
            text += f"Body (excerpt): {a['body']}\n"
        text += f"Source: {a['source']}\n"
        text += f"Link: {a.get('link', '')}\n"
    return text


def _build_history_instruction(used_titles):
    if not used_titles:
        return ""
    titles_list = "\n".join(f"- {t}" for t in used_titles[:12])
    return f"""
## 중복 방지 (필수)
아래는 최근 며칠간 이미 다룬 기사 제목입니다. **같은 주제, 같은 사건, 같은 인물/회사에 대한 기사는 반드시 제외**해주세요.
URL이 다르더라도 동일한 이벤트를 다룬 기사는 중복입니다.
{titles_list}
"""


def _parse_response(text):
    text = text.strip()
    code_block = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
    if code_block:
        text = code_block.group(1).strip()
    else:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)
    return json.loads(text)


def generate_card_content(articles, select_count=None, used_titles=None):
    """카드뉴스 콘텐츠 생성."""
    prompt = build_prompt(articles, select_count, used_titles)
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )
    response_text = message.content[0].text
    try:
        return _parse_response(response_text)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[경고] JSON 파싱 실패, 재시도 중... ({e})")
        message = client.messages.create(
            model=MODEL,
            max_tokens=3000,
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response_text},
                {"role": "user", "content": "JSON 형식이 올바르지 않습니다. 올바른 JSON으로 다시 응답해주세요."},
            ],
        )
        return _parse_response(message.content[0].text)
