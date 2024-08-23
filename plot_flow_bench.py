from matplotlib import pyplot as plt
import json


def draw(path="usage.json"):
    # read json file
    f = open(path)
    usages = json.load(f)
    f.close()

    procs = {}
    for usage in usages:
        for pid, content in usage.items():
            if pid not in procs:
                procs[pid] = {"cpu":[], "mem":[]}
            procs[pid]["cpu"].append(content["cpu_percent"])
            # rss
            procs[pid]["mem"].append(content["memory_info"][0]//1024//1024)

    fig, ax = plt.subplots(1, 1)

    for pid, curve in procs.items():
        ax.plot(curve["mem"], label=pid)

    ax.legend()
    ax.set_title("Memory Usage (MB)")
    
    img = path.removesuffix(".json") + "_mem.png"
    fig.savefig(img)

    fig, ax = plt.subplots(1, 1)
    for pid, curve in procs.items():
        ax.plot(curve["cpu"], label=pid)

    ax.legend()
    ax.set_title("CPU Percent")
    
    img = path.removesuffix(".json") + "_cpu.png"
    fig.savefig(img)

def draw_in_one_mem(files: list[str], legends: list[str]):
    fig, ax = plt.subplots(1, 1)


    for idx, f in enumerate(files):
        with open(f) as f:
            usages = json.load(f)

        procs = {}
        for usage in usages:
            for pid, content in usage.items():
                if pid not in procs:
                    procs[pid] = {"cpu":[], "mem":[]}
                procs[pid]["cpu"].append(content["cpu_percent"])
                # rss
                procs[pid]["mem"].append(content["memory_info"][0]//1024//1024)
        
        for pid, curve in procs.items():
            ax.plot(curve["mem"], label=legends[idx])

    ax.legend()
    ax.set_title("Memory Usage (MB)")
    img = "all_in_one_mem.png"
    fig.savefig(img)

def draw_in_one_cpu(files: list[str], legends: list[str]):
    fig, ax = plt.subplots(1, 1)


    for idx, f in enumerate(files):
        with open(f) as f:
            usages = json.load(f)

        procs = {}
        for usage in usages:
            for pid, content in usage.items():
                if pid not in procs:
                    procs[pid] = {"cpu":[], "mem":[]}
                procs[pid]["cpu"].append(content["cpu_percent"])
                # rss
                procs[pid]["mem"].append(content["memory_info"][0]//1024//1024)
        
        for pid, curve in procs.items():
            ax.plot(curve["cpu"], label=legends[idx])

    ax.legend()
    ax.set_title("CPU Usage(%)")
    img = "all_in_one_cpu.png"
    fig.savefig(img)
    

if __name__ == "__main__":
    cata = [0, 1, 10, 100, 300, 500]
    files = [f"usage_{c}.json" for c in cata]
    legends = [str(c) for c in cata]
    draw_in_one_cpu(files, legends)
