"""Transient-DNS handling in src/article_fetch.py::is_public_http_url.

Regression coverage for the 2026-10-06 unsafe_url false-positive fix: a
scrape-time EAI_AGAIN resolver blip used to return False ("definitively
unsafe"), permanently burning window items as unsafe_url failures. The
contract under test: EAI_AGAIN returns None (temporarily unverifiable —
callers fail closed but must not blacklist), NXDOMAIN/private IPs still
return False.
"""
import socket
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.article_fetch import is_public_http_url  # noqa: E402


class TransientDnsTests(unittest.TestCase):
    def test_transient_eai_again_returns_none(self):
        err = socket.gaierror()
        err.errno = getattr(socket, "EAI_AGAIN", 11002)
        with mock.patch("src.article_fetch.socket.getaddrinfo", side_effect=err):
            self.assertIsNone(is_public_http_url("https://dns-blip.example/article"))

    def test_transient_eai_fail_returns_none(self):
        err = socket.gaierror()
        err.errno = getattr(socket, "EAI_FAIL", 11003)
        with mock.patch("src.article_fetch.socket.getaddrinfo", side_effect=err):
            self.assertIsNone(is_public_http_url("https://dns-blip.example/article"))

    def test_nxdomain_still_false(self):
        err = socket.gaierror()
        err.errno = getattr(socket, "EAI_NONAME", 11001)
        with mock.patch("src.article_fetch.socket.getaddrinfo", side_effect=err):
            self.assertIs(is_public_http_url("https://nx.example/article"), False)

    def test_private_ip_still_false(self):
        with mock.patch(
            "src.article_fetch.socket.getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.5", 443))],
        ):
            self.assertIs(is_public_http_url("https://rebind.example/article"), False)

    def test_public_ip_true(self):
        with mock.patch(
            "src.article_fetch.socket.getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))],
        ):
            self.assertIs(is_public_http_url("https://fine.example/article"), True)

    def test_empty_url_false(self):
        self.assertIs(is_public_http_url(None), False)
        self.assertIs(is_public_http_url(""), False)


if __name__ == "__main__":
    unittest.main()
