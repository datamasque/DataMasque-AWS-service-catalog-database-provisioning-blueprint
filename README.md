# AWS Service Catalog Database Provisioning Blueprint (Aurora)

> **Reference blueprint — adapt to your environment.** This repository is a
> starting point, not a turnkey product. Review and harden IAM, networking,
> secrets, and TLS for your own environment before any production use.

[DataMasque](https://datamasque.com) replaces sensitive data with realistic,
synthetically identical customer data so teams can work with production-like data without exposing
PII. This blueprint provisions a **masked** Aurora cluster + instance through
**AWS Service Catalog**: it publishes a self-service product whose only
selectable snapshots are the masked DB cluster snapshots produced by the
[Aurora masking blueprint](https://github.com/datamasque/DataMasque-AWS-Aurora-masking-stepfunctions-blueprint).
End users launch the product to restore a fresh Aurora cluster from a masked
snapshot, so non-production environments never receive raw production data.

**Learn more:** [datamasque.com](https://datamasque.com) ·
[Product docs](https://datamasque.com/portal/documentation/) ·
[Book a demo](https://datamasque.com/request-a-demo)

---

A scheduled Lambda keeps the Service Catalog product's snapshot list current by
reading the available masked cluster snapshots and re-publishing the
provisioning template. This blueprint provisions databases from already-masked
snapshots; it does not itself call the DataMasque API.

![Reference deployment](reference_deployment.png "Reference deployment")

The diagram above shows the DataMasque reference architecture in AWS. This
blueprint covers the **self-service provisioning** steps highlighted in purple.

## RDS vs Aurora

This repository ships two branches:

- `main-aurora` — provisions an **Aurora cluster + instance** from a masked DB
  cluster snapshot (this branch).
- `main-rds` — provisions a standalone **RDS DB instance** from a masked DB
  snapshot. Check it out with `git checkout main-rds`.

For masking the source cluster snapshots first, see the
[AWS Aurora masking (Step Functions) blueprint](https://github.com/datamasque/DataMasque-AWS-Aurora-masking-stepfunctions-blueprint).

## Prerequisites

- AWS CLI configured with credentials for the target account.
- The [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html).
- Python 3.12 (Lambda runtime; only needed locally to run the tests).
- At least one **masked** Aurora DB cluster snapshot already produced by the
  Aurora masking blueprint.

## Deploy

This is an AWS SAM application. Build and deploy it with the SAM CLI:

```bash
sam build
sam deploy --guided
```

`sam deploy --guided` prompts for the stack name, region, and the deployer
parameters below, then writes a `samconfig.toml` you can reuse with
`sam deploy`.

### Deployer parameters (template.yaml)

| Parameter            | Description                                                                        | Default                               |
|----------------------|------------------------------------------------------------------------------------|---------------------------------------|
| `SourceTemplateURL`  | URL of the provisioning template the update Lambda fetches and re-publishes.        | _(required)_                          |
| `RDSIdentifier`      | Source Aurora cluster identifier whose masked snapshots feed the product.           | _(required)_                          |
| `TemplateBucketName` | Globally-unique name for the S3 bucket holding published templates.                 | `datamasque-servicecatalog-templates` |
| `PortfolioName`      | Service Catalog portfolio display name.                                             | `DatamasquePortfolio`                 |
| `ProductName`        | Service Catalog product name.                                                       | `DatamasqueRDSProvisioning`           |

> `TemplateBucketName` must be globally unique across all AWS accounts. Override
> the default to avoid collisions.

#### Example samconfig.toml

```toml
version = 0.1
[default.deploy.parameters]
stack_name = "service-catalog-automation"
s3_prefix = "service-catalog-automation"
region = "ap-southeast-2"
confirm_changeset = true
capabilities = "CAPABILITY_IAM"
parameter_overrides = "SourceTemplateURL=\"https://raw.githubusercontent.com/datamasque/DataMasque-AWS-service-catalog-database-provisioning-blueprint/main-aurora/RDSDBInstance.template\" RDSIdentifier=\"your-aurora-cluster-id\""
```

## End-user provisioning parameters

End users launching the Service Catalog product supply the parameters consumed
by `RDSDBInstance.template`:

| Parameter                   | Description                                                            |
|-----------------------------|------------------------------------------------------------------------|
| DBClusterSnapshotIdentifier | The masked snapshot used to provision the new Aurora cluster.          |
| DBInstanceClass             | Instance class for the new Aurora instance.                            |
| DBClusterEngine             | Aurora cluster engine.                                                 |
| DBClusterEngineVersion      | Aurora cluster engine version.                                         |
| DBClusterIdentifier         | Aurora cluster identifier.                                             |
| DBClusterSubnetGroupName    | Aurora cluster subnet group.                                           |
| VPCSecurityGroups           | Aurora security group(s).                                              |
| KmsKeyId                    | Optional KMS key to re-encrypt the restored cluster. Leave blank to inherit the snapshot's encryption — a snapshot of an unencrypted source stays unencrypted, so set a key if you need encryption-at-rest guaranteed. |

## After deploying

Once the stack is created, grant end users access so they can self-serve:

1. [Create an IAM group for end users to launch products](https://docs.aws.amazon.com/servicecatalog/latest/adminguide/getstarted-iamenduser.html).
2. [Grant end users access to the portfolio](https://docs.aws.amazon.com/servicecatalog/latest/adminguide/getstarted-deploy.html).
3. [Verify the end-user experience](https://docs.aws.amazon.com/servicecatalog/latest/adminguide/getstarted-verify.html).

Reference: <https://docs.aws.amazon.com/servicecatalog/latest/adminguide/getstarted.html>

## Notes

- Use this product as the provisioning method for a **DataMasque** masked
  snapshot.
- The provisioning parameters **need to reflect your setup** and **preferred
  configuration** within your AWS environment.
- The update Lambda has a (disabled) scheduled trigger; enable it in
  `template.yaml` to refresh the snapshot list automatically.

### Template note

CloudFormation short-form intrinsic functions (`!Ref`, `!Join`) are not used in
`RDSDBInstance.template` because the PyYAML loader that rewrites it does not
understand them. Use the long form instead, e.g.:

```yaml
DBInstanceIdentifier:
  Fn::Join:
    - '-'
    - - Ref: DBClusterIdentifier
      - 'dtq'
```

---

## Related DataMasque blueprints

- [AWS RDS masking (Step Functions)](https://github.com/datamasque/DataMasque-AWS-RDS-masking-stepfunctions-blueprint)
- [Azure DB masking (Logic Apps)](https://github.com/datamasque/DataMasque-Azure-DB-masking-logicapps-blueprint)
- [AWS Cross-Account Bucket Access](https://github.com/datamasque/DataMasque-AWS-Cross-Account-Bucket-Access)
- [AWS ECS Deployment](https://github.com/datamasque/DataMasque-AWS-ECS-Deployment)
- [masque-bricks (Databricks)](https://github.com/datamasque/masque-bricks)
