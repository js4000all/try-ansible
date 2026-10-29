FROM ubuntu

RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y \
        ansible-core \
        curl \
        iputils-ping \
        pipx \
    && rm -rf /var/lib/apt/lists/*

USER ubuntu

ENV PATH="/home/ubuntu/.local/bin:${PATH}"

RUN pipx install ansible-lint \
    && pipx install yamllint

RUN ansible-galaxy collection install \
      ansible.posix \
      community.general

WORKDIR /work
