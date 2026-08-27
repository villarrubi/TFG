import json
import os
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXTENSION = os.path.join(ROOT, "extension_gmail")


class TestExtensionAssets(unittest.TestCase):
    def test_manifest_carga_configuracion_antes_del_content_script(self):
        with open(os.path.join(EXTENSION, "manifest.json"), encoding="utf-8") as file:
            manifest = json.load(file)

        scripts = manifest["content_scripts"][0]["js"]
        self.assertEqual(scripts[:2], ["server_config.js", "content.js"])
        self.assertEqual(
            set(manifest["host_permissions"]),
            {"http://127.0.0.1/*", "http://localhost/*"},
        )
        self.assertEqual(manifest["optional_host_permissions"], ["https://*/*"])

    def test_no_quedan_endpoints_fijos_en_los_consumidores(self):
        for filename in ("content.js", "options.js"):
            with open(os.path.join(EXTENSION, filename), encoding="utf-8") as file:
                source = file.read()
            self.assertNotIn("127.0.0.1:8765", source)
            self.assertIn("PhishingServerConfig", source)

        with open(os.path.join(EXTENSION, "server_config.js"), encoding="utf-8") as file:
            configuration = file.read()
        self.assertIn("127.0.0.1:8766", configuration)
        self.assertIn("HTTP solo se admite en local", configuration)
        self.assertIn("permissionOrigin", configuration)

        with open(os.path.join(EXTENSION, "content.js"), encoding="utf-8") as file:
            content = file.read()
        self.assertIn("MAX_FIELD_CHARS", content)
        self.assertIn("requestError.retryable", content)

        with open(os.path.join(EXTENSION, "options.html"), encoding="utf-8") as file:
            options = file.read()
        self.assertIn("python src/backend_server.py", options)
        self.assertNotIn("127.0.0.1:8765", options)


if __name__ == "__main__":
    unittest.main()
