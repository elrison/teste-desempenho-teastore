#!/bin/sh
# setenv.sh - override JAVA_OPTS to inject a correct JDBC URL for persistence app
# This file is mounted into /usr/local/tomcat/bin/setenv.sh before Tomcat starts.

# Full JDBC URL for local testing (disable SSL to avoid SSL negotiation warnings)
JDBC_OVERRIDE="jdbc:mysql://teastore-db:3306/teadb?useSSL=false"

# Add several possible system properties that different apps may read
JAVA_OPTS="${JAVA_OPTS} -Djavax.persistence.jdbc.url=${JDBC_OVERRIDE} -Djdbc.url=${JDBC_OVERRIDE} -Ddatabase.url=${JDBC_OVERRIDE}"
export JAVA_OPTS

echo "setenv.sh applied: JAVA_OPTS=${JAVA_OPTS}"
