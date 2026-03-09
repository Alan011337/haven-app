import configparser
from pathlib import Path
import unittest


class AlembicConfigSecurityTests(unittest.TestCase):
    def test_alembic_default_url_is_safe_local_value(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = configparser.ConfigParser()
        config.read(root / "alembic.ini")

        url = config.get("alembic", "sqlalchemy.url").strip()
        self.assertTrue(url.startswith("sqlite:///"))
        self.assertNotIn("@", url)
        self.assertNotIn("postgresql://", url)
        self.assertNotIn("supabase", url)


if __name__ == "__main__":
    unittest.main()
