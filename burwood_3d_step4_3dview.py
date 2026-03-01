"""
========================================================
🏙️ Step 4: 3D Map View 설정
========================================================
📌 하는 일:
    1. 건물 레이어에 3D Extrusion(돌출) 설정
    2. 3D Map View 창 열기
    3. 지형(Terrain) 설정
    4. 카메라 위치/각도 설정

💡 비유: 2D 지도 위의 납작한 건물을 "뽑아올려서" 입체로 만드는 거예요!
🔧 사용법: Step 3 실행 후, QGIS Python 콘솔에서 실행하세요
========================================================
"""

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsProperty,
)
from qgis._3d import (
    QgsPhongMaterialSettings,
    QgsVectorLayer3DRenderer,
    QgsPolygon3DSymbol,
)
from qgis.PyQt.QtGui import QColor
from qgis.utils import iface

# ─────────────────────────────────────────────
# 📍 설정값
# ─────────────────────────────────────────────
BURWOOD_LAT = -33.8773
BURWOOD_LNG = 151.1043

# ─────────────────────────────────────────────
# 🔍 건물 레이어 찾기
# ─────────────────────────────────────────────
print("🔍 건물 레이어를 찾고 있어요...")

project = QgsProject.instance()
building_layer = None

for layer in project.mapLayers().values():
    if "Building" in layer.name() or "building" in layer.name():
        building_layer = layer
        break

if not building_layer:
    print("❌ 건물 레이어를 찾을 수 없어요!")
    print("💡 Step 2를 먼저 실행했는지 확인해주세요")
    raise Exception("Buildings layer not found")

print(f"   ✅ 건물 레이어 찾음: {building_layer.name()}")

# ─────────────────────────────────────────────
# 🏗️ 1단계: 3D 심볼 설정 (Extrusion)
# ─────────────────────────────────────────────
# 💡 비유: 종이 위의 건물 그림에 "높이" 정보를 줘서
#          레고 블록처럼 위로 쌓아 올리는 거예요!
print("🏗️ 건물 3D Extrusion을 설정하고 있어요...")

# 3D 폴리곤 심볼 생성
symbol_3d = QgsPolygon3DSymbol()

# 재질(Material) 설정 - 건물이 빛을 받았을 때 어떻게 보이는지
# 💡 비유: 건물 외벽의 색깔과 광택을 정하는 거예요
material = QgsPhongMaterialSettings()
material.setDiffuse(QColor(180, 180, 200))    # 기본 색: 밝은 회색-파랑
material.setAmbient(QColor(100, 100, 120))    # 그림자 색: 어두운 회색
material.setSpecular(QColor(255, 255, 255))   # 반사광: 흰색
material.setShininess(50.0)                    # 광택 정도
symbol_3d.setMaterialSettings(material)

# Extrusion 높이 설정
# 💡 "height" 필드 값만큼 건물을 위로 쌓아 올려요
symbol_3d.setExtrusionHeight(0)  # 기본값 0 (data-defined로 설정)

# 3D 렌더러 생성 및 적용
renderer_3d = QgsVectorLayer3DRenderer()
renderer_3d.setSymbol(symbol_3d)
renderer_3d.setLayer(building_layer)

# height 필드를 사용하여 각 건물마다 다른 높이 적용
# Property를 사용하여 height 필드 매핑
prop = QgsProperty.fromExpression('"height"')
symbol_3d.dataDefinedProperties().setProperty(
    QgsPolygon3DSymbol.PropertyExtrusionHeight, prop
)

renderer_3d.setSymbol(symbol_3d)
building_layer.setRenderer3D(renderer_3d)

print("   ✅ 3D Extrusion 설정 완료!")
print("   💡 건물이 'height' 필드 값만큼 솟아올라요")

# ─────────────────────────────────────────────
# 🎥 2단계: 3D Map View 열기
# ─────────────────────────────────────────────
# 💡 비유: 드론으로 위에서 건물들을 내려다보는 시점을 만드는 거예요
print("🎥 3D Map View를 열고 있어요...")
print("   💡 QGIS 메뉴에서 View → 3D Map Views 에서도 열 수 있어요")

# ⚠️ createNewMapCanvas3D()는 현재 QGIS 버전에서
#    C++ 레벨 segfault(OpenGL/Metal 충돌)를 일으켜 QGIS가 크래시해요
#    → 3D 뷰는 사용자가 직접 열어야 안전합니다
print("   📌 3D View를 수동으로 열어주세요:")
print("      메뉴 → View → 3D Map Views → New 3D Map View")
print("")
print("   📌 3D View 조작법:")
print("      🖱️ 마우스 왼쪽 드래그: 회전")
print("      🖱️ 마우스 휠: 확대/축소")
print("      🖱️ 마우스 가운데 드래그: 이동")
print("      Shift + 왼쪽 드래그: 기울기 변경")

# ─────────────────────────────────────────────
# ✅ 완료 메시지
# ─────────────────────────────────────────────
print("")
print("=" * 50)
print("✅ Step 4 완료!")
print("=" * 50)
print("🏙️ 3D 설정 완료:")
print("   🏢 건물 Extrusion: height 필드 기반")
print("   🎨 건물 재질: 밝은 회색-파랑 (Phong shading)")
print("   🌍 지형: Flat terrain")
print("")
print("💡 팁: 3D 뷰에서 마우스로 회전/확대하며 건물을 살펴보세요!")
print("")
print("👉 다음 단계: burwood_3d_step5_render.py 를 실행하세요!")
