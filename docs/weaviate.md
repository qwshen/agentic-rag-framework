# https://js.langchain.com/docs/integrations/vectorstores/weaviate/
# https://docs.weaviate.io/deploy/installation-guides/embedded
#
# docker pull semitechnologies/weaviate:latest
# docker run -d -p 8080:8080 -p 50051:50051 cr.weaviate.io/semitechnologies/weaviate:latest


# install milvus docker version
curl -sfL https://raw.githubusercontent.com/milvus-io/milvus/master/scripts/standalone_embed.sh -o standalone_embed.sh
bash standalone_embed.sh start

