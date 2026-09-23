import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parents[1] / "app.py")


class AppTests(unittest.TestCase):
    def test_demo_and_speaker_mapping(self):
        app = AppTest.from_file(APP_PATH).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "Quryltai AI")
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe[0].value), 5)
        app.text_input(key="name_speaker_1").set_value("Алия").run()
        self.assertFalse(app.exception)
        self.assertIn("Алия", app.dataframe[0].value["Responsible person"].tolist())
        self.assertTrue(all(button.disabled for button in app.button if button.label.startswith("Export")))

    def test_non_demo_does_not_generate_fake_results(self):
        app = AppTest.from_file(APP_PATH).run()
        app.toggle[0].set_value(False).run()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.error)
        self.assertEqual(len(app.dataframe), 0)

    def test_empty_title_has_useful_error(self):
        app = AppTest.from_file(APP_PATH).run()
        app.text_input[0].set_value("   ")
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.error)


if __name__ == "__main__":
    unittest.main()
