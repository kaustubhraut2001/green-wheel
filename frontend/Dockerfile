# ── Serve pre-built Vite output with Nginx ────────────────────────────────────
# We do NOT run npm install inside Docker.
# The frontend is built locally first (npm run build → dist/)
# then the dist/ folder is copied directly into the nginx image.
# This avoids all npm network issues inside Docker completely.

FROM nginx:alpine

RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the pre-built Vite output (built on host before docker compose up)
COPY dist/ /usr/share/nginx/html/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
