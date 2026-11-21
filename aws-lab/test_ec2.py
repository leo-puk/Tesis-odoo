"""Provisioning recovery checks with a fake AWS API and temporary local state."""
import argparse
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import ec2


class ProvisionTests(unittest.TestCase):
    def test_unauthorized_error_includes_session_token_and_recovery_command(self):
        denied = ec2.subprocess.CompletedProcess([], 255, "", "UnauthorizedOperation: ec2:DescribeSubnets")
        with patch("ec2.subprocess.run", return_value=denied):
            with self.assertRaisesRegex(RuntimeError, "session token") as context:
                ec2.aws("us-east-1", "ec2", "describe-subnets")
        self.assertIn("ec2:DescribeSubnets", str(context.exception))
        self.assertIn("use-lab-credentials.sh", str(context.exception))

    def test_retry_after_response_loss_reuses_ec2_token_and_group(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = argparse.Namespace(region="us-east-1", ami="ami-test", subnet="subnet-test",
                security_group="sg-test", key_pair="lab", ssh_cidr="203.0.113.1/32",
                instance_type="m5.xlarge", disk_gib=100, profile=None, apply=True,
                state=Path(temporary) / "instance.json")
            requests = []

            def fake_aws(region, service, command, *arguments):
                if command == "describe-subnets":
                    return {"Subnets": [{"VpcId": "vpc-test"}]}
                if command == "describe-images":
                    return {"Images": [{"ImageId": "ami-test", "Architecture": "x86_64", "RootDeviceName": "/dev/sda1"}]}
                if command == "run-instances":
                    request = json.loads((args.state.parent / "launch-request.json").read_text())
                    requests.append(request)
                    if len(requests) == 1:
                        raise RuntimeError("response lost after API accepted request")
                    return {"Instances": [{"InstanceId": "i-test"}]}
                return {}

            with patch("ec2.aws", side_effect=fake_aws), redirect_stdout(io.StringIO()):
                with self.assertRaises(RuntimeError):
                    ec2.launch(args)
                ec2.launch(args)
                ec2.launch(args)
                self.assertEqual(len(requests), 2)
                self.assertEqual(requests[0], requests[1])
                self.assertTrue(requests[0]["MetadataOptions"]["HttpTokens"] == "required")
                args.disk_gib = 50
                with self.assertRaises(ValueError):
                    ec2.launch(args)


if __name__ == "__main__":
    unittest.main()
