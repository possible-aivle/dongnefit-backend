# 표준 라이브러리 임포트
import argparse
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from config import get_credentials

# 로컬 모듈 임포트
from content_generator import ContentGenerator
from data_processor import DataProcessor
from tistory_writer import TistoryWriter
from user_input import get_user_input

# 로거 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_data_source(
    source: Union[str, Path, Dict, List], source_type: Optional[str] = None, **kwargs
) -> List[str]:
    """
    데이터 소스를 로드하고 처리하는 함수

    Args:
        source: 데이터 소스 (파일 경로, 문자열, 딕셔너리, 리스트 등)
        source_type: 데이터 소스 유형 ('text', 'json', 'csv', 'excel' 등)
        **kwargs: 데이터 처리에 필요한 추가 인자

    Returns:
        List[str]: 처리된 텍스트 데이터 리스트
    """
    processor = DataProcessor()
    return processor.process(source, source_type, **kwargs)


def get_user_choices(generator: ContentGenerator, data: List[str]) -> Dict[str, Any]:
    """
    사용자로부터 블로그 콘텐츠 생성을 위한 선택사항을 수집하는 함수

    Args:
        generator: ContentGenerator 인스턴스
        data: 처리된 텍스트 데이터 리스트

    Returns:
        Dict[str, Any]: 사용자 선택사항 (키워드, 제목, 카테고리, 해시태그)
    """
    print("\n=== 블로그 콘텐츠 생성 설정 ===")

    # 1. 키워드 선택
    print("\n[1/4] 키워드 선택")
    print("🔍 텍스트에서 키워드를 추출 중...")
    auto_keywords = generator.extract_keywords(data)
    auto_keyword = auto_keywords[0] if auto_keywords else "부동산 정책"
    print(f"✅ 추출된 키워드: {', '.join(auto_keywords) if auto_keywords else '없음'}")

    use_custom_keyword = get_user_input(
        "사용자 지정 키워드를 입력하시겠습니까? (y/n)", bool, default=False
    )

    if use_custom_keyword:
        keyword = get_user_input(
            "사용할 키워드를 입력하세요", str, default=auto_keyword
        )
    else:
        # 키워드 목록에서 선택
        if auto_keywords:
            print("\n추출된 키워드 목록:")
            for i, kw in enumerate(auto_keywords, 1):
                print(f"{i}. {kw}")
            print(f"{len(auto_keywords) + 1}. 직접 입력")

            choice = get_user_input(
                f"사용할 키워드 번호를 선택하세요 (1-{len(auto_keywords) + 1})",
                int,
                default=1,
                validation_func=lambda x: 1 <= x <= len(auto_keywords) + 1,
                error_message=f"1부터 {len(auto_keywords) + 1} 사이의 숫자를 입력해주세요.",
            )

            if choice <= len(auto_keywords):
                keyword = auto_keywords[choice - 1]
            else:
                keyword = get_user_input("사용할 키워드를 직접 입력하세요", str)
        else:
            keyword = get_user_input(
                "사용할 키워드를 입력하세요", str, default=auto_keyword
            )

    # 2. 제목 입력
    print("\n[2/4] 제목 설정")
    auto_title = generator.generate_title(keyword)
    print(f"✅ 자동 생성된 제목: {auto_title}")

    use_custom_title = get_user_input(
        "사용자 지정 제목을 입력하시겠습니까? (y/n)", bool, default=False
    )

    title = (
        get_user_input("블로그 제목을 입력하세요", str, default=auto_title)
        if use_custom_title
        else auto_title
    )

    # 3. 본문 생성 (이미지 포함)
    print("\n[3/4] 본문 생성")
    print("📄 본문 생성 중...")
    blog_result = generator.generate_blog(keyword, num_images=3)
    content = blog_result["content"]
    image_urls = blog_result.get("images", [])
    print(f"✅ 본문 생성 완료 (이미지 {len(image_urls)}개 포함)")

    # 4. 카테고리 선택
    print("\n[4/4] 카테고리 설정")
    auto_category = generator.classify_category(content)
    print(f"✅ 추천된 카테고리: {auto_category}")

    use_custom_category = get_user_input(
        "사용자 지정 카테고리를 입력하시겠습니까? (y/n)", bool, default=False
    )

    category = (
        get_user_input("카테고리를 입력하세요", str, default=auto_category)
        if use_custom_category
        else auto_category
    )

    # 5. 해시태그 설정
    print("\n[5/5] 해시태그 설정")
    auto_hashtags = generator.generate_hashtags(content)
    print(
        f"✅ 자동 생성된 해시태그: {', '.join(auto_hashtags) if auto_hashtags else '없음'}"
    )

    use_custom_hashtags = get_user_input(
        "사용자 지정 해시태그를 입력하시겠습니까? (y/n)", bool, default=False
    )

    if use_custom_hashtags:
        hashtags_input = get_user_input(
            "해시태그를 쉼표로 구분하여 입력하세요 (예: 부동산,집구하기,부동산시장)",
            str,
            default=", ".join(auto_hashtags) if auto_hashtags else "",
        )
        hashtags = [tag.strip() for tag in hashtags_input.split(",") if tag.strip()]
    else:
        hashtags = auto_hashtags

    return {
        "keyword": keyword,
        "title": title,
        "content": content,
        "images": image_urls,
        "category": category,
        "hashtags": hashtags,
    }


def generate_blog_content(
    generator: ContentGenerator,
    data: List[str],
    user_choices: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    블로그 콘텐츠를 생성하는 함수

    Args:
        generator: ContentGenerator 인스턴스
        data: 처리된 텍스트 데이터 리스트
        user_choices: 사용자 선택사항 (키워드, 제목, 카테고리, 해시태그 등)

    Returns:
        Dict[str, Any]: 생성된 블로그 콘텐츠 정보 (제목, 본문, 카테고리, 해시태그)
    """
    if user_choices is None:
        # 사용자 선택사항이 없으면 자동으로 생성
        print("🔍 키워드 추출 중...")
        keywords = generator.extract_keywords(data)
        keyword = keywords[0] if keywords else "부동산 정책"  # 기본 키워드 설정
        print(f"✅ 추출된 키워드: {keywords}")

        # 제목 생성
        print("📝 제목 생성 중...")
        blog_title = generator.generate_title(keyword)
        print(f"✅ 생성된 제목: {blog_title}")

        # 본문 생성 (이미지 포함)
        print("📄 본문 생성 중...")
        blog_result = generator.generate_blog(keyword, num_images=3)  # 이미지 3개 삽입
        blog_content = blog_result["content"]
        image_urls = blog_result.get("images", [])
        print(f"✅ 본문 생성 완료 (이미지 {len(image_urls)}개 포함)")

        # 카테고리 추천
        print("🏷️  카테고리 추천 중...")
        category = generator.classify_category(blog_content)
        print(f"✅ 추천된 카테고리: {category}")

        # 해시태그 추출
        print("🔖 해시태그 생성 중...")
        hashtags = generator.generate_hashtags(blog_content)
        print(f"✅ 생성된 해시태그: {hashtags}")

        return {
            "title": blog_title,
            "content": blog_content,
            "images": image_urls,
            "category": category,
            "hashtags": hashtags,
        }
    else:
        # 사용자 선택사항이 있으면 해당 값 사용
        return user_choices

    return {
        "title": blog_title,
        "content": blog_content,
        "images": image_urls,
        "category": category,
        "hashtags": hashtags,
    }


def post_to_tistory(credentials: Any, blog_data: Dict[str, Any]):
    """
    티스토리에 게시글을 작성하는 함수

    Args:
        credentials: 인증 정보가 포함된 객체
        blog_data: 작성할 블로그 데이터 (제목, 본문, 카테고리, 해시태그, 이미지 경로)
    """
    print("🚀 티스토리 게시글 작성을 시작합니다...")
    writer = TistoryWriter(credentials.tistory_id, credentials.tistory_password)

    try:
        # 로그인
        print("🔑 로그인 중...")
        writer.login()

        # 게시글 작성 (이미지 경로 포함)
        print("📝 게시글 작성 중...")
        writer.write_post(
            blog_data["title"],
            blog_data["content"],
            blog_data["category"],
            blog_data["hashtags"],
            image_paths=blog_data.get("images", []),  # 이미지 경로 전달
        )
        print("🎉 게시글이 성공적으로 작성되었습니다!")
    except Exception as e:
        print(f"❌ 오류가 발생했습니다: {str(e)}")
        raise
    finally:
        # 브라우저 종료
        writer.close()


def main():
    # 명령줄 인수 파싱
    parser = argparse.ArgumentParser(description="블로그 자동 포스팅 도구")
    parser.add_argument(
        "--source", type=str, help="데이터 소스 (파일 경로 또는 텍스트)"
    )
    parser.add_argument(
        "--source-type",
        type=str,
        choices=["text", "json", "csv", "excel"],
        help="데이터 소스 유형",
    )
    parser.add_argument(
        "--text-columns",
        type=str,
        nargs="+",
        help="CSV/Excel에서 텍스트로 사용할 컬럼 목록",
    )
    parser.add_argument(
        "--test-mode", action="store_true", help="테스트 모드 (실제로 포스팅하지 않음)"
    )
    args = parser.parse_args()

    # 크리덴셜 로드
    try:
        credentials = get_credentials()
    except Exception as e:
        print(f"❌ 설정 파일을 로드하는 중 오류가 발생했습니다: {e}")
        return

    # 데이터 소스 처리
    if args.source:
        # 명령줄 인수에서 소스 로드
        source = args.source
        source_type = args.source_type
        text_columns = args.text_columns
    else:
        # 기본 테스트 데이터 사용
        source = [
            "[서울=뉴시스]이연희 기자 = 한국토지주택공사(LH)가 7~9일 3일간 무주택 청년·신혼부부와 중산층·서민층 등을 위한 매입임대주택 청약 접수를 실시한다고 7일 밝혔다. "
            "매입임대 사업은 LH가 도심 내 교통 접근성이 좋아 직주근접이 가능한 신축 및 기존주택을 매입해 저렴하게 임대하는 제도다."
        ]
        source_type = None
        text_columns = None
        print("ℹ️  별도의 소스가 지정되지 않아 기본 테스트 데이터를 사용합니다.")

    try:
        # 데이터 로드 및 처리
        print("📂 데이터를 로드하는 중...")
        data = load_data_source(
            source=source, source_type=source_type, text_columns=text_columns
        )

        if not data:
            print("❌ 처리할 데이터가 없습니다.")
            return

        # ContentGenerator 초기화
        generator = ContentGenerator(credentials.openai_api_key)

        # 사용자 입력 받기
        print("\n=== 블로그 콘텐츠 생성을 시작합니다 ===")
        use_custom_input = get_user_input(
            "사용자 입력을 통해 콘텐츠를 생성하시겠습니까? (y/n)", bool, default=False
        )

        if use_custom_input:
            # 사용자 입력을 받아서 콘텐츠 생성
            user_choices = get_user_choices(generator, data)
            blog_data = generate_blog_content(generator, data, user_choices)
        else:
            # 자동으로 콘텐츠 생성
            print("\n자동으로 콘텐츠를 생성합니다...")
            blog_data = generate_blog_content(generator, data)

        # 테스트 모드가 아니면 티스토리에 포스팅
        if not args.test_mode:
            post_to_tistory(credentials, blog_data)
        else:
            print("\n=== 테스트 모드 결과 ===")
            print(f"제목: {blog_data['title']}")
            print(f"카테고리: {blog_data['category']}")
            print(f"해시태그: {', '.join(blog_data['hashtags'])}")
            print("\n본문 미리보기:")
            print(blog_data["content"][:300] + "...")
            print("\n✅ 테스트 모드 완료 (실제로 포스팅되지 않음)")

    except Exception as e:
        print(f"❌ 오류가 발생했습니다: {e}")


if __name__ == "__main__":
    main()
