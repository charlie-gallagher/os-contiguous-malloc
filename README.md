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

Some defaults are:

```py
ticks = 500
stop_making_processes_tick = 500
include_process_bounds = (1, 2)
process_time_bounds = (10, 30)
process_memory_bounds = (10, 50)
sleep_rate = 0.05
```


---

Charlie Gallagher, December 2023