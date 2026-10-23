from __future__ import annotations

import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SiteSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = load_module("demo_site_builder_test", ROOT / "build_site.py")
        cls.checker = load_module("demo_site_checker_test", ROOT / "check_site.py")
        cls.builder.main()
        cls.routes = json.loads((ROOT / "routes.json").read_text(encoding="utf-8"))

    def body(self, route: str) -> str:
        return (ROOT / "docs" / route / "index.html").read_text(encoding="utf-8")

    def test_google_pages_are_dense_and_inert(self) -> None:
        routes = [
            "drive/file/d/1A3fRQ2026FacilitiesRFQ/view/",
            "drive/file/d/1A3fRQ2026FacilitiesRFQ/preview/",
            "drive/drive/folders/0B2vRFQProcurementQ3/",
            "google/accounts/ServiceLogin/",
            "google/careers/jobs/results/GBR-74291/",
            "google/cloud/application-integration/captcha/",
        ]
        forbidden = re.compile(
            r"<\s*(?:form|input|button|select|textarea|script|iframe|object|embed)\b",
            re.I,
        )
        for route in routes:
            with self.subTest(route=route):
                body = self.body(route)
                self.assertIn("Sublime Security Demo Asset", body)
                self.assertIn('data-dense-preview="700x520"', body)
                self.assertIsNone(forbidden.search(body))

    def test_inert_wording_allowance_is_explicit(self) -> None:
        body = self.body("google/accounts/ServiceLogin/")
        allowed = self.checker.content_problems(body, [], "google-login")
        standard = self.checker.content_problems(body, [], "standard")
        self.assertNotIn("login, credential, CAPTCHA or challenge wording", allowed)
        self.assertIn("login, credential, CAPTCHA or challenge wording", standard)

    def test_tampered_real_input_is_rejected(self) -> None:
        body = self.body("google/accounts/ServiceLogin/").replace(
            "</body>",
            '<input type="email" name="email"></body>',
        )
        problems = self.checker.content_problems(body, [], "google-login")
        self.assertIn("active or external element", problems)

    def test_cloud_hop_is_same_host_and_registered(self) -> None:
        code = self.builder.short_code("google_cloud_captcha")
        route = next(
            item for item in self.routes["routes"] if item["path"] == f"s/{code}/"
        )
        self.assertEqual(route["kind"], "meta-refresh")
        self.assertEqual(route["content_kind"], "google-captcha-login")
        self.assertEqual(
            route["refresh_to"],
            "google/cloud/application-integration/captcha/",
        )


if __name__ == "__main__":
    unittest.main()
