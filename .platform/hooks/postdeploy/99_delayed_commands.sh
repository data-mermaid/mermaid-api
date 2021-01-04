#!/usr/bin/env bash


c_id=`docker ps --no-trunc -q | head -n 1`
docker exec $c_id python /var/projects/webapp/manage.py dbbackup
docker exec $c_id python /var/projects/webapp/manage.py collectstatic --noinput
docker exec $c_id python /var/projects/webapp/manage.py migrate --noinput
docker exec $c_id supervisorctl restart all