FROM python:3.9-alpine3.13
LABEL mantainer="federico.lunardon"

#Faster response
ENV PYTHONUNBUFFERED 1

COPY ./requirements.txt /tmp/requirements.txt
COPY ./requirements.dev.txt /tmp/requirements.dev.txt 
COPY ./app /app
WORKDIR /app
EXPOSE 8000

#false, then we will not be in dev mode forever
ARG DEV=false
RUN python -m venv /py && \
    # &&\ can run multiple commands
    /py/bin/pip install --upgrade pip && \ 
    /py/bin/pip install -r /tmp/requirements.txt && \
    #shell-scripting
    if [ $DEV = "true" ]; \
        then /py/bin/pip install -r /tmp/requirements.dev.txt ;\
        fi && \
    rm -rf /tmp && \
    adduser \
        --disabled-password \
        --no-create-home \
        django-user

ENV PATH="/scripts:/py/bin:$PATH"

USER django-user