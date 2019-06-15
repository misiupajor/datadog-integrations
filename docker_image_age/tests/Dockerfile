FROM alpine:3.1

RUN apk add --update nginx && mkdir /tmp/nginx && rm -rf /var/cache/apk/*

LABEL "com.datadoghq.ad.check_names"='["docker_image_age"]'
LABEL "com.datadoghq.ad.init_configs"='[{}]'
LABEL "com.datadoghq.ad.instances"='[{"pid": "%%pid%%", "age": "0", "debug": "True"}]'

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
