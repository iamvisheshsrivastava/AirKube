output "bucket_name" {
  value = google_storage_bucket.news_raw.name
}

output "dataset_id" {
  value = google_bigquery_dataset.news.dataset_id
}

output "service_account_email" {
  value = google_service_account.data_platform.email
}
