"""Local assistant checks without real AWS credentials or resource creation."""
import argparse
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import iniciar


class AssistantTests(unittest.TestCase):
    def test_env_accepts_lab_ini_and_preserves_quoted_secrets(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ):
            path = Path(temporary) / ".env"
            path.write_text('[default]\naws_access_key_id=example-id\naws_secret_access_key="example # secret"\n'
                            'aws_session_token=example-token\n', encoding="utf-8")
            values = iniciar.load_environment(path)
            self.assertEqual(values["AWS_SECRET_ACCESS_KEY"], "example # secret")
            self.assertEqual(os.environ["AWS_ACCESS_KEY_ID"], "example-id")
            path.write_text("AWS_ACCESS_KEY_ID=only-id\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "AWS_SESSION_TOKEN"):
                iniciar.load_environment(path)

    def test_subnet_uses_explicit_route_table_over_main(self):
        subnet = dict(SubnetId="subnet-test", VpcId="vpc-test", State="available")
        main = dict(Associations=[dict(Main=True)], Routes=[dict(DestinationCidrBlock="0.0.0.0/0",
                    State="active", GatewayId="igw-test")])
        private = dict(Associations=[dict(SubnetId="subnet-test")], Routes=[])
        with patch("iniciar.ec2.aws", side_effect=[{"Subnets": [subnet]}, {"RouteTables": [main, private]}]):
            with self.assertRaises(ValueError):
                iniciar.public_subnet("us-east-1", None)

    def test_plan_never_creates_keys_instances_or_uploads_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            options = argparse.Namespace(state_dir=Path(temporary), env=Path(temporary) / ".env", plan=True)
            with patch("iniciar.shutil.which", return_value="available"), patch(
                "iniciar.ec2.check_identity", return_value={"Account": "account"}), patch(
                "iniciar.public_subnet", return_value="subnet"), patch(
                "iniciar.ssh_cidr", return_value="203.0.113.1/32"), patch(
                "iniciar.ensure_key") as key, patch("iniciar.ec2.launch") as launch, patch(
                "iniciar.sync.deploy") as deploy, redirect_stdout(io.StringIO()):
                iniciar.provision({}, options)
            key.assert_not_called()
            launch.assert_not_called()
            deploy.assert_not_called()

    def test_generated_key_reuses_existing_pair_on_retry(self):
        with tempfile.TemporaryDirectory() as temporary:
            key = Path(temporary) / "tesis-key"
            key.write_text("local test private key")
            key.with_suffix(".pub").write_text("ssh-ed25519 public-test")
            with patch("iniciar.ec2.aws", return_value={"KeyPairs": [{"KeyName": "test"}]}) as aws:
                iniciar.ensure_key("us-east-1", "test", key, True)
            self.assertEqual(aws.call_count, 1)
            self.assertEqual(aws.call_args.args[2], "describe-key-pairs")

    def test_full_orchestration_resumes_same_state_without_network_rediscovery(self):
        with tempfile.TemporaryDirectory() as temporary:
            options = argparse.Namespace(state_dir=Path(temporary), env=Path(temporary) / ".env", plan=False, timeout=1)

            def launch(args):
                iniciar.ec2.save(args.state, {"instance_id": "i-test"})

            with patch("iniciar.shutil.which", return_value="available"), patch(
                "iniciar.ec2.check_identity", return_value={"Account": "account"}), patch(
                "iniciar.public_subnet", return_value="subnet-test") as subnet, patch(
                "iniciar.ssh_cidr", return_value="203.0.113.1/32"), patch(
                "iniciar.ensure_key"), patch("iniciar.ec2.launch", side_effect=launch), patch(
                "iniciar.wait_for_instance", return_value="203.0.113.2"), patch(
                "iniciar.sync.deploy") as deploy, redirect_stdout(io.StringIO()):
                iniciar.provision({"AWS_SECRET_ACCESS_KEY": "test-secret"}, options)
                first = json.loads((Path(temporary) / "asistente.json").read_text())
                iniciar.provision({"AWS_SECRET_ACCESS_KEY": "test-secret"}, options)
            self.assertEqual(subnet.call_count, 1)
            self.assertEqual(deploy.call_count, 2)
            self.assertNotIn("test-secret", (Path(temporary) / "asistente.json").read_text())
            self.assertEqual(first["key_pair"], json.loads((Path(temporary) / "asistente.json").read_text())["key_pair"])


if __name__ == "__main__":
    unittest.main()
