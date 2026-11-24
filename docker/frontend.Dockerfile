FROM nginx:alpine

COPY app/frontend/index.html /usr/share/nginx/html
COPY app/frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80