standalone 基础写入速度是 `529158.32 rows/sec`， flow(执行一个 flow 任务) 是 `498610 rows/sec` 
分布式基础写入速度是 `506380.45 rows/sec`， flow(执行一个 flow 任务) 是 `410452.36 rows/sec`

测试命令：
先带 `-F pprof` 编译 db:

```shell
cargo build --release -F pprof
```

rm -r db/
/home/discord9/greptimedb/target/debug/greptime standalone start -c config.toml > db.log
启动 db:
```shell
rm -r db/
/home/discord9/greptimedb/target/release/greptime standalone start -c config.toml > db.log &

```

分布式启动:
```shell
ETCDCTL_API=3 etcdctl del --prefix __;# remove etcd content
rm -r /tmp/greptimedb;# remove data
/home/discord9/greptimedb/target/release/greptime metasrv start -c config/metasrv.example.toml > log/metasrv.log &
/home/discord9/greptimedb/target/release/greptime datanode start -c config/datanode.example.toml > log/datanode.log &
/home/discord9/greptimedb/target/release/greptime frontend start -c config/frontend.example.toml > log/frontend.log &
/home/discord9/greptimedb/target/release/greptime flownode start -c config/flownode.example.toml > log/flownode.log
```
关闭：
```shell
pidof greptime | xargs kill
```


开始 pprof 并写入压测：
```shell
psql -h 127.0.0.1 -p 4003 -d public -c "CREATE DATABASE benchmark";
sleep 1;# wait for db creation
psql -h 127.0.0.1 -p 4003 -d benchmark -f create_table.sql;
sleep 1;# wait for table creation
psql -h 127.0.0.1 -p 4003 -d public -c "CREATE FLOW perf_flow SINK TO cnt_cpu AS SELECT COUNT(1) FROM greptime.benchmark.cpu;";
curl -s '0:4000/v1/prof/cpu?seconds=200&output=flamegraph' > flow_pprof.svg &
./bin/tsbs_load_greptime \
    --urls=http://localhost:4000 \
    --file=./bench-data/influx-data.lp \
    --batch-size=3000 \
    --gzip=false \
    --do-create-db=false \
    --workers=6 > tsbs_write.txt
```

基线：
```shell
curl -s '0:4000/v1/prof/cpu?seconds=200&output=flamegraph' > flow_pprof.svg &
./bin/tsbs_load_greptime \
    --urls=http://localhost:4000 \
    --file=./bench-data/influx-data.lp \
    --batch-size=3000 \
    --gzip=false \
    --workers=6 > tsbs_write.txt
```