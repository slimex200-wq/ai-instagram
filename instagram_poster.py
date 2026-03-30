"""Instagram 캐러셀 포스팅 모듈.

GitHub Actions에서 카드뉴스 생성 후 Meta Graph API로 Instagram에 포스팅.
기존 워크플로우의 인라인 Python을 모듈로 분리.

Usage:
    python instagram_poster.py --date 2026-03-30 --base-url https://user.github.io/ai-instagram
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
import time

import httpx

GRAPH_API = "https://graph.instagram.com/v22.0"
PUBLISH_RETRY_ATTEMPTS = 5
PUBLISH_RETRY_DELAY = 5


def post_carousel(
    access_token: str,
    user_id: str,
    image_urls: list[str],
    caption: str,
) -> str:
    """Instagram 캐러셀 포스팅.

    Args:
        access_token: Meta Graph API 토큰
        user_id: Instagram 비즈니스 계정 ID
        image_urls: 카드 이미지 URL 리스트 (GitHub Pages)
        caption: 캐러셀 캡션 텍스트

    Returns:
        게시된 미디어 ID

    Raises:
        RuntimeError: API 호출 실패 시
    """
    print(f"Instagram 캐러셀: {len(image_urls)}장")

    with httpx.Client(timeout=30.0) as client:
        # 1. 개별 이미지 컨테이너 생성
        children: list[str] = []
        for i, url in enumerate(image_urls, 1):
            resp = client.post(
                f"{GRAPH_API}/{user_id}/media",
                params={
                    "image_url": url,
                    "is_carousel_item": "true",
                    "access_token": access_token,
                },
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"이미지 {i} 실패: {resp.text[:300]}")
            children.append(resp.json()["id"])
            print(f"  이미지 {i}/{len(image_urls)}: {children[-1]}")

        # 2. 캐러셀 컨테이너 생성
        time.sleep(5)
        resp = client.post(
            f"{GRAPH_API}/{user_id}/media",
            params={
                "media_type": "CAROUSEL",
                "children": ",".join(children),
                "caption": caption,
                "access_token": access_token,
            },
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"캐러셀 생성 실패: {resp.text[:300]}")
        carousel_id = resp.json()["id"]

        # 3. 발행 (재시도 포함)
        time.sleep(5)
        for attempt in range(1, PUBLISH_RETRY_ATTEMPTS + 1):
            resp = client.post(
                f"{GRAPH_API}/{user_id}/media_publish",
                params={
                    "creation_id": carousel_id,
                    "access_token": access_token,
                },
            )
            if resp.status_code < 400:
                media_id = resp.json()["id"]
                print(f"Instagram 포스팅 완료: {media_id}")
                return media_id
            print(f"  발행 재시도 {attempt}/{PUBLISH_RETRY_ATTEMPTS}...")
            time.sleep(PUBLISH_RETRY_DELAY)

        raise RuntimeError(f"발행 실패: {resp.text[:300]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Instagram 캐러셀 포스팅")
    parser.add_argument("--date", required=True, help="카드뉴스 날짜 (YYYY-MM-DD)")
    parser.add_argument("--base-url", required=True, help="GitHub Pages 베이스 URL")
    args = parser.parse_args()

    access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    user_id = os.environ.get("INSTAGRAM_USER_ID", "")

    if not access_token or not user_id:
        print("INSTAGRAM 토큰 미설정, 포스팅 건너뜀")
        sys.exit(0)

    # 캡션 로드
    caption_path = f"output/{args.date}/caption.txt"
    try:
        with open(caption_path, encoding="utf-8") as f:
            caption = f.read().strip()
    except FileNotFoundError:
        caption = "AI Daily"

    # 카드 이미지 URL 생성
    card_files = sorted(glob.glob(f"output/{args.date}/card-*.png"))
    if not card_files:
        print(f"카드 파일 없음: output/{args.date}/card-*.png")
        sys.exit(1)

    image_urls = [
        f"{args.base_url}/cards/{args.date}/{os.path.basename(f)}"
        for f in card_files
    ]

    post_carousel(access_token, user_id, image_urls, caption)


if __name__ == "__main__":
    main()
