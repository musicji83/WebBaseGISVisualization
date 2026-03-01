"""
========================================================
🎨 Step 3: 레이어 스타일링
========================================================
📌 하는 일:
    1. 건물 레이어에 높이별 그라데이션 색상 적용
       (낮은 건물 → 파란색, 높은 건물 → 빨간색)
    2. Pin 마커 스타일 확인/재설정
    3. 버퍼 스타일 확인/재설정
    4. 레이어 순서 정리

🔧 사용법: Step 2 실행 후, QGIS Python 콘솔에서 실행하세요
========================================================
"""

from qgis.core import (
    QgsProject,
    QgsGraduatedSymbolRenderer,
    QgsRendererRange,
    QgsSymbol,
    QgsFillSymbol,
    QgsMarkerSymbol,
    QgsSingleSymbolRenderer,
    QgsClassificationRange,
    QgsStyle,
)
from qgis.utils import iface

# ─────────────────────────────────────────────
# 🔍 레이어 찾기
# ─────────────────────────────────────────────
print("🔍 레이어를 찾고 있어요...")

project = QgsProject.instance()

# 레이어 이름으로 찾기
# 💡 비유: 포토샵에서 레이어 패널에서 레이어를 찾는 것과 같아요
building_layer = None
pin_layer = None
buffer_layer = None

for layer in project.mapLayers().values():
    name = layer.name()
    if "Building" in name or "building" in name:
        building_layer = layer
    elif "Pin" in name or "pin" in name or "Station" in name:
        pin_layer = layer
    elif "Buffer" in name or "buffer" in name:
        buffer_layer = layer

if not building_layer:
    print("❌ 건물 레이어를 찾을 수 없어요!")
    print("💡 Step 2를 먼저 실행했는지 확인해주세요")
    raise Exception("Buildings layer not found")

print(f"   ✅ 건물 레이어: {building_layer.name()} ({building_layer.featureCount()}개)")
if pin_layer:
    print(f"   ✅ 핀 레이어: {pin_layer.name()}")
if buffer_layer:
    print(f"   ✅ 버퍼 레이어: {buffer_layer.name()}")

# ─────────────────────────────────────────────
# 🏢 1단계: 건물 높이별 그라데이션 색상 적용
# ─────────────────────────────────────────────
# 💡 비유: 온도 지도처럼 낮은 건물은 차가운 색(파랑),
#          높은 건물은 뜨거운 색(빨강)으로 칠하는 거예요
print("🏢 건물에 높이별 그라데이션 색상을 적용하고 있어요...")

# 높이 범위별 색상 정의
# (최소높이, 최대높이, 채우기색, 테두리색, 라벨)
height_classes = [
    (0,   6,   "#3288BD", "#2166AC", "0-6m (1-2층)"),
    (6,   12,  "#66C2A5", "#1B9E77", "6-12m (2-4층)"),
    (12,  20,  "#ABDDA4", "#66BD63", "12-20m (4-7층)"),
    (20,  35,  "#FEE08B", "#D9A825", "20-35m (7-12층)"),
    (35,  60,  "#FDAE61", "#E66101", "35-60m (12-20층)"),
    (60,  200, "#D53E4F", "#B2182B", "60m+ (20층 이상)"),
]

ranges = []
for low, high, fill_color, outline_color, label in height_classes:
    # 각 범위에 대한 심볼(색상) 만들기
    symbol = QgsFillSymbol.createSimple({
        'color': fill_color,
        'outline_color': outline_color,
        'outline_width': '0.3',
    })
    # 투명도 설정 (약간 반투명하게)
    symbol.setOpacity(0.85)
    rng = QgsRendererRange(low, high, symbol, label)
    ranges.append(rng)

# "height" 필드 기준으로 분류 렌더러 생성
renderer = QgsGraduatedSymbolRenderer("height", ranges)
renderer.setMode(QgsGraduatedSymbolRenderer.Custom)
building_layer.setRenderer(renderer)
building_layer.triggerRepaint()

print("   ✅ 건물 그라데이션 색상 적용 완료!")

# ─────────────────────────────────────────────
# 📍 2단계: Pin 마커 스타일 재확인
# ─────────────────────────────────────────────
if pin_layer:
    print("📍 핀 마커 스타일을 확인하고 있어요...")
    pin_symbol = QgsMarkerSymbol.createSimple({
        'name': 'star',
        'color': '#FF0000',
        'outline_color': '#8B0000',
        'size': '8',
        'outline_width': '0.6',
    })
    pin_layer.setRenderer(QgsSingleSymbolRenderer(pin_symbol))
    pin_layer.triggerRepaint()
    print("   ✅ 핀 스타일 확인 완료!")

# ─────────────────────────────────────────────
# ⭕ 3단계: 버퍼 스타일 재확인
# ─────────────────────────────────────────────
if buffer_layer:
    print("⭕ 버퍼 스타일을 확인하고 있어요...")
    buffer_symbol = QgsFillSymbol.createSimple({
        'color': '50,120,200,30',
        'outline_color': '#1E90FF',
        'outline_width': '1.2',
        'outline_style': 'dash',
    })
    buffer_layer.setRenderer(QgsSingleSymbolRenderer(buffer_symbol))
    buffer_layer.triggerRepaint()
    print("   ✅ 버퍼 스타일 확인 완료!")

# ─────────────────────────────────────────────
# 📋 4단계: 레이어 순서 정리
# ─────────────────────────────────────────────
# 💡 비유: 포토샵에서 레이어를 위아래로 정렬하는 거예요
#          맨 아래 = 배경지도, 중간 = 건물, 위 = 버퍼와 핀
print("📋 레이어 순서를 정리하고 있어요...")

root = project.layerTreeRoot()

# 레이어 순서: (위에서 아래로)
#   1. Pin (맨 위 - 가장 잘 보여야 함)
#   2. Buffer (원형 테두리)
#   3. Buildings (건물)
#   4. OpenStreetMap (배경)
desired_order = ["Pin", "Buffer", "Building", "OpenStreetMap"]

for i, keyword in enumerate(desired_order):
    for child in root.children():
        if keyword.lower() in child.name().lower():
            clone = child.clone()
            root.insertChildNode(i, clone)
            root.removeChildNode(child)
            break

print("   ✅ 레이어 순서 정리 완료!")

# 맵 새로고침
iface.mapCanvas().refresh()

# ─────────────────────────────────────────────
# ✅ 완료 메시지
# ─────────────────────────────────────────────
print("")
print("=" * 50)
print("✅ Step 3 완료!")
print("=" * 50)
print("🎨 스타일 적용:")
print("   🏢 건물: 높이별 파랑→빨강 그라데이션")
print("   📍 핀: 빨간색 별")
print("   ⭕ 버퍼: 파란 점선 테두리")
print("")
print("👉 다음 단계: burwood_3d_step4_3dview.py 를 실행하세요!")
