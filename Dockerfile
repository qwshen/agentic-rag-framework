ARG UBUNTU_VERSION="22.04"
FROM ubuntu:${UBUNTU_VERSION} AS build

ENV API_VERSION="1.0.0"
ENV RES_DIRECTORY="/agentic-rag-${API_VERSION}"
ARG API_DIRECTORY="/opt/agentic-rag-${API_VERSION}"
ARG TMP_DIRECTORY="/tmp/a-rag-api-${API_VERSION}"
RUN mkdir -p $API_DIRECTORY && mkdir -p $RES_DIRECTORY/prompts \
    && mkdir -p $TMP_DIRECTORY/qwshen 

WORKDIR $TMP_DIRECTORY
COPY ./requirements.txt .
RUN apt-get update && apt-get install -y python3 python3-pip zip \
    && pip3 install setuptools wheel \
    && pip3 install -r requirements.txt \
    && rm -f requirements.txt

COPY ./src/qwshen ./qwshen
COPY ./src/api.py ./__main__.py
RUN zip -r ${API_DIRECTORY}/rag-api-${API_VERSION}.zip . \
    && rm -rf $TMP_DIRECTORY

WORKDIR $RES_DIRECTORY
COPY ./resources/definition.json ./resources/application.env .
COPY ./resources/prompts ./prompts
COPY ./resources/certs ./certs

WORKDIR $API_DIRECTORY
ENTRYPOINT ["sh", "-c", "python3 rag-api-${API_VERSION}.zip --def ${RES_DIRECTORY}/definition.json --env ${RES_DIRECTORY}/application.env"]
