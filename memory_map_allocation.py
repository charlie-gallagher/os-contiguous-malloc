import time
import random
from statistics import mean, median, quantiles
from typing import List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field


class Memory:
    def __init__(self) -> None:
        self.memory_map = [False] * 100

    def reserve(self, memory_slice: Tuple[int, int]):
        self.memory_map[memory_slice[0] : memory_slice[1] + 1] = [True] * (
            memory_slice[1] - memory_slice[0] + 1
        )

    def free(self, memory_slice: Tuple[int, int]):
        self.memory_map[memory_slice[0] : memory_slice[1] + 1] = [False] * (
            memory_slice[1] - memory_slice[0] + 1
        )

    def available_slots(self) -> Union[Tuple[int, int], None]:
        """
        Get next available slice and its size

        A generator.

        Returns the following tuple:
        ::
            ``(start, end)``
        """
        if len(self.memory_map) == 0:
            return None

        i = 0
        while i < len(self.memory_map):
            # Skip all the occupied slots
            while i < len(self.memory_map) and self.memory_map[i] == True:
                i += 1

            if i == len(self.memory_map):
                # This should break the loop
                continue
            # Found an unoccupied slot, mark contiguous unoccupied region
            start = i
            while i < len(self.memory_map) and self.memory_map[i] == False:
                i += 1

            end = i - 1
            i += 1
            yield (start, end)

    def calculate_free_bytes(self, as_bytes=False):
        if as_bytes == True:
            ten_k = 10000
        else:
            ten_k = 1
        return sum([int(not x) for x in self.memory_map if x == False]) * ten_k

    def calculate_percent_free_bytes(self):
        free_bytes = self.calculate_free_bytes()
        total_bytes = len(self.memory_map)
        return float(free_bytes) / float(total_bytes)

    def calculate_n_blocks(self):
        i = 0
        for x in self.available_slots():
            i += 1
        return i


@dataclass(slots=True)
class Process:
    time_remaining: int
    memory_required: int
    memory_slice: Tuple[int, int] = None
    id: int = -1
    status: str = "INACTIVE"

    def __eq__(self, other: object) -> bool:
        return self.id == other.id

    def decrement_timer(self) -> None:
        if self.status == "ACTIVE":
            self.time_remaining -= 1
        else:
            raise Exception("Process is not started")

    def start(self, queue: "OperatingSystem") -> None:
        self.id = queue.push(self)

    def end(self, queue: "OperatingSystem") -> None:
        queue.destroy(self)


@dataclass(eq=False)
class OperatingSystem:
    process_map: List[Process] = field(default_factory=list)
    process_queue: List[Process] = field(default_factory=list)
    id_counter: int = 0

    def push(self, x: Process) -> int:
        self.process_queue.append(x)
        x.status = "QUEUED"
        return self._new_id()

    def _new_id(self) -> int:
        out = self.id_counter
        self.id_counter += 1
        return out

    def flush_queue(self, memory: Memory, strategy: str = "first"):
        if strategy == "first":
            self._flush_queue_first(memory=memory)
        elif strategy == "best":
            self._flush_queue_best(memory=memory)
        elif strategy == "worst":
            self._flush_queue_worst(memory=memory)
        elif strategy == "next":
            raise NotImplementedError()
    
    def _flush_queue_first(self, memory: Memory):
        local_queue = self.process_queue.copy()
        # Loop over processes
        for process in local_queue:
            available_slots = self._get_all_potential_slots(memory=memory, process=process)
            if len(available_slots) > 0:
                first_available = available_slots[0]
                self._reserve_slot(memory=memory, slot=first_available, process=process)

    def _flush_queue_best(self, memory: Memory):
        local_queue = self.process_queue.copy()
        for process in local_queue:
            available_slots = self._get_all_potential_slots(
                memory=memory, process=process
            )
            best_slot = self._get_best_slot(available_slots=available_slots)
            if best_slot is not None:
                self._reserve_slot(memory=memory, slot=best_slot, process=process)

    def _get_best_slot(self, available_slots):
        """
        Get best fit slot

        Assumes ``available_slots`` only contains potential matches.
        """
        if len(available_slots) < 1:
            return None

        slot_sizes = list(set([x["slot_size"] for x in available_slots]))
        best_slot_size = min(slot_sizes)
        best_fit_slots = [
            x for x in available_slots if x["slot_size"] == best_slot_size
        ]
        best_slot = best_fit_slots[0]
        return best_slot

    def _flush_queue_worst(self, memory: Memory):
        local_queue = self.process_queue.copy()
        for process in local_queue:
            available_slots = self._get_all_potential_slots(
                memory=memory, process=process
            )
            worst_slot = self._get_worst_slot(available_slots=available_slots)
            if worst_slot is not None:
                self._reserve_slot(memory=memory, slot=worst_slot, process=process)

    def _get_worst_slot(self, available_slots: List[dict[str, Any]]):
        if len(available_slots) < 1:
            return None

        slot_sizes = list(set([x["slot_size"] for x in available_slots]))
        worst_slot_size = max(slot_sizes)
        worst_fit_slots = [
            x for x in available_slots if x["slot_size"] == worst_slot_size
        ]
        worst_slot = worst_fit_slots[0]
        return worst_slot

    def _get_all_potential_slots(self, memory, process):
        memory_required = process.memory_required
        available_slots = []  # type: List[dict[str, Any]]
        # Find an available slot
        for open_slot in memory.available_slots():
            slot_size = open_slot[1] - open_slot[0] + 1
            if memory_required <= slot_size:
                # TODO: this should probably be an object
                slot_info = {
                    "memory_slice": open_slot,
                    "slot_size": slot_size,
                    "difference": slot_size - memory_required,
                }
                available_slots.append(slot_info)
            else:
                pass
        return available_slots

    def _reserve_slot(self, memory, slot, process):
        memory_slice = (
            slot["memory_slice"][0],
            slot["memory_slice"][0] + process.memory_required - 1,
        )
        memory.reserve(memory_slice)
        process.status = "ACTIVE"
        process.memory_slice = memory_slice
        self.process_map.append(process)
        self.process_queue.remove(process)


    def prune_process_map(self, memory: Memory):
        """
        Prune the process map to get rid of jobs that have finished
        """
        for process in self.process_map:
            process.decrement_timer()
            if process.time_remaining == 0:
                self.process_map.remove(process)
                memory.free(process.memory_slice)


# Main ------------------------------------------------------------------


def main(
    ticks,
    include_process_bounds,
    process_time_bounds,
    process_memory_bounds,
    sleep_rate,
    stop_making_processes_tick,
    strategy,
):
    memory = Memory()
    os = OperatingSystem()
    metric_store = {
        "n_processes": [],
        "n_queue": [],
        "pct_occupied": [],
        "n_blocks": [],
    }

    i = 1
    while i < ticks:
        new_processes = []
        if i < stop_making_processes_tick:
            potential_process = get_random_process(
                process_time_bounds=process_time_bounds,
                process_memory_bounds=process_memory_bounds,
            )
            if (
                random.randint(include_process_bounds[0], include_process_bounds[1])
                == 1
            ):
                new_processes.append(potential_process)
        tick_environment(
            memory,
            os,
            new_processes,
            metric_store=metric_store,
            sleep_rate=sleep_rate,
            strategy=strategy,
        )
        i += 1
    print("")  # Clear remaining text
    print_summary(metric_store)
    return metric_store


def get_random_process(
    process_time_bounds,
    process_memory_bounds,
):
    time_remaining = random.randint(process_time_bounds[0], process_time_bounds[1])
    memory_required = random.randint(process_memory_bounds[0], process_memory_bounds[1])
    return Process(time_remaining=time_remaining, memory_required=memory_required)


def tick_environment(
    memory: Memory,
    os: OperatingSystem,
    new_processes: List[Process],
    metric_store: dict,
    sleep_rate,
    strategy,
):
    print_metrics(os=os, memory=memory)
    store_metrics(os=os, memory=memory, metric_store=metric_store)
    os.prune_process_map(memory=memory)
    os.flush_queue(memory=memory, strategy=strategy)
    for process in new_processes:
        process.start(queue=os)
    time.sleep(sleep_rate)
    return None


def print_metrics(memory, os):
    n_processes = len(os.process_map)
    n_queue = len(os.process_queue)
    pct_occupied = (1 - memory.calculate_percent_free_bytes()) * 100
    n_blocks = memory.calculate_n_blocks()
    print(
        f"Processes: {n_processes}\tQueued processes: {n_queue}\tFree blocks: {n_blocks}\tPercent occupied: {pct_occupied}%                      ",
        end="\r",
    )


def print_summary(metric_store):
    avg_processes = mean(metric_store["n_processes"])
    avg_queue = mean(metric_store["n_queue"])
    avg_occupied = mean(metric_store["pct_occupied"])
    avg_blocks = mean(metric_store["n_blocks"])
    print("AVERAGES")
    print("--------")
    print(
        f"Processes: {avg_processes}\nQueued processes: {avg_queue}\nFree blocks: {avg_blocks}\nPercent occupied: {avg_occupied}%"
    )


def store_metrics(memory, os, metric_store) -> None:
    n_processes = len(os.process_map)
    n_queue = len(os.process_queue)
    pct_occupied = (1 - memory.calculate_percent_free_bytes()) * 100
    n_blocks = memory.calculate_n_blocks()
    metric_store["n_processes"].append(n_processes)
    metric_store["n_queue"].append(n_queue)
    metric_store["pct_occupied"].append(pct_occupied)
    metric_store["n_blocks"].append(n_blocks)
    return None


if __name__ == "__main__":
    ticks = 500
    stop_making_processes_tick = 500
    include_process_bounds = (1, 10)
    process_time_bounds = (5, 60)
    process_memory_bounds = (5, 30)
    sleep_rate = 0.01
    strategy = "first"
    main(
        ticks=ticks,
        include_process_bounds=include_process_bounds,
        process_time_bounds=process_time_bounds,
        process_memory_bounds=process_memory_bounds,
        sleep_rate=sleep_rate,
        stop_making_processes_tick=stop_making_processes_tick,
        strategy=strategy,
    )
