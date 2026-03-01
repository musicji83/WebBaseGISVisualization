"""
========================================================
🏢 Step 2: OSM 건물 데이터 다운로드
========================================================
📌 하는 일:
    1. Overpass API로 Burwood Station 500m 반경 건물 데이터를 가져와요
    2. 건물 높이 정보를 계산해요 (층수, height 태그 등)
    3. GeoJSON 파일로 저장해요
    4. QGIS 레이어로 로드해요

🔧 사용법: Step 1 실행 후, QGIS Python 콘솔에서 실행하세요
========================================================
"""

import json
import os
import urllib.request
import urllib.parse

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
)
from qgis.PyQt.QtCore import QVariant
from qgis.utils import iface

# ─────────────────────────────────────────────
# 📍 설정값
# ─────────────────────────────────────────────
BURWOOD_LAT = -33.8773
BURWOOD_LNG = 151.1043
BUFFER_RADIUS_M = 500

# GeoJSON 저장 경로
# 💡 비유: 다운로드한 건물 데이터를 어디에 저장할지 정하는 거예요
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.path.expanduser("~/Desktop/QGIS_MCP")
GEOJSON_PATH = os.path.join(SCRIPT_DIR, "burwood_buildings.geojson")

# 기본 건물 높이 (태그가 없을 때)
# 💡 비유: 건물 높이를 모르면 "대충 3층 건물(9m)"이라고 가정해요
DEFAULT_HEIGHT_M = 9.0
METERS_PER_LEVEL = 3.0  # 한 층 = 3미터

# ─────────────────────────────────────────────
# 🌐 1단계: Overpass API로 건물 데이터 다운로드
# ─────────────────────────────────────────────
# 💡 비유: OpenStreetMap 서버에 "이 근처 건물 정보 줘!" 라고 부탁하는 거예요
print("🌐 Overpass API에서 건물 데이터를 다운로드하고 있어요...")
print(f"   📍 중심: ({BURWOOD_LAT}, {BURWOOD_LNG})")
print(f"   ⭕ 반경: {BUFFER_RADIUS_M}m")

# Overpass QL 쿼리
# 💡 설명: "이 위치 주변 500m 안에 있는 모든 건물(way와 relation)을 찾아줘"
overpass_query = f"""
[out:json][timeout:60];
(
  way["building"](around:{BUFFER_RADIUS_M},{BURWOOD_LAT},{BURWOOD_LNG});
  relation["building"](around:{BUFFER_RADIUS_M},{BURWOOD_LAT},{BURWOOD_LNG});
);
out body;
>;
out skel qt;
"""

overpass_url = "https://overpass-api.de/api/interpreter"
encoded_data = urllib.parse.urlencode({"data": overpass_query}).encode("utf-8")

try:
    req = urllib.request.Request(overpass_url, data=encoded_data)
    req.add_header("User-Agent", "QGIS-PyScript/1.0")
    with urllib.request.urlopen(req, timeout=120) as response:
        raw_data = json.loads(response.read().decode("utf-8"))
    print(f"   ✅ 데이터 수신 완료! (elements: {len(raw_data.get('elements', []))}개)")
except Exception as e:
    print(f"   ❌ 다운로드 실패: {e}")
    print("   💡 인터넷 연결을 확인하거나 잠시 후 다시 시도해주세요")
    raise

# ─────────────────────────────────────────────
# 🔨 2단계: Overpass 응답을 GeoJSON으로 변환
# ─────────────────────────────────────────────
# 💡 비유: 서버에서 받은 날것의 데이터를 QGIS가 이해할 수 있는 형태로 바꾸는 거예요
print("🔨 건물 데이터를 GeoJSON으로 변환하고 있어요...")

elements = raw_data.get("elements", [])

# 노드(점) 좌표를 딕셔너리에 저장
# 💡 비유: 건물의 꼭짓점 좌표를 번호표(ID)로 정리하는 거예요
nodes = {}
for el in elements:
    if el["type"] == "node":
        nodes[el["id"]] = (el["lon"], el["lat"])

# Way(선/면)를 GeoJSON Feature로 변환
features = []
for el in elements:
    if el["type"] != "way":
        continue
    if "tags" not in el:
        continue
    if "building" not in el.get("tags", {}):
        continue

    # 건물 꼭짓점 좌표 리스트 만들기
    coords = []
    for nd_id in el.get("nodes", []):
        if nd_id in nodes:
            coords.append(list(nodes[nd_id]))

    # 폴리곤이 되려면 최소 4개 점 필요 (시작점=끝점 포함)
    if len(coords) < 4:
        continue

    # 폴리곤이 닫혀있는지 확인 (시작점 == 끝점)
    if coords[0] != coords[-1]:
        coords.append(coords[0])

    tags = el.get("tags", {})

    # ───── 건물 높이 계산 ─────
    # 💡 비유: 건물이 몇 미터 높은지 알아내는 과정이에요
    #    1순위: "height" 태그가 있으면 그걸 쓰고
    #    2순위: "building:levels"(층수)가 있으면 층수 × 3m
    #    3순위: 아무것도 없으면 기본 9m (3층 건물)
    height = DEFAULT_HEIGHT_M
    if "height" in tags:
        try:
            h_str = tags["height"].replace("m", "").replace(" ", "")
            height = float(h_str)
        except ValueError:
            pass
    elif "building:levels" in tags:
        try:
            levels = float(tags["building:levels"])
            height = levels * METERS_PER_LEVEL
        except ValueError:
            pass

    # GeoJSON Feature 생성
    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [coords],
        },
        "properties": {
            "osm_id": el["id"],
            "building": tags.get("building", "yes"),
            "name": tags.get("name", ""),
            "height": height,
            "levels": tags.get("building:levels", ""),
            "addr_street": tags.get("addr:street", ""),
            "addr_housenumber": tags.get("addr:housenumber", ""),
        },
    }
    features.append(feature)

print(f"   ✅ 건물 {len(features)}개 변환 완료!")

# 높이 통계 출력
if features:
    heights = [f["properties"]["height"] for f in features]
    print(f"   📊 높이 통계:")
    print(f"      최소: {min(heights):.1f}m")
    print(f"      최대: {max(heights):.1f}m")
    print(f"      평균: {sum(heights)/len(heights):.1f}m")

# ─────────────────────────────────────────────
# 💾 3단계: GeoJSON 파일로 저장
# ─────────────────────────────────────────────
print(f"💾 GeoJSON 파일로 저장하고 있어요...")

geojson_data = {
    "type": "FeatureCollection",
    "crs": {
        "type": "name",
        "properties": {"name": "urn:ogc:def:crs:EPSG::4326"},
    },
    "features": features,
}

with open(GEOJSON_PATH, "w", encoding="utf-8") as f:
    json.dump(geojson_data, f, ensure_ascii=False, indent=2)

print(f"   ✅ 저장 완료: {GEOJSON_PATH}")

# ─────────────────────────────────────────────
# 📂 4단계: QGIS에 건물 레이어 로드
# ─────────────────────────────────────────────
print("📂 QGIS에 건물 레이어를 추가하고 있어요...")

building_layer = QgsVectorLayer(GEOJSON_PATH, "Buildings", "ogr")

if building_layer.isValid():
    QgsProject.instance().addMapLayer(building_layer)
    print(f"   ✅ 건물 레이어 추가 완료! (피처 {building_layer.featureCount()}개)")
else:
    print("   ❌ 레이어 로드 실패")
    print(f"   💡 파일 경로를 확인해주세요: {GEOJSON_PATH}")

# 맵 새로고침
iface.mapCanvas().refresh()

# ─────────────────────────────────────────────
# ✅ 완료 메시지
# ─────────────────────────────────────────────
print("")
print("=" * 50)
print("✅ Step 2 완료!")
print("=" * 50)
print(f"🏢 건물: {len(features)}개 다운로드 및 로드")
print(f"💾 파일: {GEOJSON_PATH}")
print("")
print("👉 다음 단계: burwood_3d_step3_style.py 를 실행하세요!")
