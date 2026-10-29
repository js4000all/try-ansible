FROM ubuntu

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-venv \
        curl \
        iputils-ping \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/ansible

ENV PATH="/opt/ansible/bin:${PATH}"

RUN pip install --no-cache-dir \
        ansible-lint \
        yamllint

USER ubuntu

RUN ansible-galaxy collection install \
      ansible.posix \
      community.general

ENV PAGER=cat
WORKDIR /work
