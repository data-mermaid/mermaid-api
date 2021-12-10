FROM honeycrisp/docker:django-geo-api

ADD ./requirements.txt requirements.txt
RUN pip install --upgrade -r requirements.txt
RUN rm requirements.txt

WORKDIR /var/projects/webapp
ADD ./src .

ADD ./ci_cd/VERSION.txt .

ADD ./ci_cd/simpleq.supervisor .
RUN bash -c "cat <(echo) <(echo) simpleq.supervisor  >> /etc/supervisor/supervisord.conf"
RUN rm simpleq.supervisor

ADD ./ci_cd/update_summary_site.supervisor .
RUN bash -c "cat <(echo) <(echo) update_summary_site.supervisor  >> /etc/supervisor/supervisord.conf"
RUN rm update_summary_site.supervisor

EXPOSE 8000 80 443
CMD ["supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
