from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from __PACKAGE_NAME__.secrets import SecretProviderError, SecretResolver, read_secret_file


class SecretResolverTests(unittest.TestCase):
    def test_environment_mode(self) -> None:
        resolver = SecretResolver.from_environment(
            {"BOT_SECRET_MODE": "env", "FEISHU_APP_SECRET": "value"}
        )
        self.assertEqual(resolver.get("FEISHU_APP_SECRET"), "value")
        self.assertEqual(resolver.public_summary()["mode"], "env")

    @unittest.skipIf(os.name != "posix", "POSIX permission check")
    def test_file_mode_requires_restricted_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "secrets.txt"
            path.write_text("FEISHU_APP_SECRET=value\n", encoding="utf-8")
            path.chmod(0o644)
            with self.assertRaisesRegex(SecretProviderError, "0600"):
                read_secret_file(path)
            path.chmod(0o600)
            self.assertEqual(read_secret_file(path)["FEISHU_APP_SECRET"], "value")

    def test_file_mode_rejects_duplicate_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "secrets.txt"
            path.write_text("TOKEN=one\nTOKEN=two\n", encoding="utf-8")
            path.chmod(0o600)
            with self.assertRaisesRegex(SecretProviderError, "duplicate"):
                read_secret_file(path)

    def test_missing_required_secret_is_visible_without_value(self) -> None:
        resolver = SecretResolver(mode="env", values={})
        with self.assertRaisesRegex(SecretProviderError, "NOT_SET"):
            resolver.get("NOT_SET")


if __name__ == "__main__":
    unittest.main()
