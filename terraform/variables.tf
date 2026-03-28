variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "Default GCP region."
  type        = string
  default     = "us-central1"
}

variable "bucket_name" {
  description = "GCS bucket for raw and staged data."
  type        = string
}

variable "dataset_id" {
  description = "BigQuery dataset for the news warehouse."
  type        = string
  default     = "news_pipeline"
}

variable "service_account_id" {
  description = "Service account name for Airflow and data jobs."
  type        = string
  default     = "airkube-data-platform"
}
