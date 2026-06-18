import os
import json
import tempfile
import shutil
import unittest
from unittest.mock import patch
from luma_core.git_utils import ensure_artifact_gitignore

class TestGitUtils(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.gitignore_path = os.path.join(self.test_dir, ".gitignore")
        self.luma_dev_path = os.path.join(self.test_dir, ".luma_dev.json")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch("luma_core.config.AUTO_UPDATE_GITIGNORE", True)
    def test_gitignore_created_if_not_exists(self):
        ensure_artifact_gitignore(self.test_dir)
        self.assertTrue(os.path.exists(self.gitignore_path))
        with open(self.gitignore_path, "r") as f:
            content = f.read()
        self.assertIn("# AI Agent Artifacts", content)
        self.assertIn(".agents/", content)
        self.assertIn("docs/features/", content)

    @patch("luma_core.config.AUTO_UPDATE_GITIGNORE", True)
    def test_gitignore_appended_if_missing(self):
        with open(self.gitignore_path, "w") as f:
            f.write("node_modules/\n.env\n")
        
        ensure_artifact_gitignore(self.test_dir)
        
        with open(self.gitignore_path, "r") as f:
            content = f.read()
        
        self.assertIn("node_modules/", content)
        self.assertIn(".env", content)
        self.assertIn("# AI Agent Artifacts", content)
        self.assertIn(".agents/", content)
        self.assertIn("docs/features/", content)

    @patch("luma_core.config.AUTO_UPDATE_GITIGNORE", True)
    def test_gitignore_skipped_if_present(self):
        original_content = "node_modules/\n# AI Agent Artifacts\n.agents/\ndocs/features/\n"
        with open(self.gitignore_path, "w") as f:
            f.write(original_content)
        
        ensure_artifact_gitignore(self.test_dir)
        
        with open(self.gitignore_path, "r") as f:
            content = f.read()
        
        self.assertEqual(content, original_content)

    @patch("luma_core.config.AUTO_UPDATE_GITIGNORE", False)
    def test_gitignore_honors_global_false(self):
        ensure_artifact_gitignore(self.test_dir)
        self.assertFalse(os.path.exists(self.gitignore_path))

    @patch("luma_core.config.AUTO_UPDATE_GITIGNORE", True)
    def test_gitignore_honors_local_dev_json(self):
        with open(self.luma_dev_path, "w") as f:
            json.dump({"AUTO_UPDATE_GITIGNORE": False}, f)
        
        ensure_artifact_gitignore(self.test_dir)
        self.assertFalse(os.path.exists(self.gitignore_path))

if __name__ == '__main__':
    unittest.main()
