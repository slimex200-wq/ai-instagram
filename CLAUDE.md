# AI CardNews — Instagram

## Commands
- `python cardnews.py --count 4 --output output/` - 카드뉴스 생성 (기본 4장)
- `pytest tests/ -v` - 테스트 실행

## Architecture
소셜(8개)+RSS 수집 → 키워드 필터 → 이미지/본문 크롤링 → Claude API 선별+작성 → HTML→PNG 렌더링 → Instagram 캐러셀

| 파일 | 역할 |
|------|------|
| cardnews.py | 메인 파이프라인 + QA 게이트 + 중복 방지 히스토리 |
| ai_writer.py | Claude API 프롬프트 구성 + JSON 파싱 (Instagram 캡션) |
| card_renderer.py | html2image 기반 1080x1080 카드 렌더링 |
| social_collector.py | 8개 소스 병렬 수집 (last30days 스킬 활용) |
| rss_collector.py | RSS 피드 수집 (보충용) |
| image_fetcher.py | og:image 크롤링 + Pexels 폴백 |
| page_generator.py | GitHub Pages 갤러리 HTML 생성 |

## Conventions
- 카드 구조: card-01(표지) → card-02~N(뉴스) → card-N+1(마무리/QR)
- output/{날짜}/ 에 PNG + caption.txt + links.txt 저장
- history.json으로 최근 3일 기사 중복 방지
- Claude 모델: `claude-sonnet-4-20250514`
- Instagram 캐러셀로 포스팅 (Meta Graph API)

## NEVER
- NEVER 주간 표현 사용 ("한 주", "이번 주", "weekly") -- QA가 자동 reject
- NEVER original_title 필드 수정 -- 이미지 매칭용
- NEVER output/ 내 파일 수동 편집 -- CI가 매일 덮어씀

## ALWAYS
- ALWAYS ai_writer.py 프롬프트 수정 시 QA 검증도 함께 갱신
- ALWAYS 카드 포인트 5번째는 "So What" 분석으로 마무리
- ALWAYS caption에 해시태그 5~8개 포함 -- Instagram 탐색탭 노출
