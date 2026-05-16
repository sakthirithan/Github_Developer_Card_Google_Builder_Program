FROM nginx:alpine

# Use a custom entrypoint to inject the BACKEND_URL environment variable into index.html
COPY index.html /usr/share/nginx/html/index.html

# Simple entrypoint to replace the placeholder with the environment variable
CMD ["/bin/sh", "-c", "sed -i 's|__BACKEND_URL__|'\"$BACKEND_URL\"'|g' /usr/share/nginx/html/index.html && nginx -g 'daemon off;'"]
