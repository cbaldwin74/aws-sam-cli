import os
from unittest import TestCase
from unittest.mock import patch

from parameterized import parameterized

from samcli.lib.providers.provider import LayerVersion, BuildableStack
from samcli.lib.providers.sam_layer_provider import SamLayerProvider

STACK_PATH = os.path.join("this_is_a", "stack_path")


class TestSamLayerProvider(TestCase):
    TEMPLATE = {
        "Resources": {
            "ServerlessLayer": {
                "Type": "AWS::Serverless::LayerVersion",
                "Properties": {
                    "LayerName": "Layer1",
                    "ContentUri": "PyLayer/",
                    "CompatibleRuntimes": ["python3.8", "python3.6"],
                },
                "Metadata": {"BuildMethod": "python3.8"},
            },
            "LambdaLayer": {
                "Type": "AWS::Lambda::LayerVersion",
                "Properties": {
                    "LayerName": "Layer1",
                    "Content": "PyLayer/",
                    "CompatibleRuntimes": ["python3.8", "python3.6"],
                },
                "Metadata": {"BuildMethod": "python3.8"},
            },
            "ServerlessLayerNoBuild": {
                "Type": "AWS::Serverless::LayerVersion",
                "Properties": {
                    "LayerName": "Layer1",
                    "ContentUri": "PyLayer/",
                    "CompatibleRuntimes": ["python3.8", "python3.6"],
                },
            },
            "LambdaLayerNoBuild": {
                "Type": "AWS::Lambda::LayerVersion",
                "Properties": {
                    "LayerName": "Layer1",
                    "Content": "PyLayer/",
                    "CompatibleRuntimes": ["python3.8", "python3.6"],
                },
            },
            "ServerlessLayerS3Content": {
                "Type": "AWS::Serverless::LayerVersion",
                "Properties": {
                    "LayerName": "Layer1",
                    "ContentUri": "s3://dummy-bucket/my-layer.zip",
                    "CompatibleRuntimes": ["python3.8", "python3.6"],
                },
            },
            "LambdaLayerS3Content": {
                "Type": "AWS::Lambda::LayerVersion",
                "Properties": {
                    "LayerName": "Layer1",
                    "Content": {"S3Bucket": "dummy-bucket", "S3Key": "layer.zip"},
                    "CompatibleRuntimes": ["python3.8", "python3.6"],
                },
            },
            "SamFunc": {
                "Type": "AWS::Serverless::Function",
                "Properties": {
                    # CodeUri is unsupported S3 location
                    "CodeUri": "s3://bucket/key",
                    "Runtime": "nodejs4.3",
                    "Handler": "index.handler",
                },
            },
        }
    }

    def setUp(self):
        self.parameter_overrides = {}
        self.stack = BuildableStack("this_is_a", "stack_path", "template.yaml", self.parameter_overrides, self.TEMPLATE)
        with patch("samcli.lib.providers.sam_stack_provider.get_template_data") as get_template_data_mock:
            get_template_data_mock.return_value = self.TEMPLATE
            self.provider = SamLayerProvider([self.stack])

    @parameterized.expand(
        [
            (
                "ServerlessLayer",
                LayerVersion(
                    "ServerlessLayer",
                    "PyLayer/",
                    ["python3.8", "python3.6"],
                    {"BuildMethod": "python3.8"},
                    stack_path=STACK_PATH,
                ),
            ),
            (
                "LambdaLayer",
                LayerVersion(
                    "LambdaLayer",
                    "PyLayer/",
                    ["python3.8", "python3.6"],
                    {"BuildMethod": "python3.8"},
                    stack_path=STACK_PATH,
                ),
            ),
            (
                "ServerlessLayerNoBuild",
                LayerVersion(
                    "ServerlessLayerNoBuild", "PyLayer/", ["python3.8", "python3.6"], None, stack_path=STACK_PATH
                ),
            ),
            (
                "LambdaLayerNoBuild",
                LayerVersion("LambdaLayerNoBuild", "PyLayer/", ["python3.8", "python3.6"], None, stack_path=STACK_PATH),
            ),
            (
                "ServerlessLayerS3Content",
                LayerVersion("ServerlessLayerS3Content", ".", ["python3.8", "python3.6"], None, stack_path=STACK_PATH),
            ),
            (
                "LambdaLayerS3Content",
                LayerVersion("LambdaLayerS3Content", ".", ["python3.8", "python3.6"], None, stack_path=STACK_PATH),
            ),
        ]
    )
    def test_get_must_return_each_layer(self, name, expected_output):
        actual = self.provider.get(name)
        self.assertEqual(actual, expected_output)

    def test_get_all_must_return_all_layers(self):
        result = [f.arn for f in self.provider.get_all()]
        expected = [
            "ServerlessLayer",
            "LambdaLayer",
            "ServerlessLayerNoBuild",
            "LambdaLayerNoBuild",
            "ServerlessLayerS3Content",
            "LambdaLayerS3Content",
        ]

        self.assertEqual(result, expected)

    def test_provider_ignores_non_layer_resource(self):
        self.assertIsNone(self.provider.get("SamFunc"))

    def test_fails_with_empty_name(self):
        with self.assertRaises(ValueError):
            self.provider.get("")
