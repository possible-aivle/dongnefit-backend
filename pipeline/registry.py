"""프로세서 레지스트리.

모든 프로세서를 등록하고 조회하는 중앙 관리소입니다.
새 데이터 소스 추가 시 여기에 등록하면 CLI 메뉴에 자동 노출됩니다.
"""

from pipeline.processors.base import BaseProcessor


class Registry:
    """프로세서 레지스트리."""

    _processors: dict[str, BaseProcessor] = {}

    @classmethod
    def register(cls, processor: BaseProcessor) -> None:
        cls._processors[processor.name] = processor

    @classmethod
    def get(cls, name: str) -> BaseProcessor:
        if name not in cls._processors:
            raise KeyError(f"등록되지 않은 프로세서: {name}")
        return cls._processors[name]

    @classmethod
    def list_all(cls) -> list[tuple[str, str]]:
        """등록된 모든 프로세서의 (name, description) 리스트."""
        return [(p.name, p.description) for p in cls._processors.values()]

    @classmethod
    def names(cls) -> list[str]:
        return list(cls._processors.keys())

    @classmethod
    def count(cls) -> int:
        return len(cls._processors)


def auto_discover() -> None:
    """processors/ 디렉토리의 모든 프로세서를 자동 등록합니다.

    각 프로세서 모듈에서 register() 호출이 필요합니다.
    새 프로세서 추가 시:
        1. pipeline/processors/my_source.py 생성
        2. BaseProcessor 상속 클래스 구현
        3. 모듈 하단에 Registry.register(MySourceProcessor()) 추가
    """
    import importlib
    import pkgutil

    import pipeline.processors as pkg

    for _importer, modname, _ispkg in pkgutil.iter_modules(pkg.__path__):
        if modname == "base":
            continue
        importlib.import_module(f"pipeline.processors.{modname}")
