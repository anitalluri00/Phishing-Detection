FROM nginxinc/nginx-unprivileged:1.27-alpine

ENV BACKEND_UPSTREAM=http://backend:5000

COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY src /usr/share/nginx/html

EXPOSE 8080
