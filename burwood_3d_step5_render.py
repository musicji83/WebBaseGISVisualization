"""
========================================================
📸 Step 5: 렌더링 및 프로젝트 저장
========================================================
📌 하는 일:
    1. 2D 맵을 PNG 이미지로 렌더링
    2. QGIS 프로젝트를 .qgz 파일로 저장

💡 비유: 완성된 작품을 사진 찍고(PNG), 원본 파일을 저장(QGZ)하는 거예요!
🔧 사용법: Step 4 실행 후, QGIS Python 콘솔에서 실행하세요
========================================================
"""

import os

from qgis.core import QgsProject
from qgis.utils import iface

# ─────────────────────────────────────────────
# 📍 저장 경로 설정
# ─────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.path.expanduser("~/Desktop/QGIS_MCP")
PNG_PATH = os.path.join(SCRIPT_DIR, "burwood_2d_map.png")
QGZ_PATH = os.path.join(SCRIPT_DIR, "burwood_3d.qgz")

# ─────────────────────────────────────────────
# 📸 1단계: 2D 맵 PNG 렌더링
# ─────────────────────────────────────────────
# 💡 비유: 지금 보이는 지도 화면을 스크린샷 찍는 거예요
# ⚠️ 3D 렌더러가 설정된 상태에서 saveAsImage()를 호출하면
#    내부적으로 3D 관련 코드가 실행되며 QGIS 크래시가 발생할 수 있음
#    → 렌더링 전 3D 렌더러를 임시 제거 후 복원하는 방식으로 안전하게 처리
print("📸 2D 맵을 PNG 이미지로 렌더링하고 있어요...")

# 3D 렌더러가 있는 레이어를 찾아서 임시 제거
saved_3d_renderers = {}
for layer_id, layer in QgsProject.instance().mapLayers().items():
    r3d = layer.renderer3D()
    if r3d:
        saved_3d_renderers[layer_id] = r3d.clone()
        layer.setRenderer3D(None)

canvas = iface.mapCanvas()
canvas.saveAsImage(PNG_PATH)

# 3D 렌더러 복원
for layer_id, r3d in saved_3d_renderers.items():
    layer = QgsProject.instance().mapLayer(layer_id)
    if layer:
        layer.setRenderer3D(r3d)

if os.path.exists(PNG_PATH):
    file_size_kb = os.path.getsize(PNG_PATH) / 1024
    print(f"   ✅ PNG 저장 완료!")
    print(f"   📁 경로: {PNG_PATH}")
    print(f"   📦 크기: {file_size_kb:.0f} KB")
    if saved_3d_renderers:
        print(f"   💡 3D 렌더러 {len(saved_3d_renderers)}개 임시 제거 후 복원 완료")
else:
    print("   ❌ PNG 저장 실패")

# ─────────────────────────────────────────────
# 💾 2단계: QGIS 프로젝트 저장 (.qgz)
# ─────────────────────────────────────────────
# 💡 비유: 모든 레이어와 스타일 설정을 하나의 파일에 담아 저장해요
#          나중에 이 파일을 열면 지금 상태 그대로 볼 수 있어요!
print("💾 QGIS 프로젝트를 저장하고 있어요...")

project = QgsProject.instance()
if project.write(QGZ_PATH):
    file_size_mb = os.path.getsize(QGZ_PATH) / (1024 * 1024)
    print(f"   ✅ 프로젝트 저장 완료!")
    print(f"   📁 경로: {QGZ_PATH}")
    print(f"   📦 크기: {file_size_mb:.1f} MB")
else:
    print("   ❌ 프로젝트 저장 실패")

# ─────────────────────────────────────────────
# ✅ 최종 완료 메시지
# ─────────────────────────────────────────────
print("")
print("=" * 55)
print("🎉 모든 단계 완료! Burwood 3D 건물 시각화 프로젝트")
print("=" * 55)
print("")
print("📂 생성된 파일:")
print(f"   📄 burwood_buildings.geojson  - 건물 데이터")
print(f"   📸 burwood_2d_map.png         - 2D 렌더링 이미지")
print(f"   💾 burwood_3d.qgz             - QGIS 프로젝트 파일")
print("")
print("🗺️ 레이어 구성:")
print("   📍 Burwood Station Pin  - 빨간 별 마커")
print("   ⭕ 500m Buffer          - 파란 점선 원")
print("   🏢 Buildings            - 높이별 색상 건물")
print("   🗺️ OpenStreetMap        - 배경지도")
print("")
print("💡 3D 보기:")
print("   3D Map View 창에서 마우스로 회전/확대하세요!")
print("   메뉴 → View → 3D Map Views 에서 열 수 있어요")
print("")
print("🎊 축하합니다! 프로젝트가 완성되었습니다!")
