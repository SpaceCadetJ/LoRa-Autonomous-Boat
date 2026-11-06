"""Mutation checks for exact historical Power viewer replay boundaries."""
import copy
import json
import unittest
import replay_power_viewer as replay


class PowerViewerReplayTests(unittest.TestCase):
    def setUp(self):
        self.files = {}
        self.archives = {}
        self.inputs = {}
        for index, (target, snapshot) in enumerate(replay.ARCHIVE_PATHS.items()):
            data = ('original shared input ' + str(index) + '\n').encode()
            self.files[snapshot] = data
            self.inputs[target] = replay.digest(data)
            self.archives[target] = {'snapshot': snapshot, 'sha256': replay.digest(data),
                                     'git_blob': replay.git_blob_id(data),
                                     'source_commit': '9' * 40, 'source_path': target}
        self.other = replay.PACKET + '/build_view.py'
        self.files[self.other] = b'original comparison viewer\n'
        self.inputs[self.other] = replay.digest(self.files[self.other])
        self.record = {'input_sha256': self.inputs}

    def load(self, name):
        return self.files[name]

    def test_exact_archives_and_other_inputs(self):
        saved = replay.validate_archives(self.archives, self.record, self.load)
        self.assertEqual(set(saved), set(replay.ARCHIVE_PATHS))
        replay.check_hashes({self.other: self.inputs[self.other]}, self.load)

    def test_wrong_archived_builder_hash(self):
        self.files[replay.ARCHIVE_PATHS['pm/tools/build.mjs']] += b'changed'
        with self.assertRaisesRegex(ValueError, 'Archived SHA-256'):
            replay.validate_archives(self.archives, self.record, self.load)

    def test_missing_builder_archive(self):
        del self.files[replay.ARCHIVE_PATHS['pm/tools/build.mjs']]
        with self.assertRaises(KeyError):
            replay.validate_archives(self.archives, self.record, self.load)

    def test_other_viewer_input_cannot_be_masked(self):
        self.files[self.other] += b'changed'
        with self.assertRaisesRegex(ValueError, 'Viewer input mismatch'):
            replay.validate_archives(self.archives, self.record, self.load)

    def test_template_snapshot_target_cannot_be_redirected(self):
        self.archives['pm/index.template.html']['snapshot'] = self.other
        with self.assertRaisesRegex(ValueError, 'snapshot target'):
            replay.validate_archives(self.archives, self.record, self.load)

    def test_wrong_git_blob(self):
        self.archives['pm/tools/build.mjs']['git_blob'] = '0' * 40
        with self.assertRaisesRegex(ValueError, 'Git blob'):
            replay.validate_archives(self.archives, self.record, self.load)

    def test_changed_viewer_hash_rejected_even_if_archive_consistent(self):
        self.inputs['pm/tools/build.mjs'] = replay.digest(b'different captured bytes')
        with self.assertRaisesRegex(ValueError, 'differs from viewer capture'):
            replay.validate_archives(self.archives, self.record, self.load)

    def test_extra_archive_target_rejected(self):
        self.archives[self.other] = copy.deepcopy(self.archives['pm/tools/build.mjs'])
        with self.assertRaisesRegex(ValueError, 'Only the two'):
            replay.validate_archives(self.archives, self.record, self.load)

    def test_artifact_coverage_must_be_exact(self):
        entries = {'one': 'digest', 'two': 'digest'}
        replay.check_coverage(entries, ['one', 'two'])
        for actual in [['one'], ['one', 'two', 'extra']]:
            with self.subTest(actual=actual), self.assertRaisesRegex(ValueError, 'artifact coverage'):
                replay.check_coverage(entries, actual)

    def test_anchored_manifest_rejects_changed_bytes(self):
        original = json.dumps({'artifact_sha256': {'a': 'original'}}).encode()
        self.assertEqual(replay.anchored_manifest(original, replay.digest(original)), json.loads(original))
        with self.assertRaisesRegex(ValueError, 'manifest anchor'):
            replay.anchored_manifest(original + b' ', replay.digest(original))


if __name__ == '__main__':
    unittest.main()
