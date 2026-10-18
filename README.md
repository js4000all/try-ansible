# Ansible demo

## prepare_known_hosts.py

Ansibleのinventoryを参照し、対象ホストのSSHホスト公開鍵を収集して `known_hosts` に登録するスクリプトです。

### 前提条件

- Python 3.10以降
- Ansible（`ansible-inventory` コマンド）
- OpenSSHクライアント（`ssh-keyscan`、`ssh-keygen` コマンド）
- 対象ホストにSSH接続可能であること

本リポジトリではコンテナ内で実行すればOK。

```bash
docker compose run --rm -v "${HOME}/.ssh:/mnt/ssh" ops ./prepare_known_hosts.py -i inventory/hosts.yml -f /mnt/ssh/known_hosts
```

このコマンドでは、ホスト側の`.ssh`ディレクトリをマウントし、その中の`known_hosts`ファイルを変更対象として指定しています。

`hosts.yml` には、各ホストについて次の変数を定義されていることが前提(`hosts.yml.example`参照)。

- `ansible_host`：現在の接続先IPアドレス
- `network_ipv4_address`：変更後の固定IPアドレス

### 処理内容

1. `ansible-inventory` からホストとIPアドレスを取得する。
2. 現在のIPアドレスに対して `ssh-keyscan` を実行し、SSHホスト公開鍵を収集する。
3. 未登録の公開鍵についてfingerprintを表示し、ユーザーに承認を求める。
4. 承認された公開鍵を、現在のIPアドレスと変更後のIPアドレスの両方に紐づけて `known_hosts` に登録する。

すでに登録されている公開鍵なら再承認を求めません。

既存のIPアドレスに異なる公開鍵が登録されている場合は、上書きせずエラーで終了します。

**すべての確認が完了するまで `known_hosts` は更新しません。**


## 初期セットアップ

Ansibleによるbootstrapを実行する前に、管理対象マシンを手作業でセットアップする。

対象マシンとOSは以下のとおり。

| OS | 権限昇格 |
|---|---|
| Debian | sudo |
| Alpine Linux | doas |

### 1. 共通の前提条件

OSのインストール後、以下の状態を確保する。

- LANに接続され、管理PCからIPアドレスで到達できる。
- デフォルトユーザが作成されている。
- デフォルトユーザにパスワード認証でSSH接続できる。
- デフォルトユーザがパスワードなしでroot権限に昇格できる。

デフォルトユーザをそのままAnsibleの接続ユーザとして使用する。Ansible専用ユーザは作成しない。

Python 3とSSH公開鍵の設定は、後続のbootstrapで実施する。

### 2. Debian

OSインストール時に、一般ユーザを作成し、SSHサーバを有効化する。

必要に応じて、root権限で以下を実行する。

**sudoの設定**

```sh
apt-get update
apt-get install -y sudo openssh-server
usermod -aG sudo <username>
```

`visudo` を実行し、sudoグループに対する設定を確認・変更する。

```sudoers
%sudo ALL=(ALL:ALL) NOPASSWD: ALL
```

既存のsudoグループ設定と競合しないようにする。

**SSHの設定**

```sh
systemctl enable --now ssh
```

パスワード認証が許可されていることを確認する。

設定を変更した場合は、SSHサービスを再起動する。

### 3. Alpine Linux

OSインストール時に `setup-alpine` を実行し、ネットワークとSSHサーバを設定する。

**doasの設定**

root権限で以下を実行する。

```sh
apk add doas openssh
addgroup <username> wheel
```

`/etc/doas.d/ansible.conf` を作成する。

```text
permit nopass :wheel
```

wheelグループのユーザがパスワードなしでroot権限に昇格できるようにする。

**SSHの設定**

```sh
rc-update add sshd default
rc-service sshd start
```

パスワード認証が許可されていることを確認する。

設定を変更した場合は、SSHサービスを再起動する。

### 4. 初期状態の確認

管理PCから、各マシンに対して以下を確認する。

**Debian**

```sh
ssh <username>@<ip-address>
sudo -n id -u
```

**Alpine**

```sh
ssh <username>@<ip-address>
doas -n id -u
```

いずれも、権限昇格後のコマンドがパスワード入力なしで `0` を返すことを確認する。

これらの条件を満たした時点で、Ansibleのbootstrapを実行できる。

### 5. bootstrapとの責務分担

手作業では、Ansibleが接続して権限昇格できる最低限の状態を確保する。

bootstrapでは以下を実施する。

- Python 3のインストール
- デフォルトユーザへのSSH公開鍵登録

IPアドレスの固定化、hostname、SSHのセキュリティ設定、Docker、Git、GWのルーティングなどは通常のplaybookで管理する。

bootstrapで確立した管理経路と権限は、通常のplaybookでも維持する。

## run_ansible.shについて

`run_ansible.sh`は以下を行っている。

- コンテナ上で`ansbible`または`ansible-playbook`を実行
- コンテナ内にssh鍵を引き継ぐために、ssh-agentを自動起動・停止
- インベントリ定義ファイル、ssh秘密鍵は`.env`で指定


## bootstrapする

`playbook/bootstrap.yml`を実行し、通常のplaybookを実行できる最低限の下地を整える。

limitを指定して、bootstrap用playbookが通るか確認。

```bash
./run_ansible.sh \
  playbooks/bootstrap.yml \
  --limit dev_pc \
  --ask-pass
```

成功したら、パスワードなしで動作することを確認。
```bash
./run_ansible.sh \
  playbooks/bootstrap.yml \
  --limit dev_pc
```

