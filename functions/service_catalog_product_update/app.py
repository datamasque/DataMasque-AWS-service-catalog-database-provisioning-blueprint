import os
import boto3
import urllib.request
import yaml
import json

rds_identifier = os.environ['RDS_IDENTIFIER']
source_template_url  = os.environ['SOURCE_TEMPLATE_URL']
product_id = os.environ['PRODUCT_ID']
s3_bucket = os.environ['S3_BUCKET']
s3_bucket_regional_domain_name = os.environ['S3_BUCKET_REGIONAL_DOMAIN_NAME']

def lambda_handler(event, context):

  rds = boto3.client('rds')

  response = rds.describe_db_cluster_snapshots(
    DBClusterIdentifier=rds_identifier
  )

  snapshots = response['DBClusterSnapshots']

  snapshot_ids = [d['DBClusterSnapshotIdentifier'] for d in snapshots]

  with urllib.request.urlopen(source_template_url) as f:
    template = yaml.safe_load(f)

  template['Parameters']['DBClusterSnapshotIdentifier']['AllowedValues'] = snapshot_ids

  print(yaml.dump(template))

  print(response)

  print(snapshot_ids)

  template_string = yaml.dump(template)
  encoded_template_string = template_string.encode("utf-8")


  file_name = "RDSDBCluster.template"
  s3_path = "" + file_name

  s3 = boto3.resource("s3")
  s3.Bucket(s3_bucket).put_object(Key=s3_path, Body=template_string)

  servicecatalog = boto3.client('servicecatalog')


  response = servicecatalog.create_provisioning_artifact(
    ProductId=product_id,
    Parameters={
      'Name': 'default',
      'Info': {
        'LoadTemplateFromURL': 'https://' + s3_bucket_regional_domain_name + '/' + s3_path
      },
      'Type': 'CLOUD_FORMATION_TEMPLATE',
      'DisableTemplateValidation': True
    }
  )

  latest_artifact_id = response['ProvisioningArtifactDetail']['Id']

  response = servicecatalog.describe_product_as_admin(Id=product_id)

  print(response)

  artifact_list = response['ProvisioningArtifactSummaries']

  artifact_ids = [d['Id'] for d in artifact_list]

  artifact_ids.remove(latest_artifact_id)

  for a in artifact_ids:
    r = servicecatalog.delete_provisioning_artifact(
      ProductId=product_id,
      ProvisioningArtifactId=a
    )
    print(r)

  return {'response': latest_artifact_id}