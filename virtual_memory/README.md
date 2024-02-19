# Virtual Memory
Simulating virtual memory shouldn't be too difficult, at least not more difficult than simulating memory block placement. The idea is to have a large address space with a small amount of physical memory, and different processes demand paging in various pages of virtual addresses. In a real system each process has a working set, and I will try to simulate each process having maybe one or more working sets throughout its lifetime.

But of course a simulation isn't that fun unless you can compare different strategies; I am going to be comparing strategies for ejecting one page in favor of some new page, aka page replacement. The strategies I will try to support are:

- Best. Since this is a simulation, I can play god a little bit. That means I can know exactly when some page that is in physical memory will be used next. This page-replacement strategy ejects the page that will be used most in the future.
- LRU. Least recently used, which in operating systems is usually regarded as having too much overhead. But this is python; everything has lots of overhead.
- MRU. Most recently used, which works best when pages are not frequently re-referenced.
- NUR. Not used recently, details on this one below. It should perform nearly as well as LRU.

There are a few support tables I'll need for this. The process needs to know which virtual address block it has been given. The operating system needs to know how to convert a virtual address into a real address. But it's not so simple for the operating system, because it also has to know whether a page referenced in a virtual address is in physical memory or not.

Each process will need a size, which the operating system will use two allocate some virtual address block (a _contiguous_ address block). To simulate a process running, it will simply request some address from within its address block at each tick. I will consider various distributions and strategies for picking an address to simulate a process' working set.

At each tick, the operating system will service all of the processes that it can. Servicing a process means bringing the page that contains the requested address into physical memory. I will probably need some guard rails on this, and how many processes are running at one time, to prevent too much thrashing.

At each tick, some number of new processes will have the potential to be created.

To avoid all the things I already simulated in the memory placement part of this repository, I'm probably going to just pick a larger of virtual address space that it will never be a problem. Worst case scenario I bring in all of that code and extend it, but that's a lot of junk.

# Features

## Processes

- Limited lifetime
- Random memory requirements
- Natural working sets
- Only aware of virtual memory
- Fully deterministic. I want to be able to calculate exactly when in the future a page will be used again.

## Operating system

- Maps all processes into virtual memory
- Maintains page table, which stores metadata about each page
- Maintains page map, which maps pages to physical memory
- Responds to a page fault (a request for a page that is not in memory) by putting the missing page in physical memory using some strategy
- Capable of introspection into process' futures


# Implementation
The operating system takes a static program image and creates a process from it. The program image is only composed of a list of addresses, that will be accessed when the program runs. The program image is a list of relative addresses; in order to load this into virtual memory, the operating system has to do some sort of mapping. According to my book, "the key to the virtual storage concept is disassociating the addresses referenced in a running process from the addresses available in primary storage."

The process has a virtual address space, and "virtual addresses must be mapped into real addresses as a process executes." Active pages are stored in physical memory, and inactive pages are stored on disk. "When a process is to be run, its code and data are brought to the main storage." Dynamic address translation involves converting addresses as the program runs. A virtual address is composed of a block number (page number in my case) and a displacement within that block.

The address has to be a single number that can be converted into an object with a block number and a displacement. In python, I think there are boolean operations but I don't know what control I have over the number of bits in for example an integer. Normally, I would use the first N bits for the block number and the remaining ones for the displacement, and then use a mask to get the block number and the displacement respectively.

Suppose an 8-bit integer, where the first 4 bits are the page and the last 4 bits are the offset.

```python
# 0001 1011, page = 1, offset = 11
addr1 = 0x1b
# 1111 0011, page = 15, offset = 3
addr2 = 0xf3

def get_page(x):
    return (x & 0xf0) >> 4

def get_offset(x):
    return x & 0x0f

for addr in (addr1, addr2):
    print(f"Address: {addr}, Page: {get_page(addr)}, Offset: {get_offset(addr)}")
```

In practice I want to keep the page size small, but allow for a large number of pages. If the average program is 32 units large, I think it makes sense to have 4-units pages, to make things interesting. Naturally this should be parameterized.

```python
from dataclasses import dataclass

@dataclass
class VirtualAddress:
    page: int
    offset: int

def get_virtual_address(x, bits=32, page_size=4):
    offset_mask = (2 ** page_size) - 1
    page_mask = ((2 ** bits) - 1) ^ offset_mask
    page_shift = page_size
    va = VirtualAddress(
        page=(x & page_mask) >> page_shift,
        offset=x & offset_mask
    )
    return va  

# 0001 1011, page = 1, offset = 11
addr1 = 0x1b
# 1111 0011, page = 15, offset = 3
addr2 = 0xf3

for addr in (addr1, addr2):
    virtual_address = get_virtual_address(x=addr, bits=8, page_size=4)
    print(f"Address: {addr}, Page: {virtual_address.page}, Offset: {virtual_address.offset}")
```

A process gets a contiguous range of page addresses, but the way those pages appear in memory can be arbitrary. For now I'm not going to worry about the operating system giving more memory to running processes.

So the steps involved in running a process are:

1. Operating system gives the process an address range, depending on the memory requirements of the program image.
2. The process is queued to be started; none of the processes pages are loaded into physical memory.

At each tick, what should happen?

- Every process progresses one instruction (aka, requests some virtual address)
- The operating system pages in pages as necessary, and keeps count of the swaps per tick
- Some new processes are generated
- Once a process executes its last instruction, it is removed and the pages are freed

## Running a process
When the operating system picks a process off of the runnable queue, it will do something like this:

```python
new_program = q.pop()
new_process = Process(
    virtual_address_range=self.get_virtual_address_range(new_program),
    id=id,
    size=new_program.size
)
add_new_pages_to_page_table(
    pid=new_process.id,
    pages=os.get_pages(new_process) # gets page IDs for each page in address space
)
```

Some design notes:

- Process does not know about pages
- Adding pages to the page table should probably happen when the virtual address range is allocated
- The virtual address range is a straightforward mapping; the virtual addresses are still sequential

## Fetching process instructions, loading into physical memory
To run a process we need to fetch its next instruction and try to get its address from physical memory. If the address is not in physical memory, that is, if the page is not loaded into physical memory, bring that whole page into memory.





---

Charlie Gallagher, February 2024