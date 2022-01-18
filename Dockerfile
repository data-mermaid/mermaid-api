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

ADD ./ci_cd/update_summaries.supervisor .
RUN bash -c "cat <(echo) <(echo) update_summaries.supervisor  >> /etc/supervisor/supervisord.conf"
RUN rm update_summaries.supervisor

EXPOSE 8000 80 443
CMD ["supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
