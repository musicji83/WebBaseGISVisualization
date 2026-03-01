#!/usr/bin/env python3
"""
========================================================
🚀 QGIS 자동 실행 + MCP 서버 대기 + Step 1~5 실행
========================================================
📌 하는 일:
    1. QGIS가 꺼져있으면 자동으로 실행
    2. MCP 서버가 켜질 때까지 대기 (auto_start_mcp.py가 자동으로 켜줌)
    3. Step 1→2→3→5→4 순서로 실행
       (⚠️ Step 4의 setRenderer3D()가 QGIS 상태를 망가뜨리므로
        렌더링/저장(Step 5)을 먼저 하고, 3D 설정(Step 4)은 마지막에!)
    4. 각 단계 결과를 출력

🔧 사용법: 터미널에서 python3 run_all_steps.py
========================================================
"""

import socket
import json
import subprocess
import time
import sys
import os

# ─────────────────────────────────────────────
# 📍 설정
# ─────────────────────────────────────────────
MCP_HOST = "localhost"
MCP_PORT = 9876
QGIS_APP = "/Applications/QGIS.app"
QGIS_BIN = "/Applications/QGIS.app/Contents/MacOS/QGIS"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AUTO_START_SCRIPT = os.path.join(SCRIPT_DIR, "auto_start_mcp.py")

# MCP 서버 대기 최대 시간 (초)
MAX_WAIT_SECONDS = 30


# ─────────────────────────────────────────────
# 🔧 유틸리티 함수들
# ─────────────────────────────────────────────
_persistent_socket = None


def _get_socket(timeout=120):
    """소켓을 하나 유지하고 재사용 (연결이 끊기면 재연결)"""
    global _persistent_socket
    if _persistent_socket is not None:
        try:
            # 연결 상태 확인
            _persistent_socket.settimeout(timeout)
            return _persistent_socket
        except Exception:
            _persistent_socket = None

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect((MCP_HOST, MCP_PORT))
    _persistent_socket = s
    return s


def send_command(cmd_type, params=None, timeout=120):
    """QGIS MCP 서버에 명령을 보내고 응답을 받는 함수 (단일 연결 유지)"""
    s = _get_socket(timeout)
    command = {"type": cmd_type, "params": params or {}}
    try:
        s.sendall(json.dumps(command).encode("utf-8"))
    except (BrokenPipeError, ConnectionResetError, OSError):
        # 연결이 끊긴 경우 재연결
        global _persistent_socket
        _persistent_socket = None
        s = _get_socket(timeout)
        s.sendall(json.dumps(command).encode("utf-8"))

    data = b""
    while True:
        chunk = s.recv(8192)
        if not chunk:
            break
        data += chunk
        try:
            json.loads(data.decode("utf-8"))
            break
        except json.JSONDecodeError:
            continue
    if not data:
        _persistent_socket = None
        return {"status": "error", "message": "빈 응답"}
    return json.loads(data.decode("utf-8"))


def is_qgis_running():
    """QGIS가 실행 중인지 확인"""
    result = subprocess.run(
        ["pgrep", "-f", "QGIS"],
        capture_output=True, text=True
    )
    return result.returncode == 0


def is_mcp_server_ready():
    """MCP 서버에 연결 가능한지 확인"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((MCP_HOST, MCP_PORT))
        s.close()
        return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False


def execute_step(step_name, code, timeout=120):
    """Step 코드를 실행하고 결과를 출력"""
    print(f"\n{'='*55}")
    print(f"  {step_name}")
    print(f"{'='*55}")

    try:
        result = send_command("execute_code", {"code": code}, timeout=timeout)
    except Exception as e:
        print(f"  ❌ 연결 실패: {e}")
        return False

    if result.get("status") != "success":
        print(f"  ❌ 서버 에러: {result.get('message', 'unknown')}")
        return False

    r = result["result"]
    if r.get("executed"):
        # stdout 출력 (각 줄 앞에 들여쓰기)
        for line in r["stdout"].strip().split("\n"):
            print(f"  {line}")
        if r.get("stderr"):
            print(f"  ⚠️ stderr: {r['stderr']}")
        return True
    else:
        print(f"  ❌ 실행 에러: {r.get('error', 'unknown')}")
        if r.get("traceback"):
            for line in r["traceback"].strip().split("\n")[-3:]:
                print(f"    {line}")
        return False


# ─────────────────────────────────────────────
# 🚀 메인 실행
# ─────────────────────────────────────────────
def main():
    print("🚀 QGIS MCP 자동 실행 스크립트")
    print("=" * 55)

    # 1) QGIS 실행 확인 & 시작
    if is_qgis_running():
        print("✅ QGIS가 이미 실행 중입니다")
    else:
        print("🔄 QGIS를 시작합니다 (--code로 MCP 서버 자동 시작)...")
        subprocess.Popen([QGIS_BIN, "--code", AUTO_START_SCRIPT])
        print("   QGIS 앱 + MCP 자동시작 스크립트 실행됨")

    # 2) MCP 서버 대기
    print(f"⏳ MCP 서버 대기 중... (최대 {MAX_WAIT_SECONDS}초)")
    for i in range(MAX_WAIT_SECONDS):
        if is_mcp_server_ready():
            # ping으로 실제 동작 확인
            try:
                r = send_command("ping", timeout=5)
                if r.get("status") == "success":
                    print(f"   ✅ MCP 서버 준비 완료! ({i+1}초 소요)")
                    break
            except Exception:
                pass
        time.sleep(1)
        if (i + 1) % 5 == 0:
            print(f"   ... {i+1}초 경과")
    else:
        print("❌ MCP 서버 연결 시간 초과")
        print("   QGIS에서 플러그인 → QGIS MCP → Start Server를 확인해주세요")
        sys.exit(1)

    # 3) Step 1: 프로젝트 초기 설정
    with open(os.path.join(SCRIPT_DIR, "burwood_3d_step1_setup.py")) as f:
        step1_code = f.read()
    if not execute_step("📍 Step 1: 프로젝트 초기 설정", step1_code):
        sys.exit(1)

    # 4) Step 2: 건물 데이터 로드 (기존 GeoJSON 사용)
    geojson_path = os.path.join(SCRIPT_DIR, "burwood_buildings.geojson")
    step2_code = f'''
import os
from qgis.core import QgsProject, QgsVectorLayer
from qgis.utils import iface

GEOJSON_PATH = "{geojson_path}"
print("📂 burwood_buildings.geojson 로드 중...")
building_layer = QgsVectorLayer(GEOJSON_PATH, "Buildings", "ogr")
if building_layer.isValid():
    QgsProject.instance().addMapLayer(building_layer)
    print(f"   ✅ 건물 레이어 추가 완료! (피처 {{building_layer.featureCount()}}개)")
else:
    print("   ❌ 레이어 로드 실패")
    raise Exception("Buildings layer load failed")
iface.mapCanvas().refresh()
print("✅ Step 2 완료!")
'''
    if not execute_step("🏢 Step 2: 건물 레이어 로드", step2_code):
        sys.exit(1)

    # 5) Step 3: 스타일링
    with open(os.path.join(SCRIPT_DIR, "burwood_3d_step3_style.py")) as f:
        step3_code = f.read()
    if not execute_step("🎨 Step 3: 레이어 스타일링", step3_code):
        sys.exit(1)

    # 6) Step 5: 렌더링 & 저장 (⚠️ Step 4보다 먼저 실행!)
    # 💡 이유: setRenderer3D()가 QGIS 내부 상태를 망가뜨려서
    #    이후 execute_code 명령이 모두 크래시함
    #    → 2D 렌더링과 프로젝트 저장을 먼저 하고, 3D 설정은 마지막에!
    with open(os.path.join(SCRIPT_DIR, "burwood_3d_step5_render.py")) as f:
        step5_code = f.read()
    if not execute_step("📸 Step 5: 렌더링 & 프로젝트 저장", step5_code, timeout=180):
        sys.exit(1)

    # 7) Step 4: 3D 설정 (마지막에 실행 - 이후 명령이 없으므로 안전)
    # ⚠️ setRenderer3D() 호출 후 QGIS MCP 통신이 불안정해질 수 있음
    #    하지만 마지막 단계이므로 크래시되어도 모든 파일은 이미 저장됨
    with open(os.path.join(SCRIPT_DIR, "burwood_3d_step4_3dview.py")) as f:
        step4_code = f.read()
    if not execute_step("🏙️ Step 4: 3D Map View 설정", step4_code):
        print("  ⚠️ Step 4 실패했지만 렌더링/저장은 이미 완료됨!")
        print("  💡 3D 뷰는 QGIS에서 수동으로 설정할 수 있어요")

    # 완료!
    print(f"\n{'='*55}")
    print("🎉 모든 단계 완료!")
    print(f"{'='*55}")
    print(f"📂 생성된 파일:")
    print(f"   📄 {os.path.join(SCRIPT_DIR, 'burwood_buildings.geojson')}")
    print(f"   📸 {os.path.join(SCRIPT_DIR, 'burwood_2d_map.png')}")
    print(f"   💾 {os.path.join(SCRIPT_DIR, 'burwood_3d.qgz')}")


if __name__ == "__main__":
    main()
