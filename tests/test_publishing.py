import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import cli_publish
from local_state import load_state, save_state, state_lock
from planner import discover_packages, read_metadata
from publishing import prepare, publish

REPO = Path(__file__).resolve().parents[1]


class PublishingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.content = self.root / 'content'
        self.content.mkdir()
        self.add_package(1)
        self.config = {'content_root': str(self.content), 'start_date': '2099-03-28',
                       'timezone': 'Europe/Warsaw', 'client_secret': 'not-used.json',
                       'expected_channel_id': 'UC_expected', 'schedule_publication': True}
        self.config_path = self.root / 'config.json'
        self.config_path.write_text(json.dumps(self.config))
        self.state_path = self.root / 'upload_state.json'
        self.state = load_state(self.state_path)

    def add_package(self, number):
        package = self.content / f'film{number}'
        package.mkdir()
        (package / 'episode.mp4').write_bytes(b'test fixture, not a real video')
        (package / 'Miniatura.jpg').write_bytes(b'test thumbnail')
        blocks = ['MAIN VIDEO\nTitle: Episode\nDescription:\nAn episode\nTags: gaming, highlights']
        for index in range(1, 4):
            (package / f'Short_{index:02}.mp4').write_bytes(b'test short')
            blocks.append(f'SHORT {index}\nTitle: Short {index}\nDescription:\nA short\nTags: gaming')
        (package / 'YouTube.txt').write_text('\n\n'.join(blocks), encoding='utf-8')

    def reserve(self, plan):
        self.state['plan'] = {row['key']: row for row in plan['items']}

    def test_default_cli_preview_has_no_google_dependency_or_oauth(self):
        # Keep tzdata available on Windows while proving no Google package is imported.
        script = f"""
import runpy, sys
class BlockGoogle:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('google', 'googleapiclient', 'google_auth_oauthlib'):
            raise AssertionError('Offline preview imported ' + fullname)
sys.meta_path.insert(0, BlockGoogle())
sys.argv = {[str(REPO / 'cli_publish.py'), '--config', str(self.config_path), '--json']!r}
runpy.run_path({str(REPO / 'cli_publish.py')!r}, run_name='__main__')
"""
        result = subprocess.run([sys.executable, '-c', script], cwd=REPO,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        preview = json.loads(result.stdout)
        self.assertEqual(preview['new_upload_count'], 4)
        self.assertFalse(self.state_path.exists())
        self.assertFalse((self.root / 'token.json').exists())

    def test_upload_requires_approval_before_reading_config(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            cli_publish.main(['--config', '/missing/config.json', '--upload'])
        self.assertEqual(error.exception.code, 2)

    def test_changed_settings_invalidate_approval_before_authentication(self):
        _, _, digest = prepare(self.config, self.state)
        self.config['notify_main'] = False
        self.config_path.write_text(json.dumps(self.config))
        with patch('youtube_api.authenticate') as authenticate, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                cli_publish.main(['--config', str(self.config_path), '--upload', '--approve-plan', digest])
            self.assertEqual(error.exception.code, 2)
            authenticate.assert_not_called()

    def test_negative_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            prepare(self.config, self.state, -1)

    def test_moving_content_root_requires_reconciliation(self):
        self.state['content_root'] = str(self.root / 'old_location')
        with self.assertRaisesRegex(ValueError, 'Content root changed'):
            prepare(self.config, self.state)

    def test_limited_resume_keeps_all_reserved_dates_across_dst(self):
        items, plan, _ = prepare(self.config, self.state, 1)
        self.reserve(plan)
        first = items[0]
        self.state['uploads'][first.key] = {'video_id': 'v1', 'video': str(first.video),
            'publish_at': first.publish_at.isoformat(), 'thumbnail_set': True, 'playlist_added': True}
        resumed, next_plan, _ = prepare(self.config, self.state)
        self.assertEqual({item.key: item.publish_at for item in items},
                         {item.key: item.publish_at for item in resumed})
        self.assertNotIn(first.key, next_plan['selected_keys'])
        self.assertEqual(len(next_plan['selected_keys']), 3)
        # Europe/Warsaw crosses into DST during this package's schedule.
        self.assertNotEqual(items[0].publish_at.utcoffset(), items[-1].publish_at.utcoffset())

    def test_new_package_starts_after_reserved_tail(self):
        items, plan, _ = prepare(self.config, self.state, 1)
        self.reserve(plan)
        self.add_package(2)
        resumed, _, _ = prepare(self.config, self.state)
        old = [item for item in resumed if item.package.number == 1]
        new = [item for item in resumed if item.package.number == 2]
        self.assertEqual([item.publish_at for item in old], [item.publish_at for item in items])
        self.assertGreater(min(item.publish_at for item in new), max(item.publish_at for item in old))

    def test_changed_planned_metadata_or_file_blocks_resume(self):
        _, plan, _ = prepare(self.config, self.state)
        self.reserve(plan)
        metadata = self.content / 'film1' / 'YouTube.txt'
        metadata.write_text(metadata.read_text().replace('Episode', 'Changed episode'))
        with self.assertRaisesRegex(ValueError, 'metadata or asset changed'):
            prepare(self.config, self.state)
        metadata.write_text(metadata.read_text().replace('Changed episode', 'Episode'))
        (self.content / 'film1' / 'episode.mp4').write_bytes(b'changed video data')
        with self.assertRaisesRegex(ValueError, 'file changed'):
            prepare(self.config, self.state)

    def test_legacy_partial_package_uses_actual_dates(self):
        items, _, _ = prepare(self.config, self.state)
        first = items[0]
        self.state['uploads'][first.key] = {'video_id': 'legacy', 'video': str(first.video),
                                           'publish_at': first.publish_at.isoformat()}
        resumed, _, _ = prepare(self.config, self.state)
        self.assertEqual([item.publish_at for item in resumed], [item.publish_at for item in items])

    def test_ambiguous_upload_leaves_persisted_intent_and_blocks_retry(self):
        items, plan, _ = prepare(self.config, self.state, 1)
        with patch('youtube_api.connected_channel', return_value={'id': 'UC_expected'}), \
             patch('youtube_api.upload_video', side_effect=TimeoutError('unknown remote outcome')):
            with self.assertRaises(TimeoutError):
                publish(Mock(), self.config, self.state, self.state_path, items, plan, progress=lambda _: None)
        saved = load_state(self.state_path)
        self.assertEqual(saved['inflight']['key'], items[0].key)
        with self.assertRaisesRegex(ValueError, 'unknown outcome'):
            prepare(self.config, saved)

    def test_wrong_channel_blocks_all_mutations(self):
        items, plan, _ = prepare(self.config, self.state)
        with patch('youtube_api.connected_channel', return_value={'id': 'UC_wrong'}), \
             patch('youtube_api.upload_video') as upload:
            with self.assertRaisesRegex(ValueError, 'channel does not match'):
                publish(Mock(), self.config, self.state, self.state_path, items, plan, progress=lambda _: None)
            upload.assert_not_called()
            self.assertFalse(self.state_path.exists())

    def test_past_schedule_blocks_all_mutations(self):
        self.config['start_date'] = '2020-01-01'
        items, plan, _ = prepare(self.config, self.state)
        with patch('youtube_api.connected_channel', return_value={'id': 'UC_expected'}), \
             patch('youtube_api.upload_video') as upload:
            with self.assertRaisesRegex(ValueError, 'past'):
                publish(Mock(), self.config, self.state, self.state_path, items, plan, progress=lambda _: None)
            upload.assert_not_called()

    def test_thumbnail_failure_resumes_both_supplementary_steps_without_reupload(self):
        items, plan, _ = prepare(self.config, self.state, 1)
        with patch('youtube_api.connected_channel', return_value={'id': 'UC_expected'}), \
             patch('youtube_api.upload_video', return_value='video_1') as upload, \
             patch('youtube_api.set_thumbnail', side_effect=RuntimeError('thumbnail failed')):
            with self.assertRaisesRegex(RuntimeError, 'thumbnail failed'):
                publish(Mock(), self.config, self.state, self.state_path, items, plan, progress=lambda _: None)
            upload.assert_called_once()
        saved = load_state(self.state_path)
        self.assertNotIn('inflight', saved)
        self.assertEqual(saved['uploads'][items[0].key]['video_id'], 'video_1')
        # Remove upload candidates to isolate repairs for the existing video.
        repair_items = [items[0]]
        _, repair_plan, _ = prepare(self.config, saved)
        repair_plan['selected_keys'] = []
        with patch('youtube_api.connected_channel', return_value={'id': 'UC_expected'}), \
             patch('youtube_api.upload_video') as upload, \
             patch('youtube_api.set_thumbnail') as thumbnail, \
             patch('youtube_api.ensure_playlist', return_value='playlist_1'), \
             patch('youtube_api.add_to_playlist') as playlist:
            publish(Mock(), self.config, saved, self.state_path, repair_items, repair_plan)
            upload.assert_not_called()
            thumbnail.assert_called_once()
            playlist.assert_called_once_with(unittest.mock.ANY, 'playlist_1', 'video_1')
        finished = load_state(self.state_path)['uploads'][items[0].key]
        self.assertTrue(finished['thumbnail_set'])
        self.assertTrue(finished['playlist_added'])

    def test_private_upload_does_not_implicitly_enable_scheduling(self):
        self.config.pop('schedule_publication')
        self.config['api_audited'] = True  # Legacy flag grants no publishing permission.
        items, plan, _ = prepare(self.config, self.state, 1)
        with patch('youtube_api.connected_channel', return_value={'id': 'UC_expected'}), \
             patch('youtube_api.upload_video', return_value='private_video') as upload, \
             patch('youtube_api.set_thumbnail'), patch('youtube_api.ensure_playlist', return_value='p'), \
             patch('youtube_api.add_to_playlist'):
            publish(Mock(), self.config, self.state, self.state_path, items, plan, progress=lambda _: None)
            self.assertFalse(upload.call_args.args[5])
        self.assertFalse(self.state['uploads'][items[0].key]['scheduled'])

    def test_state_lock_excludes_second_process_and_releases(self):
        code = 'from pathlib import Path; from local_state import state_lock; ' \
               f'ctx=state_lock(Path({str(self.state_path)!r})); ctx.__enter__()'
        with state_lock(self.state_path):
            result = subprocess.run([sys.executable, '-c', code], cwd=REPO, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'Another publisher', result.stderr)
        with state_lock(self.state_path):
            pass

    def test_invalid_state_is_never_reset(self):
        self.state_path.write_text('{"wrong": "shape"}')
        with self.assertRaises(ValueError):
            load_state(self.state_path)
        self.assertEqual(json.loads(self.state_path.read_text()), {'wrong': 'shape'})

    @unittest.skipIf(os.name == 'nt', 'POSIX permissions')
    def test_state_file_is_private(self):
        save_state(self.state_path, self.state)
        self.assertEqual(self.state_path.stat().st_mode & 0o777, 0o600)

    def test_ambiguous_metadata_files_are_rejected(self):
        (self.content / 'film1' / 'YouTube_other.txt').write_text('MAIN VIDEO')
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            discover_packages(self.content)

    def test_duplicate_metadata_sections_are_rejected(self):
        path = self.root / 'metadata.txt'
        path.write_text('MAIN VIDEO\nTitle: A\nMAIN VIDEO\nTitle: B')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            read_metadata(path)


if __name__ == '__main__':
    unittest.main()
