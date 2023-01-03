# nano-bench

*nano-bench* is a nanocurrency benchmark tool to evaluate how well your hardware is suited for running a nano_node.
It automates:
- the generation of a nano-local network
- loading a ledger with 200k unconfirmed blocks
- measuring max cps while cementing the blocks

Network testing (e.g. bandwidth & latency impact) is out of scope of this benchmark.

# running nano-bench

Run the test: 
```
git clone https://github.com/gr0vity-dev/nano-bench.git
cd nano-bench
./bench.sh 
```

For Fedora/CentOS, you may also need the following to resolve dependency & permission issues:
```
dnf upgrade --refresh

# Install Git, Python dependencies
dnf install git python3-devel gcc 

# Install docker dependencies via the Docker.com repo
dnf -y install dnf-plugins-core
dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
dnf install docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Make the docker-compose command available
echo 'docker compose "$' > /bin/docker-compose && echo '@"' > /bin/docker-compose && sed -i 's/^/docker compose "$/' /bin/docker-compose && chmod +x /bin/docker-compose

# Start docker
systemctl start docker

# Add the selinux label (:z) to mount volumes in nanolocal/services/default_docker-compose.yml
# Details here: https://docs.docker.com/storage/bind-mounts/
vim nanolocal/services/default_docker-compose.yml
  - ./${default_docker}:/./home/nanocurrency:z
  - ./${default_docker}:/home/nanocurrency:z
  - ./${default_docker}:/root:z
```

On its first run `./bench.sh` will 
- update and init the git the submodules (nano-local)
- unzip the blocks and ledgers required to run the benchmark
- install a python virtual environment

The benchmark does the following: 
- Creating a network of 2 nodes: 
	- 1 genesis node 
	- 1 representative that holds 100% of the weight.

The network is used as follows:
- disable voting for both nodes
- load a ledger that holds 200k checked but uncemented blocks.
- stop the gensis node, so we only have 1 representative left
- re-enable voting for the representative 
- measure cps

*TODO: evaluate results / Create leaderboard*
On Ryzen9 with Kingston Renegade Disk it peaks at 13k cps

```
Ryzen9 + Kingston Renegade Disk:
         test_name         start_date         node_version  confirmed_blocks cps_p50_to_p90      cps_p100
0  BENCHMARK 1node  22-12-31 12:13:40  Nano V24.0 19935b8b            200000       13318.10   9088.448332


Ryzen9 + SSD (samsung evo 970):
         test_name         start_date         node_version  confirmed_blocks cps_p50_to_p90      cps_p100
0  BENCHMARK 1node  22-12-31 15:42:33  Nano V24.0 98227de6            200000        7156.10  4760.441235


gr0vity nano PR:
         test_name         start_date         node_version  confirmed_blocks cps_p50_to_p90      cps_p100
0  BENCHMARK 1node  22-12-31 15:49:51  Nano V24.0 98227de6            200000       13149.10  5880.375557

i5-11400 + Samsung 970 Evo Plus (NVME M2):
         test_name         start_date         node_version  confirmed_blocks cps_p50_to_p90     cps_p100
0  BENCHMARK 1node  23-01-02 20:28:34  Nano V24.0 98227de6            200000       13697.10  7405.379606
1  BENCHMARK 1node  23-01-02 20:38:37  Nano V24.0 98227de6            200000       13159.10  6894.992575
2  BENCHMARK 1node  23-01-02 20:39:52  Nano V24.0 98227de6            200000       13323.10  6450.162374
3  BENCHMARK 1node  23-01-02 20:40:53  Nano V24.0 98227de6            200000       13236.10  6663.152588
```
