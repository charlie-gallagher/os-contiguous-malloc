# Memory map allocation
## Parameters
Here are the parameters listed in Deitel's Operating Systems book:

> Develop a simulation program to investigate the relative effectiveness of the first fit, best fit, and worst fit storage placement strategies. Your program should measure storage utilization gamma and average job turnaround time for the various storage placement strategies. Assume a real memory system with one megabyte capacity of which 300K is reserved for the operating system new jobs arrive at random intervals between one and ten minutes in multiples of one minute, the size of the jobs are random between 50K and 300K in multiples of 10K, and the durations range from 5 to 60 minutes in multiples of 5 minutes units of 1 minute. Your program should simulate each of the strategies over long enough interval to achieve steady state.

```
1M bytes
300K for OS
New jobs: random intervals, 1:10:1 minutes
Sizes: random sizes, 50K:300K:10K
Durations: random durations, 5:60:5 minutes
```


## Quick Start

Simply run `memory_map_allocation.py`, and you should get a finite program. The parameters can be easily tweaked in the ``main()`` function. The parameters are:

- **ticks** The total number of ticks of the process organizer
- **stop_making_processes_tick** The tick at which to stop creating processes, in case you want to see how quickly the queue clears
- **process_time_bounds** The amount of time a process will take is decided in advance. This parameter tweaks the bounds within which a process will be assigned a time. Measured in ticks.
- **process_memory_bounds** Each process requests a strict memory requirement. This parameter tweaks the bounds within which a process will be assigned a memory requirement. Measured in 10K blocks.
- **sleep_rate** The number of seconds to sleep between ticks.
- **strategy** The memory allocation strategy to use. See section on strategies.
- **memory_size** The number of memory units available.
- **potential_processes_per_tick** The number of processes that might be created for a given tick.

Some defaults are:

```py
ticks = 500
stop_making_processes_tick = 500
include_process_bounds = (1, 2)
process_time_bounds = (10, 30)
process_memory_bounds = (10, 50)
sleep_rate = 0.05
strategy = "first"
potential_processes_per_tick=1
memory_size = 100
```


# Strategies

- **first** Search memory beginning at the start until a memory spot is available that can hold the process.
- **best** Search memory for the smallest available spot that can still hold the process.
- **worst** Search memory for the spot that results in the maximum leftover space in the spot.
- **next** Same as first, but search begins at the point when the most recent process was inserted.

## Visualizations
The below visualizations were created under the following conditions:

```py
main(
    ticks = 250,
    stop_making_processes_tick = 200,
    include_process_bounds = (1, 4),
    process_time_bounds = (5, 25),
    process_memory_bounds = (1, 4),
    sleep_rate = 0.02,
    strategy = "first",
    memory_size = 125,
    potential_processes_per_tick = 4
)
``````

### "First" strategy visualization

![First strategy](https://github.com/charlie-gallagher/os-contiguous-malloc/blob/main/first-strategy.gif)

### "Worst" strategy visualization

![Worst strategy](https://github.com/charlie-gallagher/os-contiguous-malloc/blob/main/worst-strategy.gif)




# Results
I was not able to produce meaningfully different results for any strategy. This makes me wonder if I implemented things correctly. I will review and try again.

# API
You can run a parameterized trial with `memory_map_allocation.main()`. It returns a dictionary of lists containing the data for the trial. While the trial is running it updates with the current state, and it prints a summary at the end.

```py
from memory_map_allocation import main as run_trial
results = run_trial(
    ticks=1000,
    stop_making_processes_tick=1000,
    include_process_bounds=(1, 4),
    process_time_bounds=(5, 30),
    process_memory_bounds=(10, 25),
    sleep_rate=0,
    strategy="best",
    potential_processes_per_tick=1,
    memory_size=100
)

# Processes: 5    Queued processes: 11    Free blocks: 2  Percent occupied: 96.0%                                    
# AVERAGES
# --------
# Processes: 4.56
# Queued processes: 3.69
# Free blocks: 2.35
# Percent occupied: 79.7%
```


## Implementation
Under the hood there are a few key classes.

`Memory` is a memory block, which is a list of boolean values. If a member is true, that part of memory is occupied. This memory block object has no concept of processes, which processes are where, or whether a contiguously occupied region belongs to one large process or many small processes. It is only a simple memory map.

It has methods for reserving and freeing regions of memory, and a generator method for looping over contiguous free regions.

`Process` it is a basic storage container for information about a process. Each process is given a size requirement and a number of time intervals ("ticks") that it will take to complete. They are identified by their `id`, which is given when the process becomes known to the operating system.

`OperatingSystem` is responsible for placing processes in memory and removing processes when they are finished. It is composed of a queue of processes that are waiting to start and a list of running processes. It has various other responsibilities, like decrementing the timers on each active process, giving each queued process an id, and updating the status field of the processes as they move from queue to active to dead.




---

Charlie Gallagher, December 2023