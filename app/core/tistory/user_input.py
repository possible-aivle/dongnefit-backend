from typing import Callable, List, Optional, Type, TypeVar

T = TypeVar("T")


def get_user_input(
    prompt: str,
    input_type: Type[T],
    default: Optional[T] = None,
    validation_func: Optional[Callable[[T], bool]] = None,
    error_message: str = "잘못된 입력입니다. 다시 시도해주세요.",
) -> T:
    """
    사용자로부터 입력을 받아 지정된 타입으로 변환하여 반환합니다.

    Args:
        prompt: 사용자에게 보여줄 프롬프트 메시지
        input_type: 변환할 타입 (str, int, float, bool 등)
        default: 기본값 (None인 경우 필수 입력)
        validation_func: 입력 유효성 검사 함수 (선택사항)
        error_message: 유효성 검사 실패 시 보여줄 오류 메시지

    Returns:
        사용자 입력값 (지정된 타입으로 변환됨)
    """
    while True:
        try:
            # 기본값이 있는 경우와 없는 경우 프롬프트 다르게 표시
            if default is not None:
                user_input = input(f"{prompt} (기본값: {default}): ")
                if not user_input.strip():
                    return default
            else:
                user_input = input(f"{prompt}: ")
                if not user_input.strip():
                    print("필수 입력 항목입니다. 값을 입력해주세요.")
                    continue

            # 입력값 타입 변환
            if input_type is bool:
                # 불리언 타입 처리 (y/n)
                if user_input.lower() in ("y", "yes", "true", "1"):
                    return True
                elif user_input.lower() in ("n", "no", "false", "0"):
                    return False
                else:
                    raise ValueError()
            else:
                converted = input_type(user_input)

                # 유효성 검사 함수가 제공된 경우 검사
                if validation_func and not validation_func(converted):
                    print(error_message)
                    continue

                return converted

        except ValueError:
            print(f"잘못된 형식입니다. {input_type.__name__} 타입으로 입력해주세요.")


def get_list_input(
    prompt: str,
    item_type: Type[T],
    default: Optional[List[T]] = None,
    separator: str = ",",
    validation_func: Optional[Callable[[List[T]], bool]] = None,
    error_message: str = "잘못된 입력입니다. 다시 시도해주세요.",
) -> List[T]:
    """
    사용자로부터 리스트 형태의 입력을 받아 지정된 타입의 리스트로 변환하여 반환합니다.

    Args:
        prompt: 사용자에게 보여줄 프롬프트 메시지
        item_type: 리스트 항목의 타입 (str, int, float 등)
        default: 기본값 (None인 경우 필수 입력)
        separator: 항목 구분자 (기본값: 쉼표)
        validation_func: 입력 유효성 검사 함수 (선택사항)
        error_message: 유효성 검사 실패 시 보여줄 오류 메시지

    Returns:
        사용자 입력값 (지정된 타입의 리스트로 변환됨)
    """
    while True:
        try:
            # 기본값이 있는 경우와 없는 경우 프롬프트 다르게 표시
            if default is not None:
                default_str = separator.join(map(str, default))
                user_input = input(f"{prompt} (기본값: {default_str}): ")
                if not user_input.strip():
                    return default
            else:
                user_input = input(f"{prompt}: ")
                if not user_input.strip():
                    print("필수 입력 항목입니다. 값을 입력해주세요.")
                    continue

            # 입력값을 분할하고 각 항목을 지정된 타입으로 변환
            items = [
                item.strip() for item in user_input.split(separator) if item.strip()
            ]
            converted_items = [item_type(item) for item in items]

            # 유효성 검사 함수가 제공된 경우 검사
            if validation_func and not validation_func(converted_items):
                print(error_message)
                continue

            return converted_items

        except ValueError:
            print(
                f"잘못된 형식입니다. {item_type.__name__} 타입의 값을 {separator}로 구분하여 입력해주세요."
            )
