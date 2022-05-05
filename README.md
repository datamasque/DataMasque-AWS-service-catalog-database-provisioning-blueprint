# AWS Service Catalog RDS Provisioning template

## Introduction

AWS Service catalog gives access to the users to deploy AWS resources without having to have access to underline resources.

## How to use.

- Step 1: Download the AWS CloudFormation Template
- Step 3: Create an AWS Service Catalog Portfolio
- Step 4: Create an AWS Service Catalog Product
- Step 5: Assign the Product to the Portfolio
- Step 6: Grant End Users Access to the Portfolio
- Step 7: Test the End User Experience

Reference: https://docs.aws.amazon.com/servicecatalog/latest/adminguide/getstarted.html

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

- The **AWS Service Catalog Aurora Provisioning template** should be used as a provisioning method of a **DATAMASQUE** masked cluster snapshot.
- **The template parameters will vary each RDS database cluster and should be used as a blueprint.**