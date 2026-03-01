"""
========================================================
🏗️ Step 1: Burwood Station 프로젝트 초기 설정
========================================================
📌 하는 일:
    1. 새 QGIS 프로젝트를 만들어요
    2. OpenStreetMap 배경지도를 추가해요
    3. Burwood Station 위치에 핀(Pin)을 찍어요
    4. 핀 주변 500m 원형 버퍼를 그려요
    5. 맵을 버퍼 영역으로 확대해요

🔧 사용법: QGIS Python 콘솔에서 실행하세요
========================================================
"""

from qgis.core import (
    QgsProject,
    QgsCoordinateReferenceSystem,
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsField,
    QgsCoordinateTransform,
    QgsRasterLayer,
    QgsSymbol,
    QgsSingleSymbolRenderer,
    QgsFillSymbol,
    QgsMarkerSymbol,
)
from qgis.PyQt.QtCore import QVariant
from qgis.utils import iface

# ─────────────────────────────────────────────
# 📍 기본 설정값
# ─────────────────────────────────────────────
# 💡 비유: 지도에서 "여기!" 라고 손가락으로 가리키는 좌표예요
BURWOOD_LAT = -33.8773   # 위도 (남반구라서 마이너스)
BURWOOD_LNG = 151.1043   # 경도
BUFFER_RADIUS_M = 500    # 반경 500미터

# 좌표계 정의
# 💡 비유: 지도의 "언어"를 정하는 거예요
#    EPSG:4326 = 위도/경도 (전 세계 공통)
#    EPSG:32756 = 미터 단위 (호주 시드니 근처에 정확한 좌표계)
CRS_WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")
CRS_UTM56S = QgsCoordinateReferenceSystem("EPSG:32756")

# ─────────────────────────────────────────────
# 🎯 1단계: 새 프로젝트 생성
# ─────────────────────────────────────────────
print("🎯 새 QGIS 프로젝트를 만들고 있어요...")

project = QgsProject.instance()
project.clear()  # 기존 프로젝트 내용 지우기
project.setCrs(CRS_WGS84)  # 좌표계를 WGS84로 설정
project.setTitle("Burwood Station 3D Buildings")

# ─────────────────────────────────────────────
# 🗺️ 2단계: OpenStreetMap 베이스맵 추가
# ─────────────────────────────────────────────
# 💡 비유: 하얀 도화지 위에 배경 지도를 깔아주는 거예요
print("🗺️ OpenStreetMap 배경지도를 추가하고 있어요...")

osm_url = "type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png&zmax=19&zmin=0"
osm_layer = QgsRasterLayer(osm_url, "OpenStreetMap", "wms")

if osm_layer.isValid():
    project.addMapLayer(osm_layer)
    print("   ✅ OpenStreetMap 베이스맵 추가 완료!")
else:
    print("   ⚠️ OpenStreetMap 로드 실패 - 인터넷 연결을 확인해주세요")

# ─────────────────────────────────────────────
# 📍 3단계: Burwood Station 핀(Pin) 레이어 생성
# ─────────────────────────────────────────────
# 💡 비유: 지도에 빨간 압정을 꽂는 거예요
print("📍 Burwood Station 위치에 핀을 찍고 있어요...")

# 메모리 레이어 생성 (포인트 타입, WGS84 좌표계)
pin_layer = QgsVectorLayer("Point?crs=EPSG:4326", "Burwood Station Pin", "memory")
pin_provider = pin_layer.dataProvider()

# 속성(이름) 필드 추가
pin_provider.addAttributes([
    QgsField("name", QVariant.String),
    QgsField("description", QVariant.String),
])
pin_layer.updateFields()

# 포인트 피처 생성
pin_feature = QgsFeature()
pin_feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(BURWOOD_LNG, BURWOOD_LAT)))
pin_feature.setAttributes(["Burwood Station", "Sydney, NSW, Australia"])
pin_provider.addFeatures([pin_feature])

# 핀 스타일: 빨간색 별 모양
# 💡 비유: 압정의 색깔과 모양을 정하는 거예요
pin_symbol = QgsMarkerSymbol.createSimple({
    'name': 'star',          # 별 모양
    'color': '#FF0000',      # 빨간색
    'outline_color': '#8B0000',  # 테두리: 진한 빨강
    'size': '8',             # 크기
    'outline_width': '0.6',
})
pin_layer.setRenderer(QgsSingleSymbolRenderer(pin_symbol))

project.addMapLayer(pin_layer)
print("   ✅ Burwood Station 핀 추가 완료!")

# ─────────────────────────────────────────────
# ⭕ 4단계: 500m 원형 버퍼 레이어 생성
# ─────────────────────────────────────────────
# 💡 비유: 핀 주위에 컴퍼스로 원을 그리는 거예요
print("⭕ 500m 반경 버퍼를 그리고 있어요...")

# 좌표 변환기 생성 (WGS84 → UTM으로 변환해야 미터 단위 계산 가능)
transform_to_utm = QgsCoordinateTransform(CRS_WGS84, CRS_UTM56S, project)
transform_to_wgs = QgsCoordinateTransform(CRS_UTM56S, CRS_WGS84, project)

# 포인트를 UTM 좌표로 변환
point_wgs = QgsPointXY(BURWOOD_LNG, BURWOOD_LAT)
point_utm = transform_to_utm.transform(point_wgs)

# UTM 좌표에서 500m 버퍼 생성 후 다시 WGS84로 변환
buffer_geom_utm = QgsGeometry.fromPointXY(point_utm).buffer(BUFFER_RADIUS_M, 64)
buffer_geom_wgs = QgsGeometry(buffer_geom_utm)
buffer_geom_wgs.transform(transform_to_wgs)

# 버퍼 레이어 생성
buffer_layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "500m Buffer", "memory")
buffer_provider = buffer_layer.dataProvider()
buffer_provider.addAttributes([
    QgsField("radius_m", QVariant.Int),
])
buffer_layer.updateFields()

buffer_feature = QgsFeature()
buffer_feature.setGeometry(buffer_geom_wgs)
buffer_feature.setAttributes([BUFFER_RADIUS_M])
buffer_provider.addFeatures([buffer_feature])

# 버퍼 스타일: 반투명 파란색 테두리 (채우기 없음)
# 💡 비유: 원의 선만 파란색으로 그리고 안쪽은 투명하게!
buffer_symbol = QgsFillSymbol.createSimple({
    'color': '50,120,200,30',       # 매우 연한 파란색 (거의 투명)
    'outline_color': '#1E90FF',     # 테두리: 밝은 파란색
    'outline_width': '1.2',        # 테두리 두께
    'outline_style': 'dash',       # 점선 스타일
})
buffer_layer.setRenderer(QgsSingleSymbolRenderer(buffer_symbol))

project.addMapLayer(buffer_layer)
print("   ✅ 500m 버퍼 추가 완료!")

# ─────────────────────────────────────────────
# 🔍 5단계: 맵 캔버스를 버퍼 영역으로 줌
# ─────────────────────────────────────────────
print("🔍 맵을 버퍼 영역으로 확대하고 있어요...")

# 버퍼 범위에 약간의 여백을 추가해서 줌
canvas = iface.mapCanvas()
extent = buffer_layer.extent()
extent.scale(1.3)  # 30% 여유 공간 추가
canvas.setExtent(extent)
canvas.refresh()

print("   ✅ 맵 줌 완료!")

# ─────────────────────────────────────────────
# ✅ 완료 메시지
# ─────────────────────────────────────────────
print("")
print("=" * 50)
print("✅ Step 1 완료!")
print("=" * 50)
print(f"📍 위치: Burwood Station ({BURWOOD_LAT}, {BURWOOD_LNG})")
print(f"⭕ 버퍼: {BUFFER_RADIUS_M}m 반경")
print("🗺️ 레이어: OpenStreetMap, Pin, Buffer")
print("")
print("👉 다음 단계: burwood_3d_step2_buildings.py 를 실행하세요!")
