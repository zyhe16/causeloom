from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "evals/harbor/relay/relay.py"
SPEC = importlib.util.spec_from_file_location("model_relay", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ModelRelayTest(unittest.TestCase):
    def test_normalizes_authority_and_websocket_origin_only(self):
        request = (
            b"GET /v1/responses HTTP/1.1\r\n"
            b"Host: model-relay:10101\r\n"
            b"Origin: http://model-relay:10101\r\n"
            b"Authorization: Bearer keep-me\r\n\r\n"
        )
        normalized = MODULE.normalize_request_headers(request)
        self.assertIn(b"Host: 127.0.0.1:10101\r\n", normalized)
        self.assertIn(b"Origin: http://127.0.0.1:10101\r\n", normalized)
        self.assertIn(b"Authorization: Bearer keep-me\r\n", normalized)
        self.assertNotIn(b"model-relay", normalized)


if __name__ == "__main__":
    unittest.main()
