import unittest
import os
import json
import subprocess
from unittest.mock import MagicMock, patch
from src.infrastructure.terraform_manager import TerraformManager

class TestTerraformManagerDryRun(unittest.TestCase):
    """
    Integration tests for TerraformManager that mock the actual subprocess calls
    to avoid real infrastructure changes, but verify the logic flow.
    """

    def setUp(self):
        self.manager = TerraformManager(terraform_dir="terraform")
        # Mock the subprocess.run to avoid actual execution
        self.patcher = patch('subprocess.run')
        self.mock_run = self.patcher.start()
        
        # Mock file operations for tfvars
        self.file_patcher = patch('builtins.open', new_callable=MagicMock, read_data='{}')
        # Configure the mock to behave like a file handle
        self.mock_file = self.file_patcher.start()
        self.mock_file.return_value.__enter__.return_value.read.return_value = '{}'
        
        # Mock os.path.exists to always return True for tfvars
        self.exists_patcher = patch('os.path.exists')
        self.mock_exists = self.exists_patcher.start()
        self.mock_exists.return_value = True

    def tearDown(self):
        self.patcher.stop()
        self.file_patcher.stop()
        self.exists_patcher.stop()

    def test_init(self):
        self.manager.init()
        self.mock_run.assert_called_with(
            ["terraform", "init"],
            cwd=self.manager.terraform_dir,
            check=True,
            capture_output=True,
            text=True
        )

    def test_plan_enable_backend(self):
        # Setup mock return for plan
        mock_result = MagicMock()
        mock_result.stdout = "Plan: 1 to add, 0 to change, 0 to destroy."
        self.mock_run.return_value = mock_result

        # Run plan for qdrant
        output = self.manager.plan(backend_type="qdrant")
        
        # Verify tfvars was updated
        # We expect read call then write call
        # The write call should have deploy_qdrant=True
        
        # Check that subprocess was called correctly
        self.mock_run.assert_called_with(
            ["terraform", "plan"],
            cwd=self.manager.terraform_dir,
            check=True,
            capture_output=True,
            text=True
        )
        
        self.assertIn("Plan: 1 to add", output)

    def test_apply_backend(self):
        mock_result = MagicMock()
        mock_result.stdout = "Apply complete!"
        self.mock_run.return_value = mock_result

        output = self.manager.apply("opensearch")
        
        self.mock_run.assert_called_with(
            ["terraform", "apply", "-auto-approve"],
            cwd=self.manager.terraform_dir,
            check=True,
            capture_output=True,
            text=True
        )
        self.assertEqual(output, "Apply complete!")

    def test_destroy_backend(self):
        mock_result = MagicMock()
        mock_result.stdout = "Destroy complete!"
        self.mock_run.return_value = mock_result

        output = self.manager.destroy("lancedb_s3")
        
        # Destroy in our manager actually runs apply with var=false
        self.mock_run.assert_called_with(
            ["terraform", "apply", "-auto-approve"],
            cwd=self.manager.terraform_dir,
            check=True,
            capture_output=True,
            text=True
        )
        self.assertEqual(output, "Destroy complete!")

    def test_get_status(self):
        # Mock output json
        mock_output = {
            "deployment_summary": {
                "value": {
                    "vector_stores_deployed": {
                        "s3vector": True,
                        "qdrant": False,
                        "opensearch": True
                    }
                }
            }
        }
        
        mock_result = MagicMock()
        mock_result.stdout = json.dumps(mock_output)
        self.mock_run.return_value = mock_result

        status = self.manager.get_status()
        
        self.assertTrue(status["s3vector"])
        self.assertFalse(status["qdrant"])
        self.assertTrue(status["opensearch"])
        
        self.mock_run.assert_called_with(
            ["terraform", "output", "-json"],
            cwd=self.manager.terraform_dir,
            check=True,
            capture_output=True,
            text=True
        )

    def test_get_outputs(self):
        mock_output = {
            "qdrant": {
                "value": {
                    "endpoint": "http://localhost:6333"
                }
            }
        }
        
        mock_result = MagicMock()
        mock_result.stdout = json.dumps(mock_output)
        self.mock_run.return_value = mock_result

        outputs = self.manager.get_outputs("qdrant")
        self.assertEqual(outputs["endpoint"], "http://localhost:6333")

if __name__ == '__main__':
    unittest.main()