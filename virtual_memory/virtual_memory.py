from typing import Tuple, Any, Union, List, Optional
from dataclasses import dataclass, InitVar, field
from collections import deque


# LIBRARY CODE --------------
class VirtualMemoryExceededError(Exception):
    pass


PAGE_SIZE = 4
VIRTUAL_MEMORY_PAGES = 256


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

    def __str__(self) -> str:
        return f"<Memory: {self.print_memory_map()}>"

    def __repr__(self) -> str:
        return f"<Memory: {self.print_memory_map()}>"

    def _update_slice_with(self, memory_slice, value) -> None:
        self.memory_map[memory_slice.start : memory_slice.end + 1] = [value] * (
            memory_slice.length
        )

    def reserve(self, memory_slice: MemorySlice) -> None:
        self._update_slice_with(memory_slice=memory_slice, value=True)

    def free(self, memory_slice: MemorySlice) -> None:
        self._update_slice_with(memory_slice=memory_slice, value=False)

    def available_slots(self) -> Any:
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

    def print_memory_map(self) -> str:
        occupied_char = "█"
        free_char = "░"
        printed_map = []  # type: List[str]
        for x in self.memory_map:
            if x == True:
                printed_map.append(occupied_char)
            else:
                printed_map.append(free_char)
        return "".join(printed_map)

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


@dataclass
class Page:
    id: int
    size: int
    accessed: bool = False
    modified: bool = False


@dataclass
class VirtualMemory:
    pages: List[Page]
    free_list: List[int] = field(init=False)
    occupied_list: List[int] = field(init=False)

    def __post_init__(self):
        self.free_list = [x.id for x in self.pages]
        self.occupied_list = []

    def reserve_pages(self, n: int) -> List[Page]:
        # TODO: Only allocate contiguous pages
        allocated_page_ids = self.free_list[:n]
        allocated_pages = [x for x in self.pages if x.id in allocated_page_ids]
        return allocated_pages


@dataclass(slots=True)
class VirtualAddress:
    page: int
    offset: int


def to_virtual_address(x: int, bits=32, page_size=4):
    max_address = (2**bits) - 1
    if x > max_address:
        raise VirtualMemoryExceededError(
            f"Address {x} exceeds virtual memory bounds ({bits} bits, max address {max_address})"
        )

    offset_mask = (2**page_size) - 1
    page_mask = (max_address) ^ offset_mask
    page_shift = page_size
    va = VirtualAddress(page=(x & page_mask) >> page_shift, offset=x & offset_mask)
    return va

def to_process_address(x: VirtualAddress, page_size=4):
    page_shift = page_size
    proc_addr = (x.page << page_shift) + x.offset
    return proc_addr


@dataclass
class Program:
    memory_size: int
    instructions: List[int]


@dataclass
class Process:
    # Should each process translate its address space into pages?
    id: int
    size: int
    instructions: List[int]


@dataclass
class OperatingSystem:
    virtual_memory: VirtualMemory
    physical_memory: Memory
    page_size: int
    process_table: List[Process] = field(init=False, default_factory=list)
    page_table: List[Page] = field(init=False, default_factory=list)
    next_process_id: int = field(init=False, default=0)

    def _get_new_process_id(self):
        out = self.next_process_id
        self.next_process_id += 1
        return out

    def start_process(self, program: Process):
        process = self.init_process(program=program)
        self.process_table.append(process)

    def init_process(self, program: Program):
        """Map to virtual memory, create Process object"""
        initial_virtual_address = self.reserve_virtual_memory(size=program.memory_size)
        process_instructions = [x + initial_virtual_address for x in program.instructions]
        # TODO: process ids
        process_id = self._get_new_process_id()
        process = Process(
            id=process_id,
            size=program.memory_size,
            instructions=process_instructions
        )
        return process
    
    def reserve_virtual_memory(self, size: int):
        """Gets a block of virtual memory of size ``size`` and returns starting address"""
        required_pages = (size // self.page_size) + 1
        reserved_pages = self.virtual_memory.reserve_pages(n=required_pages)
        first_page_address = VirtualAddress(page=reserved_pages[0].id, offset=0)
        starting_address = to_process_address(x=first_page_address, page_size=self.page_size)
        return starting_address


    def reserve_process_pages(self, size):
        required_pages = (size // self.page_size) + 1
        free_pages = self.virtual_memory.free_list
        try:
            pages_to_reserve = free_pages[:required_pages]
        except IndexError:
            raise VirtualMemoryExceededError("Insufficient virtual memory")
        del free_pages[:2]
        self.virtual_memory.occupied_list.extend(pages_to_reserve)
        return pages_to_reserve


# RUNTIME FUNCTIONALITY ----------
def main():
    pass


def _generate_virtual_memory(pages, page_size):
    return VirtualMemory([Page(id=x, size=page_size) for x in range(pages)])


if __name__ == "__main__":
    os = OperatingSystem(
        virtual_memory=_generate_virtual_memory(
            pages=VIRTUAL_MEMORY_PAGES, page_size=PAGE_SIZE
        ),
        physical_memory=Memory(size=50),
        page_size=PAGE_SIZE,
    )