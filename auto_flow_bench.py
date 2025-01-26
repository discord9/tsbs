import os, shutil, psutil, signal
from typing import Literal
from pathlib import Path
import time
import subprocess
import json
import atexit
import plot_flow_bench
import signal
import types

def clean_db_dir(path: str):
    path = Path(path)
    if os.path.exists(path):
        shutil.rmtree(path)


def start_greptime(
    run_name: str = "baseline",
    mode: Literal["standalone", "distributed"] = "standalone",
    with_samply=False,
    db_log="db.log",
) -> list[subprocess.Popen] | tuple[subprocess.Popen, dict[int, str]]:
    f = open(db_log, "w")
    if mode == "standalone":
        cmd = ((["samply", "record", "-s", "-o", "bench_log/{}.samply.json".format(run_name)]
                if with_samply
                else [])
                + [
                    "./greptime",
                    "standalone",
                    "start",
                    "-c",
                    "config.toml",
                ])
        print("Starting db with cmd: ", cmd)
        handler = subprocess.Popen(
            cmd,
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


def kill_db(handlers: list[subprocess.Popen], sig: int = signal.SIGINT):
    """kill the db process with SIGINT for graceful shutdown"""
    for handler in handlers:
        handler.send_signal(sig)
        # https://github.com/python/cpython/issues/119059#issuecomment-2113154389
        # os.killpg(os.getpgid(handler.pid), signal.SIGINT)


def create_flow(flow_num: int, key_num=4000, flow_type="simple"):
    # time range is 2023-06-11 00:00:00.000000 to  2023-06-13 23:59:50.000000
    factor = 4000 // key_num
    complex_query = """CREATE FLOW {flow_name} 
  SINK TO {flow_sink}
  AS 
  SELECT 
    substr(hostname, 6)::int/{factor} as host_group, 
    sum(CASE WHEN usage_user > 50 THEN usage_user ELSE 0 END) 
    FROM benchmark.cpu 
    GROUP BY host_group;"""
    # This will use 100% cpu
    simple_query = """CREATE FLOW {flow_name} SINK TO {flow_sink} AS SELECT count(ts) from benchmark.cpu;"""

    if flow_type == "simple":
        query = simple_query
    elif flow_type == "complex":
        query = complex_query
    else:
        raise ValueError("flow_type must be simple or complex")
    # create_flow = """psql -h 127.0.0.1 -p 4003 -d public -c "CREATE FLOW {flow_name} SINK TO cnt_cpu AS SELECT SUM(usage_user), date_bin(INTERVAL '1 hour', ts) as time_window FROM benchmark.cpu GROUP BY time_window;";"""
    # create_flow = """psql -h 127.0.0.1 -p 4003 -d public -c "CREATE FLOW {flow_name} SINK TO cnt_cpu AS SELECT count(ts) from benchmark.cpu;";"""
    create_flow = """psql -h 127.0.0.1 -p 4003 -d public -c "{flow_query}";"""

    for i in range(flow_num):
        cur_query = query.format(
            flow_name=f"flow_{i}", flow_sink=f"cnt_cpu_{i}", factor=factor
        )
        os.system(create_flow.format(flow_query=cur_query))
        # time.sleep(0.1)


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


def get_db_pid() -> list[int]:
    return [
        p.info["pid"]
        for p in psutil.process_iter(attrs=["pid", "name"])
        if "greptime" in p.info["name"]
    ]


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


def wait_for_end_insertion(
    usage: Usage,
    tsbs_handler: subprocess.Popen,
    db_pid: int,
    save_path: str,
    pid2name: dict,
):
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


def show_results(flow_num):
    """
    show the results of the flow"""
    if flow_num > 0:
        os.system(
            """psql -h 127.0.0.1 -p 4003 -d public -c "select * from cnt_cpu_0;" """
        )


if __name__ == "__main__":
    # baseline, simple, complex 100, 400, 1000, 2000, 4000
    with open("benchargs.json", "r") as f:
        args = json.load(f)
        
        benchargs = args["benchargs"]
        with_samply = args["with_samply"]
        auto_start_db = args["auto_start_db"]

    MEM_THRESHOLD = 20 * 1024 * 1024 * 1024  # 20GB
    mem_overflow_countdown = (
        10  # if memory usage is over MEM_THRESHOLD, wait for 10 seconds before exit
    )
    for arg in benchargs:
        print("-" * 20)
        print("pidof greptime: ", get_db_pid())
        print("Running: ", arg["run_name"])
        if not os.path.exists("bench_log"):
            os.makedirs("bench_log")
        create_flow_arg = {
            key: arg[key] for key in ["flow_num", "key_num", "flow_type"] if key in arg
        }
        if auto_start_db:
            clean_db_dir("db")
            time.sleep(1)
            db_handler, pid2name = start_greptime(
                run_name=arg["run_name"],
                mode="standalone",
                with_samply=with_samply,
                db_log=arg["db_log"],
            )
            print("db boot, pid: ", db_handler.pid)
            atexit.register(lambda: kill_db([db_handler]))
        else:
            dbpid = get_db_pid()
            db_handler = {"pid": dbpid[0]}
            db_handler = types.SimpleNamespace(**db_handler)

        time.sleep(5)
        prepare_table()
        print("Table prepared")

        create_flow(**create_flow_arg)
        if arg["flow_num"] > 0:
            print("Flows created")

        tsbs = load_greptime()
        print("Start tsbs, pid: ", tsbs.pid)
        usage = Usage()
        while tsbs.poll() == None:
            cpu_mem = read_mem_cpu([db_handler.pid], {db_handler.pid: "greptime"})
            mem = cpu_mem["greptime"]["memory_info"][0]
            if mem > MEM_THRESHOLD:
                print("Memory usage over threshold, will kill db in 10 seconds")
                break

            usage.append_and_dump(cpu_mem, arg["usage_save"])

        query_result = [
            "psql",
            "-h",
            "127.0.0.1",
            "-p",
            "4003",
            "-d",
            "public",
            "-c",
            "SELECT count(1) FROM cnt_cpu_0;",
        ]
        with open("bench_log/query_result_{}.txt".format(arg["run_name"]), "w") as f:
            subprocess.Popen(
                query_result,
                stdout=f,
                stderr=f,
                text=True,
            ).wait()
        if auto_start_db:
            time.sleep(5)
            print("Try kill db")
            kill_db([db_handler])
            time.sleep(5)
            if db_handler.poll() != None:
                print("db killed")
            else:
                while db_handler.poll() == None:
                    print("db not killed, wait for graceful shutdown")
                    if with_samply:
                        time.sleep(30)
                    time.sleep(5)
                    kill_db([db_handler], signal.SIGKILL)

        os.system(
            "cp tsbs_write.txt bench_log/tsbs_write_{}.txt".format(arg["run_name"])
        )

        plot_flow_bench.draw(arg["usage_save"])
        print("Done: ", arg["run_name"])
