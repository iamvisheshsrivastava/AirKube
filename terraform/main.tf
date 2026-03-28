provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_storage_bucket" "news_raw" {
  name                        = var.bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_bigquery_dataset" "news" {
  dataset_id                 = var.dataset_id
  friendly_name              = "AirKube News Warehouse"
  description                = "Raw and transformed news tables for analytics and downstream ML use."
  location                   = var.region
  delete_contents_on_destroy  = false
  default_table_expiration_ms = 0
}

resource "google_service_account" "data_platform" {
  account_id   = var.service_account_id
  display_name = "AirKube Data Platform Service Account"
}

resource "google_project_iam_member" "bigquery_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.data_platform.email}"
}

resource "google_project_iam_member" "bigquery_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.data_platform.email}"
}

resource "google_project_iam_member" "storage_object_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.data_platform.email}"
}
