"""CORS 回归测试：安卓 APK（Capacitor WebView）跨域调用远程后端必须被放行。

Web 版同源托管不受影响；未知 origin 不得获得 allow-origin 头（白名单外拒绝）。
"""

import unittest

from app.main import app
from fastapi.testclient import TestClient


class CorsTests(unittest.TestCase):
    def test_preflight_from_capacitor_android_origin_allowed(self):
        """APK 内 axios 带 Authorization 头的预检请求必须通过。"""
        with TestClient(app) as client:
            r = client.options(
                "/api/auth/login",
                headers={
                    "Origin": "https://localhost",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "authorization,content-type",
                },
            )
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.headers.get("access-control-allow-origin"), "https://localhost")
            self.assertIn(
                "authorization", r.headers.get("access-control-allow-headers", "").lower()
            )

    def test_actual_request_carries_allow_origin(self):
        with TestClient(app) as client:
            r = client.get("/health", headers={"Origin": "capacitor://localhost"})
            self.assertEqual(r.headers.get("access-control-allow-origin"), "capacitor://localhost")

    def test_unknown_origin_not_allowed(self):
        with TestClient(app) as client:
            r = client.get("/health", headers={"Origin": "https://evil.example.com"})
            self.assertNotIn("access-control-allow-origin", r.headers)


if __name__ == "__main__":
    unittest.main()
