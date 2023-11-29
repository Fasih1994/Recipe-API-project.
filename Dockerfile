FROM python:3.9-alpine3.13
LABEL maintainer="Fasih"

ENV PYTHONUNBUFFERED=1

COPY ./requirements.txt /tmp/requirements.txt
COPY ./requirements.dev.txt /tmp/requirements.dev.txt
COPY ./scripts /scripts
EXPOSE 8000

ARG DEV=false

RUN apk add --update --no-cache postgresql-client jpeg-dev
RUN apk add --update --no-cache --virtual .tmp-build-deps \
    build-base postgresql-dev musl-dev zlib zlib-dev linux-headers

RUN python -m venv /py && \
    /py/bin/pip install --upgrade pip && \
    /py/bin/pip install -r /tmp/requirements.txt

# Install development requirements only if DEV is true
RUN if [ "$DEV" = "true" ]; then /py/bin/pip install -r /tmp/requirements.dev.txt; fi

# Remove temporary files
RUN rm -rf /tmp
RUN apk del .tmp-build-deps

# Create a non-root user
RUN adduser --disabled-password --no-create-home django-user

# Create directories for static and media files & set permissions
RUN mkdir -p /vol/web/media
RUN mkdir -p /vol/web/static
RUN chown -R django-user:django-user /vol
RUN chmod -R 755 /vol && chmod -R +x /scripts

ENV PATH="/scripts:/py/bin:$PATH"

COPY ./app /app
WORKDIR /app

USER django-user

CMD ["run.sh"]