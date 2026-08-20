import tempfile
import unittest
from datetime import date
from pathlib import Path

from planner import Metadata, Package, build_queue, round_robin


class PlannerTests(unittest.TestCase):
    def package(self, root: Path, number: int, game: str, kind: str) -> Package:
        folder = root / f"film{number}"
        folder.mkdir()
        main = folder / "film.mp4"
        main.write_bytes(b"video")
        shorts = []
        for index in range(1, 4):
            path = folder / f"short{index}.mp4"
            path.write_bytes(b"short")
            shorts.append((path, Metadata(f"Short {index}", "Opis", ("tag",))))
        return Package(folder, number, game, kind, main, None,
                       Metadata("Film", "Opis", ("tag",)), tuple(shorts))

    def test_round_robin_alternates_games(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packages = [
                self.package(root, 1, "L4D2", "kompilacja"),
                self.package(root, 2, "L4D2", "pelna_rozgrywka"),
                self.package(root, 3, "PUBG", "kompilacja"),
            ]
            ordered = round_robin(packages, ["L4D2", "PUBG"],
                                  ["kompilacja", "pelna_rozgrywka"])
            self.assertEqual([item.game for item in ordered], ["L4D2", "PUBG", "L4D2"])

    def test_two_packages_use_main_first_five_day_schedule(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = self.package(root, 1, "L4D2", "kompilacja")
            second = self.package(root, 2, "PUBG", "kompilacja")
            queue = build_queue([first, second], date(2026, 8, 1))
            slots = [
                (item.package.number, item.kind, item.index, item.publish_at.day, item.publish_at.hour)
                for item in queue
            ]
            self.assertEqual(
                slots,
                [
                    (1, "film", 0, 1, 15),
                    (1, "short", 1, 1, 18),
                    (1, "short", 2, 2, 18),
                    (2, "film", 0, 3, 15),
                    (2, "short", 1, 3, 18),
                    (2, "short", 2, 4, 18),
                    (1, "short", 3, 5, 15),
                    (2, "short", 3, 5, 18),
                ],
            )


if __name__ == "__main__":
    unittest.main()
