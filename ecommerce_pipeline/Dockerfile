# Start from the official Apache Spark 3.5.1 image to match assignment packages
FROM apache/spark-py:v3.4.0

# Switch to root to install system packages and libraries
USER root

# Install Python dependencies required for the assignment
# psycopg2-binary: To connect to Postgres from Python scripts
# kafka-python: Standard library for Kafka producers
# pandas/numpy/etc: Standard data libraries
RUN pip install --no-cache-dir \
    pyyaml \
    numpy \
    pandas \
    matplotlib \
    scipy \
    simpy \
    psycopg2-binary \
    kafka-python

# Download PostgreSQL JDBC Driver so Spark can read from Postgres
# We place it in the jars directory so it's automatically on the classpath
RUN curl -o /opt/spark/jars/postgresql-42.7.3.jar https://jdbc.postgresql.org/download/postgresql-42.7.3.jar

COPY spark-defaults.conf /opt/spark/conf/

# Switch back to the default user
USER $SPARK_USER