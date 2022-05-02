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

| Parameter              | Description                                                             |
|------------------------|-------------------------------------------------------------------------|
| DBSnapshotIdentifier   | The masked snapshot that will be used to provision the new RDS instance |
| DBInstanceClass        | Instance class for the new RDS instance.                                |
| DBInstanceIdentifier   | RDS instance identifier.                                                |
| OptionGroupName        | RDS instance Option Group.                                              |
| DBParameterGroupName   | RDS instance Parameter Group.                                           | 
| DBSubnetGroupName      | RDS instance Subnet Group.                                              | 
| AvailabilityZone       | RDS Availability Zone.                                                  |
| VPCSecurityGroups      | RDS Security Group.                                                     |

## Notes

- The **AWS Service Catalog RDS Provisioning template** should be used as a provisioning method of a **DATAMASQUE** masked snapshot.
- **The template parameters will vary each RDS database instance and should be used as a blueprint.**