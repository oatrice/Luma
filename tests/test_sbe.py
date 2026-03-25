"""
Tests for SBE (Specification by Example) Module
TDD: Red Phase - Failing Tests First
"""
import pytest
import os

# These imports will fail initially (Red phase)
# from luma_core.sbe import (
#     generate_sbe_from_issue,
#     parse_sbe_spec,
#     validate_sbe_spec,
#     SBESpec,
#     Scenario
# )


class TestSBEDataStructures:
    """Test SBE data structures"""
    
    def test_scenario_has_required_fields(self):
        """Scenario should have name, given, when, then, examples"""
        from luma_core.sbe import Scenario
        
        scenario = Scenario(
            name="Successful transfer",
            given="I have 1000 in Savings",
            when="I transfer 200 to Emergency",
            then="Savings should have 800",
            examples=[
                {"source": "Savings", "amount": 200, "expected": 800}
            ]
        )
        
        assert scenario.name == "Successful transfer"
        assert scenario.given is not None
        assert scenario.when is not None
        assert scenario.then is not None
        assert len(scenario.examples) >= 1

    def test_sbe_spec_has_feature_and_scenarios(self):
        """SBESpec should have feature name and list of scenarios"""
        from luma_core.sbe import SBESpec, Scenario
        
        spec = SBESpec(
            feature="Transfer Money Between Jars",
            description="Allow users to move money between jars",
            scenarios=[
                Scenario(
                    name="Happy path",
                    given="sufficient balance",
                    when="transfer",
                    then="success",
                    examples=[]
                )
            ]
        )
        
        assert spec.feature == "Transfer Money Between Jars"
        assert len(spec.scenarios) >= 1


class TestParseSBESpec:
    """Test parsing SBE markdown files"""
    
    def test_parse_valid_sbe_markdown(self, tmp_path):
        """Should parse valid SBE markdown into SBESpec object"""
        from luma_core.sbe import parse_sbe_spec
        
        sbe_content = """# SBE: Transfer Money

## Feature: Transfer Money Between Jars

Allow users to move money between their jars.

### Scenario: Successful transfer

**Given** I have 1000 in "Savings" jar
**When** I transfer 200 to "Emergency" jar
**Then** "Savings" should have 800 and "Emergency" should have 200

#### Examples

| source_balance | amount | expected_source | expected_dest |
|----------------|--------|-----------------|---------------|
| 1000           | 200    | 800             | 200           |
| 500            | 500    | 0               | 500           |
"""
        # Create temp file
        sbe_file = tmp_path / "sbe_transfer.md"
        sbe_file.write_text(sbe_content)
        
        spec = parse_sbe_spec(str(sbe_file))
        
        assert spec.feature == "Transfer Money Between Jars"
        assert len(spec.scenarios) >= 1
        assert spec.scenarios[0].name == "Successful transfer"
        assert len(spec.scenarios[0].examples) == 2

    def test_parse_nonexistent_file_raises_error(self):
        """Should raise FileNotFoundError for missing file"""
        from luma_core.sbe import parse_sbe_spec
        
        with pytest.raises(FileNotFoundError):
            parse_sbe_spec("/nonexistent/path/sbe.md")


class TestValidateSBESpec:
    """Test SBE validation"""
    
    def test_valid_spec_passes(self):
        """Valid spec should pass validation"""
        from luma_core.sbe import validate_sbe_spec, SBESpec, Scenario
        
        spec = SBESpec(
            feature="Test Feature",
            description="Test description",
            scenarios=[
                Scenario(
                    name="Test Scenario",
                    given="precondition",
                    when="action",
                    then="expected",
                    examples=[{"input": 1, "output": 2}]
                )
            ]
        )
        
        assert validate_sbe_spec(spec) is True

    def test_empty_feature_fails(self):
        """Spec with empty feature name should fail"""
        from luma_core.sbe import validate_sbe_spec, SBESpec
        
        spec = SBESpec(feature="", description="", scenarios=[])
        
        assert validate_sbe_spec(spec) is False

    def test_scenario_without_examples_fails(self):
        """Scenario without examples should fail validation"""
        from luma_core.sbe import validate_sbe_spec, SBESpec, Scenario
        
        spec = SBESpec(
            feature="Test",
            description="Test",
            scenarios=[
                Scenario(
                    name="No examples",
                    given="x",
                    when="y",
                    then="z",
                    examples=[]  # Empty examples
                )
            ]
        )
        
        assert validate_sbe_spec(spec) is False


class TestGenerateSBE:
    """Test SBE generation from issue data"""
    
    def test_generate_creates_file(self, tmp_path):
        """Should create SBE file in output directory"""
        from luma_core.sbe import generate_sbe_from_issue
        
        issue_data = {
            "title": "Add Transfer Feature",
            "number": 42,
            "body": "As a user, I want to transfer money between jars."
        }
        
        output_dir = str(tmp_path / "specs")
        result = generate_sbe_from_issue(issue_data, output_dir)
        
        assert os.path.exists(result)
        assert result.endswith(".md")

    def test_generate_contains_multiple_scenarios(self, tmp_path):
        """Generated SBE should contain multiple scenarios (happy + error)"""
        from luma_core.sbe import generate_sbe_from_issue, parse_sbe_spec
        
        issue_data = {
            "title": "Add Transfer Feature",
            "number": 42,
            "body": "As a user, I want to transfer money between jars."
        }
        
        output_dir = str(tmp_path / "specs")
        result_path = generate_sbe_from_issue(issue_data, output_dir)
        
        spec = parse_sbe_spec(result_path)
        
        # Should have at least 2 scenarios (happy path + edge case)
        assert len(spec.scenarios) >= 2
