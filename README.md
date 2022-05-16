# AWS Aurora Service Catalog Provisioning Template

## Introduction

DataMasque AWS blueprint template is written in AWS CloudFormation format. The purpose of this template is to create a reusable data provisioning pipeline that calls DataMasque APIs to produce masked data that's safe for consumption in non-production environment.

The diagram below describes the DataMasque reference architecture in AWS.  This CloudFormation template is used to set up AWS Service Catalog Products to give end-users access to provision RDS Aurora instances from a [masked RDS Aurora snapshot](https://github.com/datamasque/DataMasque-AWS-Aurora-masking-stepfunctions-blueprint) - this incorporates the **self-service** steps highlighted in purple.  

![Reference deployment](reference_deployment.png "Reference deployment")

For masking and provisioning RDS, please use the following templates:
- Automate masking RDS snapshots: [DataMasque AWS RDS Masking Step Functions CloudFormation Template](https://github.com/datamasque/DataMasque-AWS-RDS-masking-stepfunctions-blueprint).
- Provision RDS instances: use the **main-rds** branch from [AWS Service Catalog Provisioning template](https://github.com/datamasque/DataMasque-AWS-service-catalog-database-provisioning-blueprint).

The solution expects a few parameters as listed below:

| Parameter         | Description                                                                            |
|-------------------|----------------------------------------------------------------------------------------|
| SourceTemplateURL | The URL used as a source for the template used on for the AWS Service Catalog Product. |
| RDSIdentifier     | RDS cluster identifier used to retrieve the snapshot list.                             |
| PortfolioName     | AWS Service Catalog portfolio name.                                                    |  
| ProductName       | AWS Service Catalog product name.                                                      |

### Prerequisites

- AWS CLI configured with appropriate credential for the target AWS account.
- AWS SAM
  CLI: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html
- Python runtime 3.9 installed.

# How to use

The SAM template deploys the AWS Catalog Product and a Lambda function used the update the list if snapshots available to be used as source to the new Aurora Cluster.

The template expects arguments that can be passed using a configuration file:

samconfig.toml

```toml
version = 0.1
[default]
[default.deploy]
[default.deploy.parameters]
stack_name = "service-catalog-automation"
s3_bucket = "aws-sam-cli-managed-default-samclisourcebucket-xxxx"
s3_prefix = "service-catalog-automation"
region = "ap-southeast-2"
confirm_changeset = true
capabilities = "CAPABILITY_IAM"
disable_rollback = true
parameter_overrides = "SourceTemplateURL=\"https:file:////github.com/datamasque/DataMasque-AWS-service-catalog-database-provisioning-blueprint/blob/dev/RDSDBInstance.template\" RDSIdentifier=\"dtq-postgresql-blueprint-testing-xxxx\""
image_repositories = []
```

## AWS Service Catalog RDS Provisioning template

AWS Service catalog gives access to the users to deploy AWS resources without having to have access to underline resources.


## Parameters

| Parameter                   | Description                                                            |
|-----------------------------|------------------------------------------------------------------------|
| DBClusterSnapshotIdentifier | The masked snapshot that will be used to provision the new RDS cluster |
| DBInstanceClass             | Instance class for the new RDS instance.                               |
| DBClusterEngine             | RDS Cluster Engine.                                                    |
| DBClusterEngineVersion      | RDS Cluster Engine Version.                                            |
| DBClusterIdentifier         | RDS Cluster identifier.                                                |
| DBClusterSubnetGroupName    | RDS Cluster Subnet Group.                                              |
| VPCSecurityGroups           | RDS Security Group.                                                    |

## Notes

- The **AWS Service Catalog RDS Provisioning template** should be used as a provisioning method of a **DataMasque** masked snapshot.
- **The parameters** to the created AWS Service Catalog products **need reflect your setup** and **preferred configurations** within your AWS Environment.
- **The Lambda has a event trigger that can be used to invoke the Lambda:**
```yaml
Events:
        Schedule:
          Type: Schedule # More info about Schedule Event Source: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-property-statemachine-schedule.html
          Properties:
            Description: Schedule to run the Service Catalog automation daily.
            Enabled: False
            Schedule: "rate(1 day)"
            Input: '{}'
```

## Template Limitation.

**To use this template with an RDS instance instead of Aurora clusters, you need to change the API call to retrieve the snapshots.**
```python
response = rds.describe_db_cluster_snapshots(
    DBClusterIdentifier=rds_identifier
  )
```

**Due to a limitation on the python library used to update the CloudFormation template, the short form of calling functions is not supported.**

**This is not supported:**
```yaml
Name:
  - Domain: !Ref RootDomainName
```

**This is:**

```yaml
- Domain:
    Ref: RootDomainName
```