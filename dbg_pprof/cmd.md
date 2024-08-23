```shell
# for benchmark
cargo build --release
# for debug
cargo clean
cargo build -F pprof
# start and output both to console and file
rm -r db/
samply record --save-only /home/discord9/greptimedb/target/release/greptime standalone start -c config.toml &> db.log

curl '0:4000/v1/prof/cpu?seconds=5&output=flamegraph'
```

# Current Working Method
```shell
# for benchmark
cargo build --release

# prepare for benchmark
sudo sysctl kernel.perf_event_paranoid=-1
sudo sysctl kernel.kptr_restrict=0

rm -r db/
samply record --save-only /home/discord9/greptimedb/target/release/greptime standalone start -c config.toml &> db.log

# or open profile automatically
rm -r db/
samply record /home/discord9/greptimedb/target/release/greptime standalone start -c config.toml &> db.log

python3 auto_flow_bench.py

samply load profile.json
```

# TODO

下述提到的 flow 任务是简单的 count(*)：
# 无 flow 任务
537508
# 1 个 flow 任务
507165.29
flow worker cpu 1~2%

# 10 个 flow 任务
505227.61
flow worker cpu 5~10%

# 100 个 flow 任务
495133.80
flow worker cpu 30~70% 大部分时间在 30%

# 500 个 flow 任务
339652.63
单核有点处理不过来了：
100% CPU

大概估计单核能满速跑 300-400个 flow 任务，接下来测测复杂一些的任务。