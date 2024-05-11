#!/usr/bin/env python3

import asyncio
import collections
import json
import os.path
import random
import time

VMS_DIR = "../vms/connect4/"
OUTPUT_DIR = "pages/"
CARGO_BINARY = "cargo"
TIMEOUT_SECONDS = 40
GAMMA = 2.2
VALUE_MIN = 48
BOARD_WIDTH = 7
BOARD_HEIGHT = 6
# These feel like they don't belong here:
DET_TEXT_ONE = "This matchup is deterministic, i.e. both players never used the <code>rnd</code> instruction. Therefore, only a single game was simulated, as all games are identical in this matchup."
DET_TEXT_MANY_IDENTICAL = "This matchup could not be determined to be deterministic, even though all games are identical. This can happen, for example, if a player uses the <code>rnd</code> instruction but does not really use the result for some reason."
DET_TEXT_MANY_EXTREME = "This matchup is not deterministic. Some games went differently than others, even though the outcome was always the same."
DET_TEXT_MANY_VARIED = "This matchup is not deterministic."

TIMESTAMP = time.strftime("%Y-%m-%d %T %Z")


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
            vms.append(VM(filename[: -len(".segment")]))
    vms.sort(key=lambda vm: vm.name)
    for i in range(len(vms) - 1):
        if vms[i + 1].name.startswith(vms[i].name):
            print(
                f"VM names must not be prefixes of each other! Problem with >>{vms[i].name}<< and >>{vms[i + 1].name}<<."
            )
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
            assert False, game
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
        stdout_bin, stderr_bin = await asyncio.wait_for(
            proc.communicate(), timeout=TIMEOUT_SECONDS
        )
    except TimeoutError:
        stderr_bin = b"<timeout>"
    if proc.returncode != 0:
        print(
            f"ERROR! Running on {vm_one.name} and {vm_two.name} resulted in an error."
        )
        print(f"{command=} {proc.returncode=}")
        print("<=== BEGIN STDERR DUMP ===>")
        print(stderr_bin.decode(errors="replace"))
        print("<=== END STDERR DUMP ===>")
        # Abort everything.
        # Note that if exit() doesn't work, this will cause a hang due to a queue.task_done().
        exit(1)
    matchup = json.loads(stdout_bin.decode())
    vm_one.matchups[vm_two.name] = matchup


def matchup_filename(vm_one, vm_two):
    return f"matchup-{vm_one.name}-vs-{vm_two.name}.html"


def hashable_game(game):
    return tuple([game["moves"], *game["res"].values(), *game["times"]])


def render_game_from_moves(moves):
    # This name needs to be minimized because it saves literal megabytes in the rendered HTML.
    board = [[("e", "")] * BOARD_WIDTH for _ in range(BOARD_HEIGHT)]
    top_row_by_col = [BOARD_HEIGHT - 1] * BOARD_WIDTH
    next_player = {"r": "y", "y": "r"}
    current_player = "r"
    for num_move, move_col in enumerate(moves):
        col = int(move_col)
        top_row = top_row_by_col[col]
        top_row_by_col[col] -= 1
        assert board[top_row][col] == ("e", "")
        board[top_row][col] = (current_player, f"#{num_move + 1}")
        current_player = next_player[current_player]
    return board


def generate_games_list(games_by_type):
    # TODO: The type of 'games_by_type' is awkward and should be refactored.
    games_list = [
        (len(games_list), games_list[0]) for games_list in games_by_type.values()
    ]
    limit = len(games_list)
    # We want to cut off at 20 games per page, but it's silly to cut off just a few games.
    # However, we need to draw the line (heh) somewhere, so we draw it at 25:
    if len(games_list) > 25:
        limit = 20
        # We cannot display the entire list, so let's try to be helpful. Order by number of occurrences (highest first), and shuffle ties.
        # This way, if something happens "often enough", it is extremely likely to end up in the generated HTML.

        # There is no good way to order the list, since the "juicy part" might be cut off.
        # Instead, shuffle the list, and hope that the "juicy part" happens often enough to make it into the printed part.
        random.shuffle(games_list)
        games_list = sorted(games_list, key=lambda e: -e[0])
        # Note that "sorted" is guaranteed to be stable, which is what we use here:
        # https://docs.python.org/3/library/functions.html#sorted
    else:
        # We can display the entire list, so let's try to be helpful. Order by:
        # - Number of occurrences (highest first)
        # - In case of ties, order by game length (shortest first)
        # - In case of ties, order by moves alphabetically (i.e. leftmost move first)
        games_list.sort(key=lambda e: (-e[0], len(e[1]["moves"]), e[1]["moves"]))
    parts = []
    for i, (occurrences, game) in enumerate(games_list[:limit]):
        if len(games_list) > 1:
            time_plural = "" if occurrences == 1 else "s"
            parts.append(
                f"<h4>Game type #{i + 1} (seen {occurrences} time{time_plural})</h4>"
            )
        if game["res"]["type"] == "draw":
            action_verb = "Draw"
        elif game["res"]["type"] == "win" and game["res"]["by"] == 1:
            action_verb = "Win"
        elif game["res"]["type"] == "win" and game["res"]["by"] == 2:
            action_verb = "Loss"
        else:
            raise AssertionError(game)
        long_reason = game["res"].get("reason", "")
        if long_reason:
            long_reason = " due to " + long_reason
            if action_verb == "Loss":
                # FIXME: Find a better way to transfer this piece of info from Rust to this generator.
                long_reason = long_reason.replace("opponent's", "our")
        parts.append(f"<p>{action_verb}{long_reason}.")
        our_time, their_time = game["times"]
        parts.append(
            f" (Executed {our_time} instructions in total; opponent executed {their_time} instructions in total.)</p>"
        )
        parts.append('<div class="game"><table>')
        board = render_game_from_moves(game["moves"])
        # TODO: Individual move timing would be quite interesting.
        # TODO: Some kind of slider that lets you see the gamestate at any point in time?
        for row in board:
            parts.append("<tr>")
            for cell in row:
                state, num_move = cell
                parts.append(f'<td class="c{state}">{num_move}</td>')
            parts.append("</tr>")
        parts.append("</table></div>")
    if limit != len(games_list):
        parts.append(f"<h4>Game types #{limit + 1} through #{len(games_list)}</h4>")
        num_elided = sum(occurrences for occurrences, _ in games_list[limit:])
        parts.append(f"<p>Sorry, the other game types (spanning {num_elided} games) ")
        parts.append("aren't listed to keep this HTML file reasonably small. ")
        parts.append("If you're interested, the other game types in this matchup ")
        parts.append('can be easily extracted from the <a href="results_general.json">')
        parts.append("JSON file</a>. Give it a try!</p>")
    return "".join(parts)


def emit_matchup(vm_one, vm_two):
    matchup = vm_one.matchups[vm_two.name]
    wins, draws, losses = analyze_matchup(matchup)
    context = dict()
    games_by_type = collections.defaultdict(list)
    for game in matchup:
        # TODO: Only need one instance and the count, but I'm lazy.
        # The correct way to do this is probably to change hashable_game's return value to something that can be easily parsed later.
        games_by_type[hashable_game(game)].append(game)
    context["vm_one"] = vm_one.name
    context["vm_two"] = vm_two.name
    context["matchup_filename"] = matchup_filename(vm_one, vm_two)
    context["reverse_matchup_filename"] = matchup_filename(
        vm_two, vm_one
    )  # ignore W1114
    context["matchup_color"] = compute_color(wins, draws, losses)
    context["wins"], context["draws"], context["losses"] = wins, draws, losses
    context["wins_plural"] = "s" if wins != 1 else ""
    context["draws_plural"] = "s" if draws != 1 else ""
    context["losses_plural"] = "es" if losses != 1 else ""
    # DET_TEXT_ONE = "This matchup is deterministic, i.e. both players never used the <code>rnd</code> instruction. Therefore, only a single game was simulated, as all games are identical in this matchup."
    # DET_TEXT_MANY_IDENTICAL = "This matchup could not be determined to be deterministic, even though all games are identical. This can happen, for example, if a player uses the <code>rnd</code> instruction but does not really use the result for some reason."
    # DET_TEXT_MANY_EXTREME = "This matchup is not deterministic. Some games went differently than others, even though the outcome was always the same."
    # DET_TEXT_MANY_VARIED = "This matchup is not deterministic."
    if wins + draws + losses == 1:
        context["determinism_statement"] = DET_TEXT_ONE
    elif len(games_by_type) == 1:
        context["determinism_statement"] = DET_TEXT_MANY_IDENTICAL
    elif (wins == 0) + (draws == 0) + (losses == 0) == 2:
        context["determinism_statement"] = DET_TEXT_MANY_EXTREME
    else:
        context["determinism_statement"] = DET_TEXT_MANY_VARIED
    context["games_plural"] = "" if len(games_by_type) == 1 else "s"
    context["games_list"] = generate_games_list(games_by_type)
    context["last_build"] = TIMESTAMP
    with open("template_single_matchup.html", "r") as fp:
        template = fp.read()
    filename = OUTPUT_DIR + matchup_filename(vm_one, vm_two)
    with open(filename, "w") as fp:
        fp.write(template.format(**context))


def emit_vm_summary(vm, _all_vms):
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
    parts = ['<table class="all-matchups">']
    # Header row
    parts.append("<tr>")
    parts.append("<th></th>")
    for vm in all_vms:
        parts.append(
            f'<th class="defender-th"><div class="defender-outer"><span class="defender-inner">{vm.name}</span></div></th>'
        )
    parts.append("</tr>")
    # Data
    for vm_one in all_vms:
        parts.append("<tr>")
        parts.append(f'<th class="attacker">{vm_one.name}</th>')
        for vm_two in all_vms:
            matchup = vm_one.matchups[vm_two.name]
            wins, draws, losses = analyze_matchup(matchup)
            color = compute_color(wins, draws, losses)
            parts.append(f'<td class="result" style="background-color: {color};">')
            parts.append(f'<a href="{matchup_filename(vm_one, vm_two)}">')
            parts.append(f"{wins}/{draws}/{losses}</a></td>")
        parts.append("</tr>")
    parts.append("</table>")
    return "".join(parts)


def emit_total_summary(all_vms):
    context = dict()
    context["overview_table"] = generate_overview_table(all_vms)
    context["last_build"] = TIMESTAMP
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
        print(
            f"Finished matchup {vm_one.name} vs. {vm_two.name} in {completed_at - started_at:.3f}s."
        )
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
        for _ in range(concurrency):
            tg.create_task(run_matches_from_queue(queue))
        await queue.join()
        # TODO: Can probably start shutting down even earlier, but that's micro-optimization.
        for _ in range(concurrency):
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

    started_at = time.monotonic()
    for vm_one in vms:
        for vm_two in vms:
            emit_matchup(vm_one, vm_two)
    # FIXME: Should order vms by success, but no idea how to measure that.
    # Hopefully that becomes clear later.
    for vm in vms:
        emit_vm_summary(vm, vms)
    emit_total_summary(vms)
    completed_at = time.monotonic()
    print(f"Emitted all files in {completed_at - started_at:.3f}s.")
    print("All done.")


if __name__ == "__main__":
    asyncio.run(run())
