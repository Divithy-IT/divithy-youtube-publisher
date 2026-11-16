import tempfile
import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from planner import Metadata, Package, QueueItem
from youtube_api import upload_video, ensure_playlist


class ApiRequestTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        video = Path(self.temporary.name) / 'episode.mp4'
        video.write_bytes(b'test fixture')
        metadata = Metadata('Example', 'Description', ('example',))
        package = Package(video.parent, 1, 'Series', 'kompilacja', video, None, metadata, ())
        self.item = QueueItem(package, 'film', 0, video, None, metadata,
                              datetime.now(timezone.utc) + timedelta(days=2))
        self.youtube = Mock()
        self.youtube.videos.return_value.insert.return_value.next_chunk.return_value = (None, {'id': 'v'})

    def test_private_only_request_has_no_publish_at(self):
        result = upload_video(self.youtube, self.item, False, '20', False, False, lambda _: None, 'en')
        request = self.youtube.videos.return_value.insert.call_args.kwargs
        self.assertEqual(result, 'v')
        self.assertEqual(request['body']['status']['privacyStatus'], 'private')
        self.assertNotIn('publishAt', request['body']['status'])
        self.assertEqual(request['body']['snippet']['defaultLanguage'], 'en')
        self.assertFalse(request['notifySubscribers'])

    def test_scheduled_request_is_private_until_future_utc_date(self):
        upload_video(self.youtube, self.item, True, '20', False, True, lambda _: None)
        body = self.youtube.videos.return_value.insert.call_args.kwargs['body']
        self.assertEqual(body['status']['privacyStatus'], 'private')
        self.assertEqual(body['status']['publishAt'], self.item.publish_at.isoformat().replace('+00:00', 'Z'))

    def test_expired_date_is_rejected_before_insert(self):
        item = replace(self.item, publish_at=datetime.now(timezone.utc) - timedelta(seconds=1))
        with self.assertRaises(ValueError):
            upload_video(self.youtube, item, False, '20', False, True, lambda _: None)
        self.youtube.videos.assert_not_called()

    def test_created_playlist_is_private_and_has_no_author_brand(self):
        self.youtube.playlists.return_value.list.return_value.execute.return_value = {'items': []}
        self.youtube.playlists.return_value.insert.return_value.execute.return_value = {'id': 'p'}
        self.assertEqual(ensure_playlist(self.youtube, 'My series', default_language='en'), 'p')
        body = self.youtube.playlists.return_value.insert.call_args.kwargs['body']
        self.assertEqual(body['status']['privacyStatus'], 'private')
        self.assertEqual(body['snippet']['description'], 'Videos in the My series series.')
        self.assertEqual(body['snippet']['defaultLanguage'], 'en')


if __name__ == '__main__':
    unittest.main()
