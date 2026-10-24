import unittest

from app.utils.certificate_lookup import certificate_number_key


class CertificateNumberKeyTests(unittest.TestCase):
    def test_trims_and_uppercases(self):
        self.assertEqual(certificate_number_key("  g2506097127 "), "G2506097127")

    def test_keeps_old_number_formats(self):
        for number in ("G25022774", "GAC12345", "G206040113617"):
            self.assertEqual(certificate_number_key(number), number)

    def test_rejects_empty_and_oversized_values(self):
        for value in ("", "   ", None, 123, "G" * 65):
            self.assertIsNone(certificate_number_key(value))


if __name__ == "__main__":
    unittest.main()
