bind = "0.0.0.0:8000"
workers = 2
worker_class = "gthread"
threads = 4
timeout = 45
graceful_timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
limit_request_line = 4094
limit_request_fields = 50
limit_request_field_size = 8190
accesslog = "-"
errorlog = "-"
# Deliberately exclude query strings and request bodies from access logs.
access_log_format = '%(h)s %(m)s %(U)s %(s)s %(L)s'
