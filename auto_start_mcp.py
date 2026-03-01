"""
QGIS --code로 실행되는 MCP 서버 자동 시작 스크립트
이 파일은 QGIS 내부 Python 환경에서 실행됩니다.
"""
from qgis.PyQt.QtCore import QTimer


def _start_mcp_server():
    """MCP 서버를 시작하는 함수 (QGIS 초기화 후 실행)"""
    try:
        from qgis.utils import iface
        from qgis.core import QgsMessageLog

        if iface is None:
            QTimer.singleShot(1000, _start_mcp_server)
            return

        # 플러그인 디렉토리에서 직접 서버 클래스 import
        import sys
        import os
        plugins_dir = os.path.join(
            os.path.expanduser("~"),
            "Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins"
        )
        if plugins_dir not in sys.path:
            sys.path.insert(0, plugins_dir)

        from qgis_mcp_plugin.qgis_mcp_plugin import QgisMCPServer

        server = QgisMCPServer(port=9876, iface=iface)
        if server.start():
            # GC 방지를 위해 builtins에 저장
            import builtins
            builtins._mcp_auto_server = server
            QgsMessageLog.logMessage(
                "MCP 서버 자동 시작 완료 (port 9876)", "QGIS MCP"
            )
        else:
            QgsMessageLog.logMessage(
                "MCP 서버 시작 실패", "QGIS MCP"
            )

    except Exception as e:
        from qgis.core import QgsMessageLog, Qgis
        QgsMessageLog.logMessage(
            f"MCP 자동 시작 에러: {e}", "QGIS MCP", Qgis.Warning
        )


# 3초 후 서버 시작 (QGIS 완전 초기화 대기)
QTimer.singleShot(3000, _start_mcp_server)
