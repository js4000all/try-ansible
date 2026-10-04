FROM ubuntu

RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y \
        ansible-core \
        curl \
        iputils-ping

USER ubuntu
RUN ansible-galaxy collection install ansible.posix

WORKDIR /work
