FROM apache/superset:4.1.1
USER root
RUN pip install --no-cache-dir psycopg2-binary==2.9.9
COPY superset_config.py /app/pythonpath/superset_config.py
COPY init.sh /app/init.sh
RUN chmod +x /app/init.sh
USER superset
