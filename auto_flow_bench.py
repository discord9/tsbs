import os, shutil, psutil, signal
from typing import Literal
from pathlib import Path
import time
import subprocess
import json


def clean_db_dir(path: str):
    path = Path(path)
    if os.path.exists(path):
        shutil.rmtree(path)


def start_greptime(
    run_name: str = "baseline",
    mode: Literal["standalone", "distributed"] = "standalone",
    with_samply=False,
) -> list[subprocess.Popen] | tuple[subprocess.Popen, dict[int, str]]:
    f = open("db.log", "w")
    if mode == "standalone":
        handler = subprocess.Popen(
            (
                ["samply", "record"]
                if with_samply
                else []
                + [
                    "/home/discord9/greptimedb/target/release/greptime",
                    "standalone",
                    "start",
                    "-c",
                    "config.toml",
                ]
            ),
            stdout=f,
            stderr=f,
            text=True,
        )
        return handler, {handler.pid: run_name}
    elif mode == "distributed":
        # TODO: start the distributed mode
        pass
    else:
        raise ValueError("mode must be standalone or distributed")


def kill_db(handlers: list[subprocess.Popen]):
    """kill the db process with SIGINT for graceful shutdown"""
    for handler in handlers:
        handler.send_signal(signal.SIGINT)
        # https://github.com/python/cpython/issues/119059#issuecomment-2113154389
        # os.killpg(os.getpgid(handler.pid), signal.SIGINT)


def create_flow(flow_num: int):
    # time range is 2023-06-11 00:00:00.000000 to  2023-06-13 23:59:50.000000
    # create_flow = """psql -h 127.0.0.1 -p 4003 -d public -c "CREATE FLOW {flow_name} SINK TO cnt_cpu AS SELECT SUM(usage_user), date_bin(INTERVAL '1 hour', ts) as time_window FROM benchmark.cpu GROUP BY time_window;";"""
    create_flow = """psql -h 127.0.0.1 -p 4003 -d public -c "CREATE FLOW {flow_name} SINK TO cnt_cpu AS SELECT count(ts) from benchmark.cpu;";"""
    for i in range(flow_num):
        os.system(create_flow.format(flow_name=f"flow_{i}"))
        #time.sleep(0.1)


def prepare_table():
    """create benchmark database and cpu table"""
    cmds = [
        """psql -h 127.0.0.1 -p 4003 -d public -c "CREATE DATABASE benchmark";""",
        """psql -h 127.0.0.1 -p 4003 -d benchmark -f create_table.sql;""",
    ]
    for cmd in cmds:
        os.system(cmd)
        time.sleep(1)


def load_greptime():

    cmd = """./bin/tsbs_load_greptime \
    --urls=http://localhost:4000 \
    --file=./bench-data/influx-data.lp \
    --batch-size=3000 \
    --gzip=false \
    --do-create-db=false \
    --workers=6 > tsbs_write.txt"""

    return subprocess.Popen(cmd, shell=True)


def read_mem_cpu(pids: list[int], pid2name: dict) -> dict:
    """
    return current memory and cpu usage for the given pids
    will block for one second to get the average cpu usage
    """
    procs = {}
    for pid in pids:
        procs[pid] = psutil.Process(pid)

    ret = {}
    for pid, proc in procs.items():
        name = pid2name[pid]
        ret[name] = {
            "memory_info": proc.memory_info(),
            "cpu_percent": proc.cpu_percent(1.0),
        }
    return ret

def get_db_pid()->list[int]:
    return [p.info["pid"] for p in psutil.process_iter(attrs=["pid", "name"]) if "greptime" in p.info["name"]]

class Usage:
    def __init__(self) -> None:
        self.usage = []

    def append(self, cpu_mem: dict):
        self.usage.append(cpu_mem)

    def dump(self, path: str):
        with open(path, "w") as f:
            json.dump(self.usage, f)

    def append_and_dump(self, cpu_mem: dict, path: str = "usage.json"):
        self.append(cpu_mem)
        self.dump(path)


def start_pprof(duration: int, svg_path: str = "flow_pprof.svg") -> subprocess.Popen:
    f = open("pprof.log", "w")
    return subprocess.Popen(
        [
            "curl",
            "-s",
            "'0:4000/v1/prof/cpu?seconds={duration}&output=flamegraph'".format(
                duration=duration
            ),
        ],
        stdout=f,
    )

def wait_for_end_insertion(usage: Usage, tsbs_handler: subprocess.Popen, db_pid: int, save_path: str, pid2name: dict):
    start = time.time()
    while tsbs_handler.poll() == None:
        cpu_mem = read_mem_cpu([db_pid], pid2name)
        usage.append_and_dump(cpu_mem, save_path)
    end = time.time()
    after_bench_wait = (end - start) * 0.5
    print("Done benchmark, waiting for {} seconds".format(after_bench_wait))
    while after_bench_wait > 0:
        cpu_mem = read_mem_cpu([db_pid], pid2name)
        usage.append_and_dump(cpu_mem, save_path)
        after_bench_wait -= 1
    
def baseline(save_path: str = "usage_baseline.json", with_samply=False):
    """baseline tsbs test with no flows"""
    clean_db_dir("db")
    db_handler, pid2name = start_greptime(with_samply)
    # wait a bit for db to start
    time.sleep(1)
    prepare_table()
    create_flow(1)
    tsbs_handler = load_greptime()
    usage = Usage()
    read_mem_cpu([db_handler.pid], pid2name)

    wait_for_end_insertion(usage, tsbs_handler, db_handler.pid, save_path, pid2name)

    time.sleep(1)
    kill_db([db_handler])


if __name__ == "__main__":
    CNT = 500
    prepare_table()
    create_flow(CNT)
    db_pids= get_db_pid()

    tsbs = load_greptime()
    usage = Usage()
    while tsbs.poll() == None:
        cpu_mem = read_mem_cpu(db_pids, {db_pids[0]: "greptime"})
        usage.append_and_dump(cpu_mem, "usage_{CNT}.json".format(CNT=CNT))

