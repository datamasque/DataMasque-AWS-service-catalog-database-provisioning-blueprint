import os
import urllib.request
from datetime import datetime, timezone

import boto3
import yaml

rds_identifier = os.environ["RDS_IDENTIFIER"]
source_template_url = os.environ["SOURCE_TEMPLATE_URL"]
product_id = os.environ["PRODUCT_ID"]
s3_bucket = os.environ["S3_BUCKET"]
s3_bucket_regional_domain_name = os.environ["S3_BUCKET_REGIONAL_DOMAIN_NAME"]

# Output template object key. Must match the file the SourceTemplateURL points at
# (RDSDBInstance.template) so the published artifact stays in sync.
TEMPLATE_FILE_NAME = "RDSDBInstance.template"


def _describe_all_cluster_snapshots(rds):
    """Page through every masked Aurora cluster snapshot for the source identifier."""
    snapshot_ids = []
    paginator = rds.get_paginator("describe_db_cluster_snapshots")
    for page in paginator.paginate(DBClusterIdentifier=rds_identifier):
        snapshot_ids.extend(
            d["DBClusterSnapshotIdentifier"] for d in page["DBClusterSnapshots"]
        )
    return snapshot_ids


def lambda_handler(event, context):
    rds = boto3.client("rds")

    snapshot_ids = _describe_all_cluster_snapshots(rds)
    if not snapshot_ids:
        # An empty AllowedValues would publish a product no one can launch.
        # Fail loudly here instead of shipping a broken provisioning artifact.
        raise RuntimeError(
            f"No masked cluster snapshots found for {rds_identifier!r}; "
            "nothing to publish."
        )

    with urllib.request.urlopen(source_template_url) as f:
        template = yaml.safe_load(f)

    template["Parameters"]["DBClusterSnapshotIdentifier"]["AllowedValues"] = snapshot_ids

    template_string = yaml.dump(template)

    s3 = boto3.resource("s3")
    s3.Bucket(s3_bucket).put_object(Key=TEMPLATE_FILE_NAME, Body=template_string)

    servicecatalog = boto3.client("servicecatalog")

    # Create the new artifact before deleting the old ones: AWS refuses to
    # delete the last provisioning artifact of a product, so destroy-first
    # would fail on a product with a single (i.e. the current) artifact.
    response = servicecatalog.create_provisioning_artifact(
        ProductId=product_id,
        Parameters={
            # AWS allows duplicate artifact names (Id is the unique key), but
            # name-based lookups (e.g. ProvisionProduct by ProvisioningArtifactName)
            # fail on ambiguity, so timestamp the name to keep re-runs unambiguous.
            "Name": datetime.now(timezone.utc).strftime("snapshots-%Y%m%d-%H%M%S"),
            "Info": {
                "LoadTemplateFromURL": "https://"
                + s3_bucket_regional_domain_name
                + "/"
                + TEMPLATE_FILE_NAME
            },
            "Type": "CLOUD_FORMATION_TEMPLATE",
            # Deliberate: validation makes Service Catalog fetch the template
            # URL, which fails because the bucket blocks all public access.
            # The source template is cfn-lint-validated in CI and this handler
            # only injects AllowedValues, so skipping validation is safe.
            "DisableTemplateValidation": True,
        },
    )

    latest_artifact_id = response["ProvisioningArtifactDetail"]["Id"]

    response = servicecatalog.describe_product_as_admin(Id=product_id)

    artifact_ids = [d["Id"] for d in response["ProvisioningArtifactSummaries"]]
    artifact_ids.remove(latest_artifact_id)

    for a in artifact_ids:
        servicecatalog.delete_provisioning_artifact(
            ProductId=product_id, ProvisioningArtifactId=a
        )

    return {"response": latest_artifact_id}
