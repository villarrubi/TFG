import unittest

from backend_server import validar_token_remoto
from sistema_phishing.network import (
    UnsafeBindAddressError,
    es_host_loopback,
    validar_host_local,
)


class TestNetworkSafety(unittest.TestCase):
    def test_reconoce_hosts_loopback(self):
        for host in ("127.0.0.1", "127.0.0.2", "::1", "localhost"):
            with self.subTest(host=host):
                self.assertTrue(es_host_loopback(host))

    def test_rechaza_bind_remoto_por_defecto(self):
        for host in ("0.0.0.0", "192.168.1.10", "example.com", ""):
            with self.subTest(host=host), self.assertRaises(UnsafeBindAddressError):
                validar_host_local(host)

    def test_exposicion_remota_requiere_flag_explicito(self):
        self.assertEqual(
            validar_host_local("0.0.0.0", allow_remote=True),
            "0.0.0.0",
        )

    def test_bind_remoto_exige_token_administrativo_robusto(self):
        validar_token_remoto(False, "")
        with self.assertRaisesRegex(SystemExit, "24 caracteres"):
            validar_token_remoto(True, "demasiado-corto")
        validar_token_remoto(True, "a" * 24)


if __name__ == "__main__":
    unittest.main()
