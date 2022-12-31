# nano-bench

*nano-bench* is a nanocurrency benchmark tool to evaluate how well your hardware is suited for running a nano_node .
It  automates :
- the generation of nano-local network
- loading a ledger with 200k unconfimred blocks.
- measuring max cps while cementing the blocks

Network is out of scope of this benchmark.

# running nano-bench


Run the test : 
``` ./bench.sh ```

On its first run this will :
- update and init the git the submodules (nano-local)
- unzip the blocks and ledgers required to run the benchmark
- install a python virtuel environment

The benchmark does the following : 
- Creating a network of 2 nodes : 
	- 1 genesis node 
	- 1 representative that holds 100% of the weight.

The network is used as follows :
- disable voting for both nodes
- load a ledger that holds 200k checked but uncemented blocks.
- stop the gensis node, so we only have 1 representative left
- re-enable voting for the representative 
- measure cps

*TODO: evaluate results / Create leaderboard*
On Ryzen9 with Kingston Renegade DIsk it peaks at 13k cps

```
         test_name         start_date         node_version  confirmed_blocks cps_p50_to_p90      cps_p100
0  BENCHMARK 1node  22-12-31 12:13:40  Nano V24.0 19935b8b            200000       13318.10   9088.448332
1  BENCHMARK 1node  22-12-31 12:20:25  Nano V24.0 98227de6            200000       13160.10   8692.851005
2  BENCHMARK 1node  22-12-31 13:24:26  Nano V24.0 98227de6            200000       13263.10   9088.164067
```