# Terraform

This directory contains the infrastructure-as-code for the AirKube data platform.

## What it provisions
- A GCS bucket for raw and staged data
- A BigQuery dataset for the news warehouse
- A service account for Airflow and data jobs
- IAM bindings for BigQuery and storage access

## Local usage
1. Copy `terraform.tfvars.example` to `terraform.tfvars`.
2. Fill in your GCP project and bucket name.
3. Run:

```bash
terraform -chdir=terraform init
terraform -chdir=terraform fmt -recursive
terraform -chdir=terraform validate
terraform -chdir=terraform plan
```