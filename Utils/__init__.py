import random


def generate_random_boolean() -> bool:
    """
    True or False를 랜덤으로 반환
    """
    return random.choice([True, False])


def get_random_4_number() -> int:
    """
    랜덤한 4자리 숫자 생성
    """
    return random.randint(1000, 9999)


def get_random_jeju_coordinates() -> tuple[float, float]:
    """
    제주도 내의 랜덤한 좌표쌍 생성
    """
    return random.uniform(33.1, 33.6), random.uniform(126.1, 126.9)


def get_random_korean_string(n: int = 1) -> str:
    """
    매개변수 n을 받아 랜덤한 n자리 한글 생성
    """
    hangul_start = 0xAC00
    hangul_end = 0xD7A3
    result = "".join(chr(random.randint(hangul_start, hangul_end)) for _ in range(n))
    return result


def get_random_alpha_string() -> str:
    """
    매개변수 n을 받아 랜덤한 n자리 알파벳(A-Z) 문자열 생성
    """
    alpha_start = 65
    alpha_end = 90
    return chr(random.randint(alpha_start, alpha_end))


def get_random_seconds(n: int = 1) -> int:
    """
    매개변수 n을 받아 랜덤한 n자리의 10의 배수 생성
    """
    if n <= 0:
        raise ValueError("Invalid Digits")
    min = 10 ** (n - 1)
    max = (10**n) - 1
    return random.randint(min, max)
