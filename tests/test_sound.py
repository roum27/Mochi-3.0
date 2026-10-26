import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mochi.sound import CommandAudioBackend, SoundEvent, SoundManager


class FakeBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, float]] = []

    def play(self, path: Path, volume: float) -> None:
        self.calls.append((path, volume))


class CommandAudioBackendTests(unittest.TestCase):
    def _launch(self, kind: str, environ: dict[str, str]) -> tuple[tuple, dict]:
        backend = CommandAudioBackend(f"/usr/bin/{kind}", kind)
        with (
            patch.dict("mochi.sound.os.environ", environ, clear=True),
            patch("mochi.sound.subprocess.Popen") as popen,
        ):
            backend.play(Path("/tmp/chirp.ogg"), 0.6)
        args, kwargs = popen.call_args
        return args[0], kwargs["env"]

    def test_pw_play_parses_volume_with_c_numerics_on_a_french_locale(self) -> None:
        # pw-play reads --volume with the locale's decimal separator, so on
        # fr_CA "0.6" silently became 0 and Mochi was mute.
        command, env = self._launch(
            "pw-play",
            {"LANG": "fr_CA.UTF-8", "LC_ALL": "fr_CA.UTF-8", "LC_NUMERIC": "fr_CA.UTF-8"},
        )
        self.assertEqual(command, ("/usr/bin/pw-play", "--volume", "0.6", "/tmp/chirp.ogg"))
        self.assertEqual(env["LC_NUMERIC"], "C")
        self.assertNotIn("LC_ALL", env)
        self.assertEqual(env["LANG"], "fr_CA.UTF-8")

    def test_paplay_keeps_its_integer_volume(self) -> None:
        command, env = self._launch("paplay", {"LANG": "fr_CA.UTF-8"})
        self.assertEqual(command, ("/usr/bin/paplay", "--volume=39322", "/tmp/chirp.ogg"))
        self.assertEqual(env["LC_NUMERIC"], "C")


class SoundManagerTests(unittest.TestCase):
    def test_missing_placeholder_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager = SoundManager(asset_root=Path(directory), backend=FakeBackend())
            self.assertFalse(manager.play(SoundEvent.PET))

    def test_volume_and_mute_apply_globally(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pet.wav").touch()
            backend = FakeBackend()
            manager = SoundManager(volume=0.4, asset_root=root, backend=backend)
            self.assertTrue(manager.play(SoundEvent.PET))
            self.assertEqual(backend.calls, [(root / "pet.wav", 0.4)])

            manager.set_muted(True)
            self.assertFalse(manager.play(SoundEvent.PET))
            self.assertEqual(len(backend.calls), 1)

    def test_level_up_hook_uses_registered_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "level_up.ogg").touch()
            backend = FakeBackend()
            manager = SoundManager(asset_root=root, backend=backend)
            self.assertTrue(manager.play_level_up())
            self.assertEqual(backend.calls[0][0].name, "level_up.ogg")

    def test_shipped_level_up_sound_asset_exists(self) -> None:
        root = Path(__file__).resolve().parents[1] / "assets" / "audio"
        path = root / SoundManager.EVENT_FILES[SoundEvent.LEVEL_UP]

        self.assertTrue(path.is_file())
        self.assertGreater(path.stat().st_size, 1_000)

    def test_lifecycle_sounds_use_subtle_event_gain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "spawn.ogg").touch()
            (root / "exit.ogg").touch()
            backend = FakeBackend()
            manager = SoundManager(volume=0.6, asset_root=root, backend=backend)

            self.assertTrue(manager.play(SoundEvent.SPAWN))
            self.assertTrue(manager.play(SoundEvent.EXIT))
            self.assertEqual(backend.calls[0][0].name, "spawn.ogg")
            self.assertAlmostEqual(backend.calls[0][1], 0.21)
            self.assertEqual(backend.calls[1][0].name, "exit.ogg")
            self.assertAlmostEqual(backend.calls[1][1], 0.168)

    def test_context_menu_sound_is_intentionally_quiet(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "menu_open.ogg").touch()
            backend = FakeBackend()
            manager = SoundManager(volume=0.6, asset_root=root, backend=backend)

            self.assertTrue(manager.play(SoundEvent.MENU_OPEN))
            self.assertEqual(backend.calls[0][0].name, "menu_open.ogg")
            self.assertAlmostEqual(backend.calls[0][1], 0.132)

    def test_volume_is_clamped(self) -> None:
        manager = SoundManager(volume=9, backend=FakeBackend())
        self.assertEqual(manager.volume, 1.0)
        manager.set_volume(-1)
        self.assertEqual(manager.volume, 0.0)


if __name__ == "__main__":
    unittest.main()
