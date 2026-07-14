"""moto-mocked test asserting the handler's boto3 call shape.

Covers the call shape (correct API names/params), not full Service Catalog
semantics — moto's servicecatalog support is patched here rather than relied on.
"""
import importlib
import os
import sys
from pathlib import Path
from unittest import mock

import boto3
import pytest
import yaml
from moto import mock_aws

FUNC_DIR = Path(__file__).resolve().parents[1] / "functions" / "service_catalog_product_update"
sys.path.insert(0, str(FUNC_DIR))

REGION = "us-east-1"
SOURCE_TEMPLATE = {
    "Parameters": {"DBSnapshotIdentifier": {"Type": "String", "AllowedValues": []}}
}


@pytest.fixture
def env(monkeypatch, tmp_path):
    template_file = tmp_path / "source.yaml"
    template_file.write_text(yaml.dump(SOURCE_TEMPLATE))
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    monkeypatch.setenv("RDS_IDENTIFIER", "prod-db")
    monkeypatch.setenv("SOURCE_TEMPLATE_URL", template_file.as_uri())
    monkeypatch.setenv("PRODUCT_ID", "prod-123")
    monkeypatch.setenv("S3_BUCKET", "templates-bucket")
    monkeypatch.setenv("S3_BUCKET_REGIONAL_DOMAIN_NAME", "templates-bucket.s3.us-east-1.amazonaws.com")


@mock_aws
def test_handler_call_shape(env):
    boto3.client("s3", region_name=REGION).create_bucket(Bucket="templates-bucket")

    app = importlib.reload(importlib.import_module("app"))

    # Stub RDS pagination: assert the handler queries by DBInstanceIdentifier
    # and threads the snapshot ids into AllowedValues.
    fake_rds = mock.Mock()
    paginator = mock.Mock()
    paginator.paginate.return_value = [
        {"DBSnapshots": [{"DBSnapshotIdentifier": "snap-1"}]},
        {"DBSnapshots": [{"DBSnapshotIdentifier": "snap-2"}]},
    ]
    fake_rds.get_paginator.return_value = paginator

    fake_sc = mock.Mock()
    fake_sc.create_provisioning_artifact.return_value = {
        "ProvisioningArtifactDetail": {"Id": "new-art"}
    }
    fake_sc.describe_product_as_admin.return_value = {
        "ProvisioningArtifactSummaries": [{"Id": "new-art"}, {"Id": "old-art"}]
    }

    real_resource = boto3.resource

    def client_factory(name, *a, **k):
        return {"rds": fake_rds, "servicecatalog": fake_sc}[name]

    with mock.patch.object(app.boto3, "client", side_effect=client_factory), \
         mock.patch.object(app.boto3, "resource", side_effect=real_resource):
        result = app.lambda_handler({}, None)

    # queried by DBInstanceIdentifier
    paginator.paginate.assert_called_once_with(DBInstanceIdentifier="prod-db")

    # AllowedValues populated from both pages
    args = fake_sc.create_provisioning_artifact.call_args.kwargs
    url = args["Parameters"]["Info"]["LoadTemplateFromURL"]
    # published object name matches the RDS-branch template file
    assert url.endswith("/RDSDBInstance.template")

    # object written to S3 under the same key, with both snapshot ids
    body = (
        real_resource("s3", region_name=REGION)
        .Object("templates-bucket", "RDSDBInstance.template")
        .get()["Body"]
        .read()
        .decode()
    )
    published = yaml.safe_load(body)
    assert published["Parameters"]["DBSnapshotIdentifier"]["AllowedValues"] == ["snap-1", "snap-2"]

    # stale artifact pruned, latest kept
    fake_sc.delete_provisioning_artifact.assert_called_once_with(
        ProductId="prod-123", ProvisioningArtifactId="old-art"
    )
    assert result == {"response": "new-art"}


@mock_aws
def test_no_snapshots_raises_and_publishes_nothing(env):
    boto3.client("s3", region_name=REGION).create_bucket(Bucket="templates-bucket")

    app = importlib.reload(importlib.import_module("app"))

    fake_rds = mock.Mock()
    paginator = mock.Mock()
    paginator.paginate.return_value = [{"DBSnapshots": []}]
    fake_rds.get_paginator.return_value = paginator

    fake_sc = mock.Mock()

    def client_factory(name, *a, **k):
        return {"rds": fake_rds, "servicecatalog": fake_sc}[name]

    with mock.patch.object(app.boto3, "client", side_effect=client_factory):
        with pytest.raises(RuntimeError, match="No DB snapshots found"):
            app.lambda_handler({}, None)

    # existing artifact untouched
    fake_sc.create_provisioning_artifact.assert_not_called()
    fake_sc.delete_provisioning_artifact.assert_not_called()
