# PostGIS Geometry 처리 가이드

DongneFit에서 공간 데이터(geometry)를 저장하고 읽어오는 전체 흐름을 설명합니다.

## 개요

```
[SHP/GeoJSON] → geojson_to_wkt() → WKT 문자열 → ST_GeomFromText() → PostGIS Geometry
PostGIS Geometry → WKBElement → wkb_to_geojson() → GeoJSON dict (API 응답)
PostGIS Geometry → WKBElement → wkb_to_shapely() → Shapely 객체 (서비스 로직)
```

## 핵심 개념

### WKBElement

GeoAlchemy2가 DB에서 geometry를 읽을 때 반환하는 타입입니다.

```python
from app.models.spatial import RoadCenterLine

road = session.get(RoadCenterLine, 1)
print(type(road.geometry))
# <class 'geoalchemy2.elements.WKBElement'>
```

- WKB(Well-Known Binary) 형식의 바이너리 데이터를 감싸는 래퍼
- `bytes`의 서브클래스가 **아님** (`isinstance(wkb, bytes)` → `False`)
- Pydantic 호환 타입이 아니므로 SQLModel 필드에 직접 타입 어노테이션 불가
- 따라서 모델에서 `geometry: Any`로 선언

### WKT (Well-Known Text)

사람이 읽을 수 있는 geometry 텍스트 형식입니다.

```
POLYGON ((127.0 37.5, 127.1 37.5, 127.1 37.6, 127.0 37.6, 127.0 37.5))
LINESTRING (127.0 37.5, 127.1 37.6)
POINT (127.0 37.5)
```

파이프라인에서 SHP 파일의 GeoJSON geometry를 WKT로 변환한 뒤 DB에 삽입합니다.

### GeoJSON

API 응답에서 사용하는 geometry JSON 형식입니다.

```json
{
  "type": "Polygon",
  "coordinates": [[[127.0, 37.5], [127.1, 37.5], [127.1, 37.6], [127.0, 37.6], [127.0, 37.5]]]
}
```

---

## 모델 설정

### geometry_column() 헬퍼

모든 geometry 컬럼은 `app.models.base.geometry_column()`으로 생성합니다.

```python
# app/models/base.py
def geometry_column(
    geometry_type: str = "GEOMETRY",  # GEOMETRY, POINT, LINESTRING, POLYGON 등
    srid: int = 4326,                 # 좌표계 (WGS84)
    description: str = "PostGIS Geometry",
) -> Any: ...
```

모델에서의 사용:

```python
from app.models.base import PublicDataBase, geometry_column

class AdministrativeDivision(PublicDataBase, table=True):
    __tablename__ = "administrative_divisions"

    code: str = Field(...)
    name: str = Field(...)
    geometry: Any = geometry_column(description="행정구역 경계 (Polygon/MultiPolygon)")
```

### 왜 `geometry: Any`인가?

| 후보 | 문제점 |
|------|--------|
| `geometry: WKBElement` | Pydantic이 WKBElement를 모름 → 유효성 검증 실패 |
| `geometry: bytes` | WKBElement는 bytes 서브클래스가 아님 → 타입이 부정확 |
| `geometry: dict` | DB에서 읽으면 dict가 아닌 WKBElement가 옴 |
| **`geometry: Any`** | 유일하게 모든 상황에서 동작 |

geometry 필드는 상황에 따라 다른 타입을 가집니다:

| 상황 | 타입 |
|------|------|
| DB에서 읽을 때 | `WKBElement` |
| 파이프라인에서 쓸 때 | `str` (WKT) |
| 값이 없을 때 | `None` |

### 적용된 모델 목록

| 모델 | 테이블 | geometry 타입 |
|------|--------|--------------|
| `AdministrativeDivision` | administrative_divisions | Polygon/MultiPolygon |
| `AdministrativeEmd` | administrative_emds | Polygon/MultiPolygon |
| `Lot` | lots | Polygon/MultiPolygon |
| `RoadCenterLine` | road_center_lines | LineString/MultiLineString |
| `UseRegionDistrict` | use_region_districts | Polygon/MultiPolygon |
| `GisBuildingIntegrated` | gis_building_integrated | Polygon/MultiPolygon |

---

## 쓰기 (Write) 흐름

### 1단계: SHP → GeoJSON → WKT

프로세서에서 SHP 파일을 읽으면 fiona가 GeoJSON dict를 반환합니다. 이를 WKT 문자열로 변환합니다.

```python
# pipeline/file_utils.py
from shapely.geometry import shape as shapely_shape

def geojson_to_wkt(geojson: dict | None) -> str | None:
    if geojson is None:
        return None
    return shapely_shape(geojson).wkt
```

프로세서의 `transform()`에서 사용:

```python
# pipeline/processors/cadastral.py
def transform(self, raw_data):
    for row in raw_data:
        records.append({
            "pnu": pnu,
            "geometry": geojson_to_wkt(row.pop("__geometry__", None)),
            # → "POLYGON ((127.0 37.5, ...))"
        })
```

### 2단계: WKT → PostGIS Geometry (SQL)

loader에서 geometry 컬럼을 `ST_GeomFromText()`로 감싸서 INSERT합니다.

```python
# pipeline/loader.py
def _build_val_expr(col: str) -> str:
    if col == "geometry":
        return f"ST_GeomFromText(:{col}, 4326)"
    return f":{col}"

# 생성되는 SQL:
# INSERT INTO lots (pnu, geometry, ...)
# VALUES (:pnu, ST_GeomFromText(:geometry, 4326), ...)
```

---

## 읽기 (Read) 흐름

### API 응답: WKBElement → GeoJSON dict

Pydantic 스키마에서 `GeoJSON` 타입을 사용하면 자동 변환됩니다.

```python
# app/schemas/base.py
from pydantic import BeforeValidator
from typing import Annotated

def wkb_to_geojson(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    from geoalchemy2.elements import WKBElement
    from geoalchemy2.shape import to_shape
    from shapely.geometry import mapping
    if isinstance(value, WKBElement):
        return mapping(to_shape(value))
    return None

# 자동 변환 타입 (BeforeValidator로 WKBElement → GeoJSON 자동 처리)
GeoJSON = Annotated[dict[str, Any] | None, BeforeValidator(wkb_to_geojson)]
```

스키마에서의 사용:

```python
# app/schemas/administrative.py
from app.schemas.base import BaseSchema, GeoJSON

class AdministrativeDivisionRead(BaseSchema):
    id: int
    code: str
    name: str
    geometry: GeoJSON = None  # WKBElement → GeoJSON dict 자동 변환
```

변환 과정:

```
DB 조회 → row.geometry (WKBElement)
        → BeforeValidator(wkb_to_geojson) 호출
        → to_shape(wkb_element) → Shapely 객체
        → mapping(shape) → GeoJSON dict
        → API 응답: {"type": "Polygon", "coordinates": [...]}
```

### 서비스 로직: WKBElement → Shapely 객체

공간 연산이 필요한 서비스 코드에서는 `wkb_to_shapely()`를 사용합니다.

```python
from app.schemas.base import wkb_to_shapely

# DB에서 읽은 행정구역
division = session.get(AdministrativeDivision, 1)

# Shapely 객체로 변환
shape = wkb_to_shapely(division.geometry)

# 공간 연산
area = shape.area
centroid = shape.centroid
contains = shape.contains(other_shape)
intersects = shape.intersects(other_shape)
```

---

## 변환 함수 요약

| 함수 | 위치 | 입력 | 출력 | 용도 |
|------|------|------|------|------|
| `geojson_to_wkt()` | `pipeline/file_utils.py` | GeoJSON dict | WKT str | 파이프라인 적재 |
| `wkb_to_geojson()` | `app/schemas/base.py` | WKBElement | GeoJSON dict | API 응답 |
| `wkb_to_shapely()` | `app/schemas/base.py` | WKBElement | Shapely 객체 | 서비스 로직 |
| `GeoJSON` (타입) | `app/schemas/base.py` | - | - | 스키마 필드 타입 |
| `geometry_column()` | `app/models/base.py` | - | Field | 모델 컬럼 정의 |

---

## Alembic 마이그레이션

GeoAlchemy2 컬럼의 마이그레이션을 위해 `alembic_helpers`를 설정합니다.

```python
# alembic/env.py
from geoalchemy2 import alembic_helpers

# offline, online 양쪽 모두 설정
context.configure(
    ...,
    process_revision_directives=alembic_helpers.writer,
    render_item=alembic_helpers.render_item,
)
```

이 설정이 없으면 `alembic revision --autogenerate` 시 geometry 컬럼이 누락되거나 잘못 생성됩니다.

---

## PostGIS SQL 참고

```sql
-- geometry를 GeoJSON으로 변환
SELECT ST_AsGeoJSON(geometry) FROM lots WHERE pnu = '1111010100100010000';

-- geometry를 WKT로 변환
SELECT ST_AsText(geometry) FROM lots WHERE pnu = '1111010100100010000';

-- 특정 좌표가 포함된 필지 검색
SELECT * FROM lots
WHERE ST_Contains(geometry, ST_SetSRID(ST_MakePoint(127.0, 37.5), 4326));

-- 두 geometry 간 거리 (미터)
SELECT ST_Distance(
    a.geometry::geography,
    b.geometry::geography
) FROM lots a, lots b
WHERE a.pnu = '...' AND b.pnu = '...';
```
