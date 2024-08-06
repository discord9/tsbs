# GreptimeDB vs. InfluxDB TSBS 压测手册

本手册帮助开发者重现《GreptimeDB vs. InfluxDB 性能测试报告》测试结果，详细结果请阅读该报告。

## 测试工具

GreptimeDB fork 的仓库，相比官方版本增加了对 GreptimeDB 和 InfluxDB v2 的支持：
[https://github.com/GreptimeTeam/tsbs](https://github.com/GreptimeTeam/tsbs)

## 测试环境

**硬件环境：**
- **实例类型：** c5d.2xlarge
- **处理器规格：** 8 cores
- **内存：** 16 GB
- **硬盘：** 100GB (GP3)
- **操作系统：** Ubuntu Server 24.04 LTS

**软件版本：**
- **数据库：** 
    - **GreptimeDB:** v0.9.1
    - **InfluxDB:** v2.7.7

除了 GreptimeDB 为了测试存储 S3 而设置了本地缓存，其他参数配置均未进行特别调整，均采用默认设置。

## 软件安装

### 安装 Go

下载链接：
[https://go.dev/dl/go1.22.5.linux-amd64.tar.gz](https://go.dev/dl/go1.22.5.linux-amd64.tar.gz)

命令：
```sh
wget https://go.dev/dl/go1.22.5.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.22.5.linux-amd64.tar.gz
export PATH=$PATH:/usr/local/go/bin
go version
```

### 安装 InfluxDB

创建 influxdb2 目录：
```sh
mkdir influxdb2
cd influxdb2
```

下载 InfluxDB：
```sh
wget https://dl.influxdata.com/influxdb/releases/influxdb2-2.7.7_linux_amd64.tar.gz
tar xvfz influxdb2-2.7.7_linux_amd64.tar.gz
```

除此之外还需要安装 CLI：
```sh
wget https://download.influxdata.com/influxdb/releases/influxdb2-client-2.7.5-linux-amd64.tar.gz
tar xvfz influxdb2-client-2.7.5-linux-amd64.tar.gz
```

启动服务：
```sh
./influxdb2-2.7.7/usr/bin/influxd
```

输出
```sh
2024-07-17T09:13:21.202512Z     info    Welcome to InfluxDB     {"log_id": "0qR~KSCW000", "version": "v2.7.7", "commit": "e9e0f744fa", "build_date": "2024-07-11T18:45:02Z", "log_level": "info"}
...(省略)...
```

### 安装 GreptimeDB

GreptimeDB 的安装可以参考官方文档。你也可以参照下面的步骤安装 GreptimeDB v0.9.0。

在当前用户 home 目录下创建 greptime 目录
```sh
mkdir greptime
cd greptime
```

下载：
```sh
wget https://github.com/GreptimeTeam/greptimedb/releases/download/v0.9.1/greptime-linux-amd64-v0.9.1.tar.gz
tar xvfz greptime-linux-amd64-v0.9.1.tar.gz
```

随后可以直接通过以下命令运行 GreptimeDB，这里通过命令行参数指定了数据目录：
```sh
./greptime-linux-amd64-v0.9.1/greptime standalone start --data-home /path/to/greptime/data
```

此外，也可以通过配置文件配置更多参数。假设配置文件为 config.toml，则可以通过以下命令启动：
```sh
./greptime-linux-amd64-v0.9.1/greptime standalone start --config-file /path/to/config.toml
```

## 测试执行

### 测试数据生成

**TSBS** [Time Series Benchmark Suite] 并没有提供预编译的二进制，需要手动编译。编译 **TSBS** 需要提前安装 **Go**。具体可以参考 https://go.dev/doc/install 。测试使用的版本是 **1.22.5**.

安装 **Go** 之后，你可以 clone TSBS 到当前目录：
```bash
git clone https://github.com/GreptimeTeam/tsbs.git
```

如果没有安装 **make**，则需要先安装它:
```bash
sudo apt install make
```

进入 **tsbs** 目录并运行 **make** 来编译 TSBS。第一次编译可能需要一些时间,因为需要下载一些依赖项：
```bash
cd tsbs
make
```

编译成功后，可以在 **bin** 目录下看到许多生成的二进制文件，我们只会使用其中的一部分:
```bash
$ ls ./bin/
tsbs_generate_data     tsbs_load_influx2           tsbs_run_queries_clickhouse
tsbs_generate_queries  tsbs_load_mongo             tsbs_run_queries_cratedb
tsbs_load              tsbs_load_prometheus        tsbs_run_queries_influx
tsbs_load_akumuli      tsbs_load_questdb           tsbs_run_queries_mongo
tsbs_load_cassandra    tsbs_load_siridb            tsbs_run_queries_questdb
tsbs_load_clickhouse   tsbs_load_timescaledb       tsbs_run_queries_siridb
tsbs_load_cratedb      tsbs_load_victoriametrics   tsbs_run_queries_timescaledb
tsbs_load_greptime     tsbs_run_queries_akumuli    tsbs_run_queries_timestream
tsbs_load_influx       tsbs_run_queries_cassandra  tsbs_run_queries_victoriametrics
```

可以在 **tsbs** 目录内创建一个新目录用于存储生成的数据：
```bash
mkdir bench-data
```

运行生成数据的命令，其中 `influx-data.lp` 就是我们生成的测试数据文件，该数据文件用于单机测试：
```bash
./bin/tsbs_generate_data --use-case="cpu-only" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:00Z" --log-interval="10s" --format="influx" > ./bench-data/influx-data.lp
```

执行以下命令生成用于 **InfluxDB** 的查询：
```bash
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=100 --query-type cpu-max-all-1 --format="influx" > ./bench-data/influx-queries-cpu-max-all-1.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=100 --query-type cpu-max-all-8 --format="influx" > ./bench-data/influx-queries-cpu-max-all-8.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=50 --query-type double-groupby-1 --format="influx" > ./bench-data/influx-queries-double-groupby-1.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=50 --query-type double-groupby-5 --format="influx" > ./bench-data/influx-queries-double-groupby-5.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=50 --query-type double-groupby-all --format="influx" > ./bench-data/influx-queries-double-groupby-all.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=50 --query-type groupby-orderby-limit --format="influx" > ./bench-data/influx-queries-groupby-orderby-limit.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=100 --query-type high-cpu-1 --format="influx" > ./bench-data/influx-queries-high-cpu-1.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=50 --query-type high-cpu-all --format="influx" > ./bench-data/influx-queries-high-cpu-all.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=10 --query-type lastpoint --format="influx" > ./bench-data/influx-queries-lastpoint.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=100 --query-type single-groupby-1-1-1 --format="influx" > ./bench-data/influx-queries-single-groupby-1-1-1.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=100 --query-type single-groupby-1-1-12 --format="influx" > ./bench-data/influx-queries-single-groupby-1-1-12.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=100 --query-type single-groupby-1-8-1 --format="influx" > ./bench-data/influx-queries-single-groupby-1-8-1.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=100 --query-type single-groupby-5-1-1 --format="influx" > ./bench-data/influx-queries-single-groupby-5-1-1.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=100 --query-type single-groupby-5-1-12 --format="influx" > ./bench-data/influx-queries-single-groupby-5-1-12.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=100 --query-type single-groupby-5-8-1 --format="influx" > ./bench-data/influx-queries-single-groupby-5-8-1.dat
```

执行以下命令生成用于生成用于 **GreptimeDB** 的查询：
```bash
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=100 --query-type cpu-max-all-1 --format="greptime" > ./bench-data/greptime-queries-cpu-max-all-1.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=100 --query-type cpu-max-all-8 --format="greptime" > ./bench-data/greptime-queries-cpu-max-all-8.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=50 --query-type double-groupby-1 --format="greptime" > ./bench-data/greptime-queries-double-groupby-1.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=50 --query-type double-groupby-5 --format="greptime" > ./bench-data/greptime-queries-double-groupby-5.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=50 --query-type double-groupby-all --format="greptime" > ./bench-data/greptime-queries-double-groupby-all.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=50 --query-type groupby-orderby-limit --format="greptime" > ./bench-data/greptime-queries-groupby-orderby-limit.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=100 --query-type high-cpu-1 --format="greptime" > ./bench-data/greptime-queries-high-cpu-1.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=50 --query-type high-cpu-all --format="greptime" > ./bench-data/greptime-queries-high-cpu-all.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=10 --query-type lastpoint --format="greptime" > ./bench-data/greptime-queries-lastpoint.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=100 --query-type single-groupby-1-1-1 --format="greptime" > ./bench-data/greptime-queries-single-groupby-1-1-1.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=100 --query-type single-groupby-1-1-12 --format="greptime" > ./bench-data/greptime-queries-single-groupby-1-1-12.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=100 --query-type single-groupby-1-8-1 --format="greptime" > ./bench-data/greptime-queries-single-groupby-1-8-1.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=100 --query-type single-groupby-5-1-1 --format="greptime" > ./bench-data/greptime-queries-single-groupby-5-1-1.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=100 --query-type single-groupby-5-1-12 --format="greptime" > ./bench-data/greptime-queries-single-groupby-5-1-12.dat
./bin/tsbs_generate_queries --use-case="devops" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:01Z" --queries=100 --query-type single-groupby-5-8-1 --format="greptime" > ./bench-data/greptime-queries-single-groupby-5-8-1.dat
```


### InfluxDB

#### 初始化
InfluxDB 初次安装后需要初始化 InfluxDB 并拿到请求的 token，如果已经有 token 则可以跳过这部分。

初始化 InfluxDB：
```sh
./influx setup \
  --username test \
  --password 12345678 \
  --token test-token \
  --org test-org \
  --bucket test-bucket \
  --force
```

输出：
```
User    Organization    Bucket
test    test-org        test-bucket
```

创建 token：
```sh
./influx auth create \
  --org test-org \
  --all-access
```

输出：
```
ID                      Description     Token                                                                                           User Name       User ID                 Permissions
0d5c027a74259000                        VTw2gBvdrgqQLpR2drSfiVgaVy-W4LLnJ1JiyLIAHgYhKYJdj9eW3Z26pnjelCiC7Q-dBGHvpZpGykjE_WqIgQ==        test            0d5c0275c5e59000        ...
```

这里可以拿到 InfluxDB 的 token。为了方便后续请求，我们将该 token export 到环境变量里：
```sh
export INFLUX2_TOKEN="VTw2gBvdrgqQLpR2drSfiVgaVy-W4LLnJ1JiyLIAHgYhKYJdj9eW3Z26pnjelCiC7Q-dBGHvpZpGykjE_WqIgQ=="
```

#### 导入数据
在 `tsbs` 目录下，执行以下命令导入数据：
```sh
./bin/tsbs_load_influx2 \
    --urls=http://localhost:8086 \
    --file=./bench-data/influx-data.lp \
    --do-create-db=false \
    --org-id=test-org \
    --db-name=test-bucket \
    --batch-size=3000 \
    --workers=8 \
    --auth-token=$INFLUX2_TOKEN
```

#### 查询
在 `tsbs` 目录下，执行查询
```sh
./bin/tsbs_run_queries_influx --file=./bench-data/influx-queries-cpu-max-all-1.dat          --db-name=test-bucket   --is-v2=true  --auth-token=$INFLUX2_TOKEN   --urls="http://localhost:8086"
...(repeat for all queries)...
```

### GreptimeDB

GreptimeDB 测试了本地磁盘和基于 S3 的对象存储版本，两者配置如下：

#### 本地磁盘 (EBS)
测试使用到的配置文件为如下:
```toml
[http]
addr = "0.0.0.0:4000"

[logging]
dir = "/home/ubuntu/greptime/logs"

[storage]
data_home = "/home/ubuntu/greptime/data-local"
```

启动命令如下，这里假设 GreptimeDB 二进制路径为 `./greptime`，配置文件的路径为 `/home/ubuntu/greptime/config-local.toml`
```sh
./greptime standalone start --config /home/ubuntu/greptime/config-local.toml
```

#### S3 对象存储
使用 S3 时，需要额外指定 S3 的配置。示例配置如下，测试期间开启了 GreptimeDB 的本地盘缓存：
```toml
[http]
addr = "0.0.0.0:4000"

[logging]
dir = "/home/ubuntu/greptime/logs"

[storage]
data_home = "/home/ubuntu/greptime/data-s3"
type = "S3"
bucket = "your-bucket"
root = "tsbs-data-s3"
access_key_id = "****"
secret_access_key = "****"
endpoint = "https://s3-endpoint/"
region = "your-region"
cache_path = "/home/ubuntu/greptime/s3cache"
cache_capacity = "20G"

[[region_engine]]
[region_engine.mito]
enable_experimental_write_cache = true
experimental_write_cache_size = "20G"
```

启动命令如下，这里假设 GreptimeDB 二进制路径为 `./greptime`，配置文件的路径为 `/home/ubuntu/greptime/config-s3.toml`
```sh
./greptime standalone start --config /home/ubuntu/greptime/config-s3.toml
```

#### 数据导入
在 `tsbs` 目录下，直接通过以下命令导入数据：
```sh
./bin/tsbs_load_greptime \
    --urls=http://localhost:4000 \
    --file=./bench-data/influx-data.lp \
    --batch-size=3000 \
    --gzip=false \
    --workers=6
```

#### 查询
在 `tsbs` 目录下，执行查询：
```sh
./bin/tsbs_run_queries_influx --file=./bench-data/greptime-queries-cpu-max-all-1.dat          --db-name=benchmark   --urls="http://localhost:4000"
...(用类似的命令执行其他查询)...
```

## 参考链接

- [InfluxData Downloads](https://www.influxdata.com/downloads/)
- [InfluxDB Installation](https://docs.influxdata.com/influxdb/v2/install/#start-influxdb)
- [InfluxDB CLI Tools](https://docs.influxdata.com/influxdb/v2/tools/influx-cli/?t=Linux)
- [InfluxDB Setup](https://docs.influxdata.com/influxdb/v2/get-started/setup/?t=Set+up+with+the+CLI)
- [Greptime Team TSBS](https://github.com/GreptimeTeam/tsbs)
- TSBS v0.9 vs InfluxDB

