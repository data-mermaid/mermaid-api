backlog            = 2048
chdir              = "/var/projects/webapp"
bind               = "unix:/var/run/webapp/gunicorn.sock"
pidfile            = "/var/run/webapp/gunicorn.pid"
daemon             = False
debug              = False
workers            = 1
accesslog          = "/var/log/webapp/gunicorn-webapp-access.log"
errorlog           = "/var/log/webapp/gunicorn-webapp-error.log"
loglevel           = "error"
proc_name          = "webapp"
user               = "webapp"
umask              = 0000
limit_request_line = 0  # unlimited
timeout            = 300  # seconds