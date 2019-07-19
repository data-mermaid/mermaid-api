FROM honeycrisp/docker:django2

ADD ./requirements.txt requirements.txt
RUN pip install --upgrade -r requirements.txt
RUN rm requirements.txt

WORKDIR /var/projects/webapp
ADD ./src .

EXPOSE 8000 80 443
CMD ["supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
