"""In-memory rejection tests for archived versus current viewer evidence."""
import unittest
import check_viewer_replay as replay


class ViewerReplayTests(unittest.TestCase):
    def setUp(self):
        self.old = b'<html>captured template</html>\n'
        self.files = {'archive.html': self.old, 'packet/model.py': b'preserved model\n'}
        self.record = {'input_sha256': {replay.PM_TEMPLATE: replay.digest(self.old),
                                      'packet/model.py': replay.digest(self.files['packet/model.py'])}}
        self.entry = {'template_snapshot': 'archive.html', 'template_sha256': replay.digest(self.old),
                      'template_git_blob': replay.git_blob_id(self.old)}

    def load(self, name):
        if name not in self.files:
            raise FileNotFoundError(name)
        return self.files[name]

    def test_exact_historical_and_current_inputs(self):
        self.assertEqual(replay.validate_archive(self.entry, self.record, self.load), self.old)
        replay.validate_viewer(self.record, self.old, self.load, live_template=self.old)

    def test_wrong_snapshot(self):
        self.files['archive.html'] += b'modified'
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            replay.validate_archive(self.entry, self.record, self.load)

    def test_wrong_git_blob(self):
        self.entry['template_git_blob'] = '0' * 40
        with self.assertRaisesRegex(ValueError, 'Git blob'):
            replay.validate_archive(self.entry, self.record, self.load)

    def test_missing_archive(self):
        del self.files['archive.html']
        with self.assertRaises(FileNotFoundError):
            replay.validate_archive(self.entry, self.record, self.load)

    def test_archive_does_not_mask_another_viewer_input(self):
        self.files['packet/model.py'] += b'changed'
        with self.assertRaisesRegex(ValueError, 'Viewer input mismatch'):
            replay.validate_archive(self.entry, self.record, self.load)

    def test_mismatched_immutable_packet_input(self):
        expected = {'packet/model.py': replay.digest(self.files['packet/model.py'])}
        self.files['packet/model.py'] = b'new model'
        with self.assertRaisesRegex(ValueError, 'Hash mismatch'):
            replay.validate_hashes(expected, self.load)

    def test_current_live_change_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Current PM template'):
            replay.validate_viewer(self.record, self.old, self.load, live_template=b'<html>new</html>')

    def test_snapshot_must_match_record_even_if_archive_hashes_agree(self):
        self.record['input_sha256'][replay.PM_TEMPLATE] = replay.digest(b'other captured template')
        with self.assertRaisesRegex(ValueError, 'differs from viewer record'):
            replay.validate_archive(self.entry, self.record, self.load)


if __name__ == '__main__':
    unittest.main()
