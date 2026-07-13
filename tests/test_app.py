"""moto-mocked test asserting the Aurora handler's boto3 call shape.

ponytail: covers the call shape (correct API names/params) and the §6.2 fix,
not full Service Catalog semantics — moto's servicecatalog support is patched
here rather than relied on.
"""
import importlib
import sys
from pathlib import Path
from unittest import mock

import boto3
import pytest
import yaml
from moto import mock_aws

REPO_ROOT = Path(__file__).resolve().parents[1]
FUNC_DIR = REPO_ROOT / "functions" / "service_catalog_product_update"
sys.path.insert(0, str(FUNC_DIR))

REGION = "us-east-1"
# Use the real shipped template so a safe_load-incompatible template fails the suite.
SOURCE_TEMPLATE_FILE = REPO_ROOT / "RDSDBInstance.template"


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    monkeypatch.setenv("RDS_IDENTIFIER", "prod-cluster")
    monkeypatch.setenv("SOURCE_TEMPLATE_URL", SOURCE_TEMPLATE_FILE.as_uri())
    monkeypatch.setenv("PRODUCT_ID", "prod-123")
    monkeypatch.setenv("S3_BUCKET", "templates-bucket")
    monkeypatch.setenv("S3_BUCKET_REGIONAL_DOMAIN_NAME", "templates-bucket.s3.us-east-1.amazonaws.com")


@mock_aws
def test_handler_call_shape(env):
    boto3.client("s3", region_name=REGION).create_bucket(Bucket="templates-bucket")

    app = importlib.reload(importlib.import_module("app"))

    fake_rds = mock.Mock()
    paginator = mock.Mock()
    paginator.paginate.return_value = [
        {"DBClusterSnapshots": [{"DBClusterSnapshotIdentifier": "snap-1"}]},
        {"DBClusterSnapshots": [{"DBClusterSnapshotIdentifier": "snap-2"}]},
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

    # Aurora queries cluster snapshots by DBClusterIdentifier
    fake_rds.get_paginator.assert_called_once_with("describe_db_cluster_snapshots")
    paginator.paginate.assert_called_once_with(DBClusterIdentifier="prod-cluster")

    args = fake_sc.create_provisioning_artifact.call_args.kwargs
    url = args["Parameters"]["Info"]["LoadTemplateFromURL"]
    # §6.2: published object name matches the branch template file
    assert url.endswith("/RDSDBInstance.template")

    body = (
        real_resource("s3", region_name=REGION)
        .Object("templates-bucket", "RDSDBInstance.template")
        .get()["Body"]
        .read()
        .decode()
    )
    published = yaml.safe_load(body)
    assert published["Parameters"]["DBClusterSnapshotIdentifier"]["AllowedValues"] == ["snap-1", "snap-2"]

    fake_sc.delete_provisioning_artifact.assert_called_once_with(
        ProductId="prod-123", ProvisioningArtifactId="old-art"
    )
    assert result == {"response": "new-art"}


@mock_aws
def test_no_snapshots_raises_before_publishing(env):
    app = importlib.reload(importlib.import_module("app"))

    fake_rds = mock.Mock()
    paginator = mock.Mock()
    paginator.paginate.return_value = [{"DBClusterSnapshots": []}]
    fake_rds.get_paginator.return_value = paginator

    fake_sc = mock.Mock()

    def client_factory(name, *a, **k):
        return {"rds": fake_rds, "servicecatalog": fake_sc}[name]

    with mock.patch.object(app.boto3, "client", side_effect=client_factory):
        with pytest.raises(RuntimeError, match="No masked cluster snapshots"):
            app.lambda_handler({}, None)

    # No broken artifact should be published when there is nothing to list.
    fake_sc.create_provisioning_artifact.assert_not_called()
