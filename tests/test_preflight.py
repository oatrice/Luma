import pytest
import os
import json
from unittest.mock import patch, MagicMock
from luma_core.preflight_checker import PreflightChecker, PreflightCheckResult, CheckType

# Temporary stubs until implementation exists
# These will be moved to luma_core/preflight_checker.py later
# but for TDD "Red" phase, we'll try to import them and expect failure
# or define tests expecting the class to exist.

class TestPreflightChecker:
    
    @pytest.fixture
    def mock_project(self, tmp_path):
        """Create a mock project structure"""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        
        # Create some files
        (project_dir / "CHANGELOG.md").write_text("# Changelog")
        (project_dir / "package.json").write_text('{"version": "1.0.0"}')
        
        # Create rules file
        rules = {
            "project": "Test",
            "preflight_checks": [
                {
                    "id": "check_changelog",
                    "name": "Check Changelog",
                    "type": "file_modified",
                    "path": "CHANGELOG.md",
                    "required": True,
                    "message": "Update changelog"
                },
                {
                    "id": "check_readme",
                    "name": "Check Readme",
                    "type": "file_exists",
                    "path": "README.md",
                    "required": True,
                    "message": "Readme missing"
                }
            ]
        }
        rules_file = project_dir / ".luma_rules.json"
        rules_file.write_text(json.dumps(rules))
        
        return project_dir

    def test_init_loads_rules(self, mock_project):
        """Test that checker loads rules from JSON file"""
        checker = PreflightChecker(str(mock_project))
        assert len(checker.rules) == 2
        assert checker.rules[0]["id"] == "check_changelog"

    def test_check_file_exists_pass(self, mock_project):
        """Test file_exists check passes when file exists"""
        (mock_project / "README.md").write_text("# Readme")
        checker = PreflightChecker(str(mock_project))
        
        # Find the specific rule to test
        rule = next(r for r in checker.rules if r["type"] == "file_exists")
        result = checker.run_single_check(rule)
        
        assert result.passed == True
        assert result.check_id == "check_readme"

    def test_check_file_exists_fail(self, mock_project):
        """Test file_exists check fails when file missing"""
        # Ensure README.md does NOT exist
        checker = PreflightChecker(str(mock_project))
        
        rule = next(r for r in checker.rules if r["type"] == "file_exists")
        result = checker.run_single_check(rule)
        
        assert result.passed == False
        assert "Readme missing" in result.message

    @patch("subprocess.run")
    def test_check_command_pass(self, mock_run, mock_project):
        """Test command check passes on exit code 0"""
        mock_run.return_value = MagicMock(returncode=0)
        
        checker = PreflightChecker(str(mock_project))
        rule = {
            "id": "test_cmd",
            "name": "Test Command",
            "type": "command",
            "command": "echo test",
            "required": True,
            "message": "Command failed"
        }
        
        result = checker.run_single_check(rule)
        assert result.passed == True

    @patch("subprocess.run")
    def test_check_command_fail(self, mock_run, mock_project):
        """Test command check fails on non-zero exit code"""
        mock_run.return_value = MagicMock(returncode=1)
        
        checker = PreflightChecker(str(mock_project))
        rule = {
            "id": "test_cmd",
            "name": "Test Command",
            "type": "command",
            "command": "false",
            "required": True,
            "message": "Command failed"
        }
        
        result = checker.run_single_check(rule)
        assert result.passed == False

    def test_run_all_checks(self, mock_project):
        """Test running all checks returns list of results"""
        (mock_project / "README.md").write_text("# Readme")
        # For file_modified, we might need to mock git or some fallback
        # For now let's assume it fails if we haven't mocked git
        
        checker = PreflightChecker(str(mock_project))
        
        # Mocking check_file_modified to always pass for this test
        # to focus on the aggregation logic
        with patch.object(checker, 'check_file_modified', return_value=True):
            results = checker.run_checks()
            
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_check_file_modified_git(self, mock_project):
        """Test file_modified uses git diff"""
        checker = PreflightChecker(str(mock_project))
        rule = {"type": "file_modified", "path": "CHANGELOG.md", "id": "test", "name": "test", "required":True, "message":""}
        
        with patch("subprocess.run") as mock_run:
            # Mock git diff returning changes
            mock_run.return_value = MagicMock(returncode=0, stdout="diff content")
            result = checker.run_single_check(rule)
            assert result.passed == True
            
            # Mock git diff returning no changes
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            result = checker.run_single_check(rule)
            assert result.passed == False

    def test_check_version_updated(self, mock_project):
        """Test version update check"""
        checker = PreflightChecker(str(mock_project))
        rule = {"type": "version_updated", "path": "package.json", "id": "v", "name": "v", "required":True, "message":""}
        
        with patch("subprocess.run") as mock_run:
            # Mock git diff showing version change
            mock_run.return_value = MagicMock(returncode=0, stdout='+ "version": "1.0.1"\n- "version": "1.0.0"')
            result = checker.run_single_check(rule)
            assert result.passed == True
            
            # Mock git diff showing other changes but no version
            mock_run.return_value = MagicMock(returncode=0, stdout='+ "name": "New Name"')
            result = checker.run_single_check(rule)
            assert result.passed == False

    def test_check_version_updated_false_positives(self, mock_project):
        """Test strictness of version update check (avoid false positives)"""
        checker = PreflightChecker(str(mock_project))
        rule = {"type": "version_updated", "path": "package.json", "id": "v", "name": "v", "required":True, "message":""}
        
        with patch("subprocess.run") as mock_run:
            # Case 1: Comment containing 'version'
            mock_run.return_value = MagicMock(returncode=0, stdout='+ // TODO: bump version later')
            result = checker.run_single_check(rule)
            assert result.passed == False, "Do not match comments"

            # Case 2: Other text containing 'version' substring
            mock_run.return_value = MagicMock(returncode=0, stdout='+ "conversion_rate": 1.0')
            result = checker.run_single_check(rule)
            assert result.passed == False, "Do not match partial words like conversion"
