import unittest
import memory_map_allocation as mem

class MemoryMapTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.memory = mem.Memory()
        return super().setUp()
    
    def test_process_decrement_timer(self):
        my_process = mem.Process(time_remaining=10, memory_required=10, status="ACTIVE")
        start_time = my_process.time_remaining
        my_process.decrement_timer()
        end_time = my_process.time_remaining
        self.assertGreater(start_time, end_time)
    
    def test_process_equality(self):
        my_process = mem.Process(time_remaining=10, memory_required=10, status="INACTIVE", id=99)
        my_other_process = mem.Process(time_remaining=10, memory_required=10, status="INACTIVE", id=99)
        self.assertEqual(my_process, my_other_process)
    
    def test_operating_system_add_process_to_queue(self):
        my_process = mem.Process(time_remaining=10, memory_required=10)
        my_os = mem.OperatingSystem()
        my_os.push(my_process)

        self.assertIs(my_os.process_queue[0], my_process)
        self.assertEqual(my_os.process_queue[0].status, "QUEUED")
    
    def test_operating_system_flush_queue(self):
        my_process = mem.Process(time_remaining=10, memory_required=10)
        my_os = mem.OperatingSystem()
        my_process.start(my_os)
        my_os.flush_queue(memory=self.memory)

        self.assertIs(my_os.process_map[0], my_process)
        self.assertEqual(len(my_os.process_queue), 0)
        self.assertEqual(my_os.process_map[0].status, "ACTIVE")
    
    def test_operating_system_flush_queue_retains_overflow(self):
        # Create 11 processes
        overflowing_process_list = [] # type: list[mem.Process]
        for i in range(1, 12):
            overflowing_process_list.append(mem.Process(time_remaining=10, memory_required=10))

        # Start them all
        my_os = mem.OperatingSystem()
        for process in overflowing_process_list:
            process.start(my_os)

        # Attempt to flush the queue
        my_os.flush_queue(memory=self.memory)

        # Memory should have 10 elements, 1 element remains in the queue
        self.assertEqual(len(my_os.process_map), 10)
        self.assertEqual(len(my_os.process_queue), 1)
    
    def test_operating_system_flush_queue_retains_overflow_and_handles_odd_spacing(self):
        # Create 11 processes
        overflowing_process_list = [] # type: list[mem.Process]
        for i in range(1, 12):
            overflowing_process_list.append(mem.Process(time_remaining=10, memory_required=10))

        # Start them all
        my_os = mem.OperatingSystem()
        self.memory.reserve((0, 7))
        for process in overflowing_process_list:
            process.start(my_os)

        # Attempt to flush the queue
        my_os.flush_queue(memory=self.memory)

        # Memory should have 10 elements, 1 element remains in the queue
        self.assertEqual(len(my_os.process_map), 9)
        self.assertEqual(len(my_os.process_queue), 2)
    
    def test_add_to_queue_updates_process(self):
        my_process = mem.Process(time_remaining=10, memory_required=10)
        my_os = mem.OperatingSystem()
        my_process.start(my_os)

        # Still not started, just queued
        self.assertTrue(my_process.status, "QUEUED")
        self.assertTrue(my_process.id != -1)

    def test_memory_reservation_works_as_expected(self):
        memory = mem.Memory()
        memory.reserve((0, 9))
        expected_output = [True]*10
        expected_output.extend([False]*90)
        self.assertEqual(
            memory.memory_map,
            expected_output
        )
    
    def test_memory_free_works_as_expected(self):
        memory = mem.Memory()
        memory.memory_map = [True]*100
        memory.free((0, 9))
        expected_output = [False]*10
        expected_output.extend([True]*90)
        self.assertEqual(
            memory.memory_map,
            expected_output
        )
    
    def test_memory_available_slots_works(self):
        memory = mem.Memory()
        memory.memory_map = [True]*100
        memory.free((0, 9))
        memory.free((50, 55))
        avail_regions = []
        for region in memory.available_slots():
            avail_regions.append(region)
        expected_regions = [(0, 9), (50, 55)]
        self.assertEqual(
            avail_regions,
            expected_regions
        )
    
    def test_memory_available_slots_works_when_full(self):
        memory = mem.Memory()
        memory.memory_map = [True]*100
        avail_regions = []
        for region in memory.available_slots():
            avail_regions.append(region)
        expected_regions = []
        self.assertEqual(
            avail_regions,
            expected_regions
        )
    
    def test_memory_available_slots_works_when_empty(self):
        memory = mem.Memory()
        memory.memory_map = [False]*100
        avail_regions = []
        for region in memory.available_slots():
            avail_regions.append(region)
        expected_regions = [(0, 99)]
        self.assertEqual(
            avail_regions,
            expected_regions
        )

    def test_free_memory_calculatin(self):
        memory = mem.Memory()
        memory.memory_map = [True]*100
        memory.free((0, 9))
        free_memory = memory.calculate_free_bytes()
        expected_free_memory = 10
        self.assertEqual(free_memory, expected_free_memory)
    
    def test_free_memory_calculatin(self):
        memory = mem.Memory()
        memory.memory_map = [True]*100
        memory.free((0, 9))
        free_memory = memory.calculate_percent_free_bytes()
        expected_free_memory = 0.1
        self.assertEqual(free_memory, expected_free_memory)

