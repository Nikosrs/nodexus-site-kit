FROM alpine:3.21 AS assets
COPY site/ /out/
COPY build/fingerprint.sh /fingerprint.sh
RUN sh /fingerprint.sh /out

FROM nginx:1.27.5-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY build/security.inc /etc/nginx/security.inc
COPY --from=assets /out/ /usr/share/nginx/html/
RUN nginx -t
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
