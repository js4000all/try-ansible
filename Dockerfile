FROM ubuntu

RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y \
        ansible-core \
        curl \
        iputils-ping

RUN ansible-galaxy collection install ansible.posix

USER ubuntu
WORKDIR /work
