#!/usr/bin/env python3

import asyncio
import json
import os.path
import time

VMS_DIR = "../vms/connect4/"
OUTPUT_DIR = "pages/"
CARGO_BINARY = "cargo"
TIMEOUT_SECONDS = 40
GAMMA = 2.2
VALUE_MIN = 48


class VM:
    def __init__(self, name):
        self.name = name
        self.matchups = dict()

    def filename(self):
        return VMS_DIR + self.name + ".segment"


def change_to_this_files_dir():
    os.chdir(os.path.dirname(__file__))


def collect_vms():
    vms = []
    for filename in os.listdir(VMS_DIR):
        if filename.endswith(".segment"):
            vms.append(VM(filename[:-len(".segment")]))
    vms.sort(key=lambda vm: vm.name)
    for i in range(len(vms) - 1):
        if vms[i + 1].name.startswith(vms[i].name):
            print(f"VM names must not be prefixes of each other! Problem with >>{vms[i].name}<< and >>{vms[i + 1].name}<<.")
            exit(1)
    return vms


def analyze_matchup(matchup):
    wins = 0
    draws = 0
    losses = 0
    for game in matchup:
        result = game["res"]
        if result["type"] == "draw":
            draws += 1
        elif result["type"] == "win" and result["by"] == 1:
            wins += 1
        elif result["type"] == "win" and result["by"] == 2:
            losses += 1
        else:
            assert False, (vm_one.name, vm_two.name, game)
    return wins, draws, losses


async def run_matchup(vm_one, vm_two):
    assert vm_two.name not in vm_one.matchups
    command = [
        CARGO_BINARY,
        "run",
        "--release",
        "--",
        vm_one.filename(),
        vm_two.filename(),
    ]
    proc = await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        # asyncio doesn't support text=True :(
    )
    try:
        stdout_bin, stderr_bin = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_SECONDS)
    except TimeoutError:
        stderr_bin = b"<timeout>"
    if proc.returncode != 0:
        print(f"ERROR! Running on {vm_one.name} and {vm_two.name} resulted in an error.")
        print(f"{command=} {proc.returncode=}")
        print("<=== BEGIN STDERR DUMP ===>")
        print(stderr_bin.decode(errors="replace"))
        print("<=== END STDERR DUMP ===>")
        # Abort everything.
        # Note that if exit() doesn't work, this will cause a hang due to a queue.task_done().
        exit(1)
    matchup = json.loads(stdout_bin.decode())
    vm_one.matchups[vm_two.name] = matchup


def emit_matchup(vm_one, vm_two):
    print(f"Skipping matchup page for {vm_one.name} <-> {vm_two.name}")
    # FIXME: raise NotImplementedError()


def emit_vm_summary(vm, all_vms):
    print(f"Skipping VM summary page for {vm.name}")
    # FIXME: raise NotImplementedError()


def compute_color(wins, draws, losses):
    fracs = [
        losses / (wins + draws + losses),
        wins / (wins + draws + losses),
        draws / (wins + draws + losses),
    ]
    assert 0.999 < sum(fracs) < 1.001, (wins, draws, losses, fracs)
    # This is terrible to read, but it's just gamma interpolation and conversion to hex:
    rgb = [int(VALUE_MIN + (255 - VALUE_MIN) * (c ** (1 / GAMMA))) for c in fracs]
    code = [f"{c:02x}" for c in rgb]
    return "#" + "".join(code)


def generate_overview_table(all_vms):
    parts = ["<table>"]
    # Header row
    parts.append("<tr>")
    parts.append("<th></th>")
    for vm in all_vms:
        parts.append(f"<th class=\"defender-th\"><div class=\"defender-outer\"><span class=\"defender-inner\">{vm.name}</span></div></th>")
    parts.append("</tr>")
    # Data
    for vm_one in all_vms:
        parts.append("<tr>")
        parts.append(f"<th class=\"attacker\">{vm_one.name}</th>")
        for vm_two in all_vms:
            matchup = vm_one.matchups[vm_two.name]
            wins, draws, losses = analyze_matchup(matchup)
            color = compute_color(wins, draws, losses)
            parts.append(f"<td class=\"result\" style=\"background-color: {color};\">{wins}/{draws}/{losses}</td>")
        parts.append("</tr>")
    parts.append("</table>")
    return "".join(parts)


def emit_total_summary(all_vms):
    context = dict()
    context["overview_table"] = generate_overview_table(all_vms)
    context["last_build"] = time.strftime("%Y-%m-%d %T %Z")
    with open("template_total_summary.html", "r") as fp:
        template = fp.read()
    with open(OUTPUT_DIR + "index.html", "w") as fp:
        fp.write(template.format(**context))
    total_dict = {vm.name: vm.matchups for vm in all_vms}
    with open(OUTPUT_DIR + "results_general.json", "w") as fp:
        json.dump(total_dict, fp, separators=",:", sort_keys=True)


async def run_matches_from_queue(queue):
    while True:
        job = await queue.get()
        if job is None:
            return
        vm_one, vm_two = job
        started_at = time.monotonic()
        await run_matchup(vm_one, vm_two)
        completed_at = time.monotonic()
        print(f"Finished matchup {vm_one.name} vs. {vm_two.name} in {completed_at - started_at:.3f}s.")
        queue.task_done()


async def run_all_matchups(vms):
    # Heavily inspired by https://docs.python.org/3/library/asyncio-queue.html#examples
    queue = asyncio.Queue()
    for vm_one in vms:
        for vm_two in vms:
            queue.put_nowait((vm_one, vm_two))
    concurrency = max(1, os.cpu_count() - 1)
    print(f"Running up to {concurrency} matches in parallel ...")
    async with asyncio.TaskGroup() as tg:
        for i in range(concurrency):
            tg.create_task(run_matches_from_queue(queue))
        await queue.join()
        # TODO: Can probably start shutting down even earlier, but that's micro-optimization.
        for i in range(concurrency):
            # Send shutdown signal:
            queue.put_nowait(None)


async def run():
    change_to_this_files_dir()
    if not os.path.exists(OUTPUT_DIR):
        print(f"Directory {OUTPUT_DIR} doesn't exist. Creating an empty directory.")
        os.mkdir(OUTPUT_DIR)

    vms = collect_vms()
    print(f"Found {len(vms)} VMs: {[vm.name for vm in vms]}")

    await run_all_matchups(vms)

    for vm_one in vms:
        for vm_two in vms:
            emit_matchup(vm_one, vm_two)
    # FIXME: Should order vms by success, but no idea how to measure that.
    # Hopefully that becomes clear later.
    for vm in vms:
        emit_vm_summary(vm, vms)
    emit_total_summary(vms)


if __name__ == "__main__":
    asyncio.run(run())
