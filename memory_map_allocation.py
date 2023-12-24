import time
import random
from statistics import mean
from typing import List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field, InitVar


@dataclass(slots=True)
class MemorySlice:
    """
    A contiguous block of memory
    ============================

    Convenience methods for dealing with slices of memory.

    Members
    -------
    ``start``
        The first index in the slice
    ``end``
        The last index in the slice
    ``length``
        The number of memory blocks available

    Methods
    -------
    ``sub_slice``
        Returns a new memory slice with a length less than or equal to the
        original.
    """

    memory_slice: InitVar[Tuple[int, int]]
    _memory_slice: Tuple[int, int] = field(init=False)

    def __post_init__(self, memory_slice):
        self._memory_slice = memory_slice

    @property
    def start(self):
        return self._memory_slice[0]

    @property
    def end(self):
        return self._memory_slice[1]

    @property
    def length(self):
        return self.end - self.start + 1

    def sub_slice(self, length):
        """
        Get a sub-slice of the current slice

        Processes only need to reserve those blocks that they need, so this
        returns a sub slice of a given length from a larger slice.
        """
        assert length <= self.length
        return MemorySlice((self.start, self.start + length - 1))


class Memory:
    """
    A simple memory map
    ===================

    Contains a memory map that tells which blocks of memory are available and
    occupied.

    Members
    -------
    ``memory_map``
        A boolean array.

    Methods
    -------
    ``reserve``
        Reserve a block of memory
    ``free``
        Free a block of memory
    ``available_slots``
        A generator that returns contiguous slices of free memory
    ``calculate_free_bytes``
        Returns the number of free blocks of memory
    ``calculate_percent_free_bytes``
        Returns the percentage of memory that is free as a float between 0 and 1
    ``calculate_n_blocks``
        Returns the number of contiguous free blocks (not memory units)
    """

    def __init__(self, size=100) -> None:
        self.memory_map = [False] * size

    def _update_slice_with(self, memory_slice, value) -> None:
        self.memory_map[memory_slice.start : memory_slice.end + 1] = [value] * (
            memory_slice.length
        )

    def reserve(self, memory_slice: MemorySlice) -> None:
        self._update_slice_with(memory_slice=memory_slice, value=True)

    def free(self, memory_slice: MemorySlice) -> None:
        self._update_slice_with(memory_slice=memory_slice, value=False)

    def available_slots(self) -> Union[MemorySlice, None]:
        """
        Get next available slice and its size

        A generator.

        Returns a ``MemorySlice``.
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
            yield MemorySlice(memory_slice=(start, end))
    
    def print_memory_map(self) -> None:
        occupied_char = "█"
        free_char = "░"
        printed_map = [] # type: List[str]
        for x in self.memory_map:
            if x == True:
                printed_map.append(occupied_char)
            else:
                printed_map.append(free_char)
        print(''.join(printed_map), end = '\r')



    def calculate_free_bytes(self, as_bytes: bool = False) -> int:
        if as_bytes == True:
            ten_k = 10000
        else:
            ten_k = 1
        return sum([int(not x) for x in self.memory_map if x == False]) * ten_k

    def calculate_percent_free_bytes(self) -> float:
        free_bytes = self.calculate_free_bytes()
        total_bytes = len(self.memory_map)
        return float(free_bytes) / float(total_bytes)

    def calculate_n_blocks(self) -> int:
        i = 0
        for x in self.available_slots():
            i += 1
        return i


@dataclass(slots=True)
class Process:
    """
    Process abstraction
    ===================
    Stores fundamental and identifying characteristics of a process.

    Members
    -------
    ``time_remaining``
        Initially, the number of ticks the process will take to complete. The
        operating system decrements this to keep track of which processes are
        still running and which have finished.
    ``memory_required``
        The number of memory units that the process will occupy.
    ``memory_slice``
        The memory slice the process occupies once it's placed by the
        operating system.
    ``id``
        A unique identifier assigned by the operating system.
    ``status``
        One of "INACTIVE", "QUEUED", "ACTIVE", or "DEFERRED". Also updated by the
        operating system.
    ``priority``
        A priority level, between 0 and 15. (15 is lowest priority.)
    ``queue_age``
        Time spent in the queue.

    Methods
    -------
    ``decrement_timer``
        Used to decrement the timer
    ``start``
        Enter the operating systems queue, and receive an ID.
    """

    time_remaining: int
    memory_required: int
    memory_slice: Optional[MemorySlice] = None
    id: int = -1
    status: str = "INACTIVE"
    priority: int = 15
    queue_age: int = 0

    def __eq__(self, other: object) -> bool:
        return self.id == other.id

    def decrement_timer(self) -> None:
        if self.status == "ACTIVE":
            self.time_remaining -= 1
        else:
            raise Exception("Process is not started")

    def start(self, queue: "OperatingSystem") -> None:
        self.id = queue.push(self)

    def bump_priority(self) -> int:
        if self.priority > 0:
            self.priority -= 1


@dataclass(eq=False)
class OperatingSystem:
    """
    Operating system abstraction
    ----------------------------
    A process queue and a process map, with methods for allocating processes
    into memory.

    Members
    -------
    ``process_map``
        The list of active processes
    ``process_queue``
        The list of processes that want to begin
    ``id_counter``
        Used for generating process ids

    Methods
    -------
    ``push``
        Add a process to the queue
    ``flush_queue``
        Attempt to allocate resources for each process and add them to the
        process map.
    ``prune_process_map``
        Remove processes that have finished from the process map and free their
        resources.
    """

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

    def flush_queue(self, memory: Memory, strategy: str = "first") -> None:
        """
        Empty the queue
        ================================================================
        Attempt to empty the queue by allocating memory for each process.

        ``memory``
            A ``Memory`` object to use for allocating processes.
        ``strategy``
            Which strategy to use to place processes. One of "first", "best",
            "worst", or "next".
        """
        # Bump queue ages
        for p in self.process_queue:
            if p.status != "DEFERRED":
                p.queue_age += 1

        self.process_queue.sort(key=lambda x: x.priority)

        # Give absolute priority to queued processes with priority 0
        if any([x.priority == 0 for x in self.process_queue]):
            self._defer_low_priority_processes()
        else:
            self._enable_all_priority_processes()

        if strategy == "first":
            self._flush_queue_first(memory=memory)
        elif strategy == "best":
            self._flush_queue_best(memory=memory)
        elif strategy == "worst":
            self._flush_queue_worst(memory=memory)
        elif strategy == "next":
            raise NotImplementedError()

        # Bump priority of any remaining processes
        for qp in self.process_queue:
            if qp.status != "DEFERRED":
                qp.bump_priority()


    def _defer_low_priority_processes(self):
        for qp in self.process_queue:
            if qp.priority > 0:
                qp.status = "DEFERRED"

    def _enable_all_priority_processes(self):
        for qp in self.process_queue:
            qp.status = "QUEUED"


    def _flush_queue_first(self, memory: Memory) -> None:
        local_queue = self.process_queue.copy()
        for process in local_queue:
            if process.status == "DEFERRED":
                continue
            available_slots = self._get_all_potential_slots(
                memory=memory, memory_required=process.memory_required
            )
            if len(available_slots) > 0:
                first_available = available_slots[0]
                self._reserve_slot(memory=memory, slot=first_available, process=process)

    def _flush_queue_best(self, memory: Memory) -> None:
        local_queue = self.process_queue.copy()
        for process in local_queue:
            if process.status == "DEFERRED":
                continue
            available_slots = self._get_all_potential_slots(
                memory=memory, memory_required=process.memory_required
            )
            best_slot = self._get_best_slot(available_slots=available_slots)
            if best_slot is not None:
                self._reserve_slot(memory=memory, slot=best_slot, process=process)

    def _get_best_slot(self, available_slots: List[MemorySlice]) -> MemorySlice:
        """
        Get best fit slot

        Assumes ``available_slots`` only contains potential matches.
        """
        if len(available_slots) < 1:
            return None

        slot_sizes = list(set([x.length for x in available_slots]))
        best_slot_size = min(slot_sizes)
        best_fit_slots = [x for x in available_slots if x.length == best_slot_size]
        best_slot = best_fit_slots[0]
        return best_slot

    def _flush_queue_worst(self, memory: Memory) -> None:
        local_queue = self.process_queue.copy()
        for process in local_queue:
            if process.status == "DEFERRED":
                continue
            available_slots = self._get_all_potential_slots(
                memory=memory, memory_required=process.memory_required
            )
            worst_slot = self._get_worst_slot(available_slots=available_slots)
            if worst_slot is not None:
                self._reserve_slot(memory=memory, slot=worst_slot, process=process)

    def _get_worst_slot(self, available_slots: List[dict[str, Any]]) -> MemorySlice:
        if len(available_slots) < 1:
            return None

        slot_sizes = list(set([x.length for x in available_slots]))
        worst_slot_size = max(slot_sizes)
        worst_fit_slots = [x for x in available_slots if x.length == worst_slot_size]
        worst_slot = worst_fit_slots[0]
        return worst_slot

    def _get_all_potential_slots(
        self, memory: Memory, memory_required: int
    ) -> List[MemorySlice]:
        available_slots = []  # type: List[MemorySlice]
        for open_slot in memory.available_slots():
            if memory_required <= open_slot.length:
                available_slots.append(open_slot)
            else:
                pass
        return available_slots

    def _reserve_slot(
        self, memory: Memory, slot: MemorySlice, process: Process
    ) -> None:
        memory_slice = slot.sub_slice(length=process.memory_required)
        memory.reserve(memory_slice)
        process.status = "ACTIVE"
        process.memory_slice = memory_slice
        self.process_map.append(process)
        self.process_queue.remove(process)

    def prune_process_map(self, memory: Memory) -> None:
        """
        Prune the process map
        =================
        Remove processes that have finished.
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
    potential_processes_per_tick,
    memory_size=50,
):
    memory = Memory(size=memory_size)
    os = OperatingSystem()
    metric_store = {
        "n_processes": [],
        "n_queue": [],
        "pct_occupied": [],
        "n_blocks": [],
        "max_queue_age": []
    }

    i = 1
    while i < ticks:
        new_processes = get_new_processes(
            tick=i,
            process_time_bounds=process_time_bounds,
            process_memory_bounds=process_memory_bounds,
            stop_making_processes_tick=stop_making_processes_tick,
            include_process_bounds=include_process_bounds,
            potential_processes_per_tick=potential_processes_per_tick
        )
        tick_environment(
            memory,
            os,
            new_processes,
            metric_store=metric_store,
            sleep_rate=sleep_rate,
            strategy=strategy,
        )
        i += 1
    print_summary(metric_store, n_processes=os.id_counter)
    return metric_store


def get_new_processes(
    tick,
    process_time_bounds: Tuple[int, int],
    process_memory_bounds: Tuple[int, int],
    stop_making_processes_tick: int,
    include_process_bounds: Tuple[int, int],
    potential_processes_per_tick: int = 5
) -> List[Process]:
    new_processes = []
    if tick < stop_making_processes_tick:
        for i in range(potential_processes_per_tick):
            potential_process = get_random_process(
                process_time_bounds=process_time_bounds,
                process_memory_bounds=process_memory_bounds,
            )
            if random.randint(include_process_bounds[0], include_process_bounds[1]) == 1:
                new_processes.append(potential_process)
    return new_processes


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


def print_metrics(memory: Memory, os: OperatingSystem):
    n_processes = len(os.process_map)
    n_queue = len(os.process_queue)
    pct_occupied = (1 - memory.calculate_percent_free_bytes()) * 100
    n_blocks = memory.calculate_n_blocks()
    if len(os.process_queue) > 0:
        avg_priority_in_queue = min([x.priority for x in os.process_queue])
        max_queue_age = max([x.queue_age for x in os.process_queue])
    else:
        avg_priority_in_queue = -1
        max_queue_age = -1


    memory.print_memory_map()
    print("")
    print(
            f"Processes: {n_processes:3d}\tQueued processes: {n_queue:3d}\tFree blocks: {n_blocks:2d}\tMax queue age: {max_queue_age:3d}   ",
        end="\r",
    )
    print("\033[A\033[A")


def print_summary(metric_store: dict[str, Any], n_processes: int):
    print("")
    print("")
    print("")  # Move to next line, don't overwrite anything
    avg_processes = mean(metric_store["n_processes"])
    avg_queue = mean(metric_store["n_queue"])
    avg_blocks = mean(metric_store["n_blocks"])
    n_processes = n_processes
    avg_occupied = mean(metric_store["pct_occupied"])
    avg_max_queue_age = mean(metric_store["max_queue_age"])
    print("AVERAGES")
    print("--------")
    print(
            f"Processes: {avg_processes}\nQueued processes: {avg_queue}\nFree blocks: {avg_blocks}\nNumber of processes created: {n_processes}\nPercent occupied: {avg_occupied}%\nAvg maximum queue age: {avg_max_queue_age}"
    )


def store_metrics(memory, os, metric_store) -> None:
    n_processes = len(os.process_map)
    n_queue = len(os.process_queue)
    pct_occupied = (1 - memory.calculate_percent_free_bytes()) * 100
    n_blocks = memory.calculate_n_blocks()
    if len(os.process_queue) > 0:
        avg_priority_in_queue = min([x.priority for x in os.process_queue])
        max_queue_age = max([x.queue_age for x in os.process_queue])
    else:
        avg_priority_in_queue = None
        max_queue_age = 0
    metric_store["n_processes"].append(n_processes)
    metric_store["n_queue"].append(n_queue)
    metric_store["pct_occupied"].append(pct_occupied)
    metric_store["n_blocks"].append(n_blocks)
    metric_store["max_queue_age"].append(max_queue_age)
    return None


if __name__ == "__main__":
    ticks = 10000
    stop_making_processes_tick = 9000
    include_process_bounds = (1, 4)
    process_time_bounds = (5, 25)
    process_memory_bounds = (1, 4)
    sleep_rate = 0.1
    strategy = "best"
    memory_size = 100
    potential_processes_per_tick = 10
    main(
        ticks=ticks,
        include_process_bounds=include_process_bounds,
        process_time_bounds=process_time_bounds,
        process_memory_bounds=process_memory_bounds,
        sleep_rate=sleep_rate,
        stop_making_processes_tick=stop_making_processes_tick,
        strategy=strategy,
        memory_size=memory_size,
        potential_processes_per_tick=potential_processes_per_tick
    )
