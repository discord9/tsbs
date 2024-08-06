# GreptimeDB vs. InfluxDB TSBS Testing Manual

This manual helps developers reproduce the test results from the "GreptimeDB vs. InfluxDB Performance Test Report". For detailed results, please read the report.

## Testing Tools

GreptimeDB fork branch, which adds support for GreptimeDB and InfluxDB v2 compared to the official version:
[https://github.com/GreptimeTeam/tsbs](https://github.com/GreptimeTeam/tsbs)

## Test Environment

**Hardware Environment:**
- **Instance Type:** c5d.2xlarge
- **Processor Specifications:** 8 cores
- **Memory:** 16 GB
- **Disk:** 100GB (GP3)
- **Operating System:** Ubuntu Server 24.04 LTS

**Software Version:**
- **Database:** 
    - **GreptimeDB:** v0.9.1
    - **InfluxDB:** v2.7.7

Except for GreptimeDB being set up with local caching for S3 testing, all other parameter configurations remain default without special adjustments.

## Software Installation

### Installing Go

Download link:
[https://go.dev/dl/go1.22.5.linux-amd64.tar.gz](https://go.dev/dl/go1.22.5.linux-amd64.tar.gz)

Commands:
```sh
wget https://go.dev/dl/go1.22.5.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.22.5.linux-amd64.tar.gz
export PATH=$PATH:/usr/local/go/bin
go version
```

### Installing InfluxDB

Create influxdb2 directory:
```sh
mkdir influxdb2
cd influxdb2
```

Download InfluxDB:
```sh
wget https://dl.influxdata.com/influxdb/releases/influxdb2-2.7.7_linux_amd64.tar.gz
tar xvfz influxdb2-2.7.7_linux_amd64.tar.gz
```

Additionally, install CLI:
```sh
wget https://download.influxdata.com/influxdb/releases/influxdb2-client-2.7.5-linux-amd64.tar.gz
```

Start the server:
```sh
./influxdb2-2.7.7/usr/bin/influxd
```

Output:
```sh
2024-07-17T09:13:21.202512Z     info    Welcome to InfluxDB     {"log_id": "0qR~KSCW000", "version": "v2.7.7", "commit": "e9e0f744fa", "build_date": "2024-07-11T18:45:02Z", "log_level": "info"}
...(trimmed for brevity)...
```

### Installing GreptimeDB

Refer to the official documentation for installing GreptimeDB:

Create greptime directory in the home directory:
```sh
mkdir greptime
cd greptime
```

Download:
```sh
wget https://github.com/GreptimeTeam/greptimedb/releases/download/v0.9.1/greptime-linux-amd64-v0.9.1.tar.gz
tar xvfz greptime-linux-amd64-v0.9.1.tar.gz
```

Run GreptimeDB with the following command, specifying the data directory via command-line parameters:
```sh
./greptime-linux-amd64-v0.9.1/greptime standalone start --data-home /path/to/greptime/data
```

Alternatively, you can configure additional parameters via a configuration file. Assuming the configuration file is named `config.toml`, you can start it with:
```sh
./greptime-linux-amd64-v0.9.1/greptime standalone start --config-file /path/to/config.toml
```

## Test Execution

### Test Data Generation

**TSBS** [Time Series Benchmark Suite] does not provide precompiled binaries, so it needs to be compiled manually. Compiling **TSBS** requires **Go** to be installed beforehand. You can refer to https://go.dev/doc/install for specific details. The version used this time is **1.22.5**.

After installing **Go**, you can clone TSBS to the current directory:
```bash
git clone https://github.com/GreptimeTeam/tsbs.git
```

If **make** is not available, you need to install **make** first:
```bash
sudo apt install make
```

Navigate to the **tsbs** directory and run **make** to compile TSBS. The first time you compile, it might take a while as some dependencies are downloaded:
```bash
cd tsbs
make
```

Once the compilation is successful, you should see many binaries generated under the **bin** directory, although we will only use a part of them:
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

To generate a directory to store the generated data, you can create a new directory within the **tsbs** directory:
```bash
mkdir bench-data
```

Run the data generation command, where `influx-data.lp` is the generated test data file, which will be used for single-machine testing:
```bash
./bin/tsbs_generate_data --use-case="cpu-only" --seed=123 --scale=4000 --timestamp-start="2023-06-11T00:00:00Z" --timestamp-end="2023-06-14T00:00:00Z" --log-interval="10s" --format="influx" > ./bench-data/influx-data.lp
```

Execute the following commands to generate queries for **InfluxDB**:
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

Execute the following commands to generate queries for **GreptimeDB**:
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

#### Initialize
After the first installation, InfluxDB needs to be initialized to obtain a token for requests. If you already have a token, you can skip this part.

Initialize InfluxDB:
```sh
./influx setup \
  --username test \
  --password 12345678 \
  --token test-token \
  --org test-org \
  --bucket test-bucket \
  --force
```

Output:
```
User    Organization    Bucket
test    test-org        test-bucket
```

Create token:
```sh
./influx auth create \
  --org test-org \
  --all-access
```

Output:
```
ID                      Description     Token                                                                                           User Name       User ID                 Permissions
0d5c027a74259000                        VTw2gBvdrgqQLpR2drSfiVgaVy-W4LLnJ1JiyLIAHgYhKYJdj9eW3Z26pnjelCiC7Q-dBGHvpZpGykjE_WqIgQ==        test            0d5c0275c5e59000        ...
```

Export the token for subsequent requests:
```sh
export INFLUX2_TOKEN="VTw2gBvdrgqQLpR2drSfiVgaVy-W4LLnJ1JiyLIAHgYhKYJdj9eW3Z26pnjelCiC7Q-dBGHvpZpGykjE_WqIgQ=="
```

#### Data Import
To import data in the `tsbs` directory, run the following command:
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

#### Queries
Run the queries in the `tsbs` directory:
```sh
./bin/tsbs_run_queries_influx --file=./bench-data/influx-queries-cpu-max-all-1.dat          --db-name=test-bucket   --is-v2=true  --auth-token=$INFLUX2_TOKEN   --urls="http://localhost:8086"
...(repeat for all queries)...
```

### GreptimeDB

GreptimeDB was tested with both local disk and S3-based object storage. Configurations for both are as follows:

#### Local Disk (EBS)
Configuration file used for testing:
```toml
[http]
addr = "0.0.0.0:4000"

[logging]
dir = "/home/ubuntu/greptime/logs"

[storage]
data_home = "/home/ubuntu/greptime/data-local"
```

Startup command assuming the GreptimeDB binary path is `./greptime` and the config file path is `/home/ubuntu/greptime/config-local.toml`:
```sh
./greptime standalone start --config /home/ubuntu/greptime/config-local.toml
```

#### S3 Object Storage
When using S3, additional S3 configurations are required. Example configuration during testing with local disk cache enabled:
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

Startup command assuming the GreptimeDB binary path is `./greptime` and the config file path is `/home/ubuntu/greptime/config-s3.toml`:
```sh
./greptime standalone start --config /home/ubuntu/greptime/config-s3.toml
```

#### Data Import
To import data in the `tsbs` directory, run the following command:
```sh
./bin/tsbs_load_greptime \
    --urls=http://localhost:4000 \
    --file=./bench-data/influx-data.lp \
    --batch-size=3000 \
    --gzip=false \
    --workers=6
```

#### Queries
Run the queries in the `tsbs` directory:
```sh
./bin/tsbs_run_queries_influx --file=./bench-data/greptime-queries-cpu-max-all-1.dat          --db-name=benchmark   --urls="http://localhost:4000"
...(repeat for all queries)...
```

## References

- [InfluxData Downloads](https://www.influxdata.com/downloads/)
- [InfluxDB Installation](https://docs.influxdata.com/influxdb/v2/install/#start-influxdb)
- [InfluxDB CLI Tools](https://docs.influxdata.com/influxdb/v2/tools/influx-cli/?t=Linux)
- [InfluxDB Setup](https://docs.influxdata.com/influxdb/v2/get-started/setup/?t=Set+up+with+the+CLI)
- [Greptime Team TSBS](https://github.com/GreptimeTeam/tsbs)
- TSBS v0.9 vs InfluxDB

