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

    def test_package_uses_three_day_schedule(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = self.package(Path(tmp), 1, "L4D2", "kompilacja")
            queue = build_queue([package], date(2026, 8, 1))
            self.assertEqual([item.publish_at.hour for item in queue], [15, 15, 15, 18])
            self.assertEqual(queue[-1].publish_at.date(), date(2026, 8, 3))


if __name__ == "__main__":
    unittest.main()
