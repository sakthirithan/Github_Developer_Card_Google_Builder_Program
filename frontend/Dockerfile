FROM nginx:alpine

# Install envsubst (part of gettext)
RUN apk add --no-cache gettext

# Copy the frontend file
COPY index.html /usr/share/nginx/html/index.html.template

# Default backend URL (can be overridden at runtime)
ENV BACKEND_URL=http://localhost:8080

# Create a custom entrypoint to inject the environment variable
RUN echo '#!/bin/sh' > /entrypoint.sh && \
    echo 'envsubst "\$BACKEND_URL" < /usr/share/nginx/html/index.html.template > /usr/share/nginx/html/index.html' >> /entrypoint.sh && \
    echo 'exec nginx -g "daemon off;"' >> /entrypoint.sh && \
    chmod +x /entrypoint.sh

# Update index.html to use the variable
# This matches the "http://localhost:8080" string in the original file
RUN sed -i 's|http://localhost:8080|${BACKEND_URL}|g' /usr/share/nginx/html/index.html.template

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
