import unittest
import virtual_memory.virtual_memory as vm


class VirtualMemoryAddressTestCase(unittest.TestCase):
    def test_virtual_address_translation_works_as_expected(self):
        bits = 8
        page_size = 2**4  # 4 bits
        # 0001 1011, page = 1, offset = 11
        addr1 = 0x1B
        # 1111 0011, page = 15, offset = 3
        addr2 = 0xF3

        expected_addr1 = vm.VirtualAddress(page=1, offset=11)
        expected_addr2 = vm.VirtualAddress(page=15, offset=3)

        self.assertEqual(
            vm.to_virtual_address(x=addr1, bits=bits, page_size=page_size),
            expected_addr1,
        )
        self.assertEqual(
            vm.to_virtual_address(x=addr2, bits=bits, page_size=page_size),
            expected_addr2,
        )

    def test_virtual_address_translation_throws_for_bounds(self):
        bits = 8
        page_size = 4
        addr1 = 0xFFFF

        with self.assertRaises(vm.VirtualMemoryExceededError):
            vm.to_virtual_address(x=addr1, bits=bits, page_size=page_size)


class OperatingSystemTestCase(unittest.TestCase):
    def setUp(self):
        self.os = vm.OperatingSystem(
            virtual_memory=vm._generate_virtual_memory(
                pages=vm.VIRTUAL_MEMORY_PAGES, page_size=vm.PAGE_SIZE
            ),
            physical_memory=vm.Memory(size=50),
            page_size=vm.PAGE_SIZE,
            n_virtual_memory_pages=vm.VIRTUAL_MEMORY_PAGES,
        )

    def test_initialize_first_process(self):
        program = vm.Program(memory_size=32, instructions=list(range(32)))
        self.os.start_process(program=program)
        self.assertEqual(len(self.os.process_table), 1)

        process = self.os.process_table[0]
        self.assertEqual(process.id, 0)
        self.assertEqual(program.instructions, process.instructions)

    def test_initialize_two_processes(self):
        program1 = vm.Program(memory_size=32, instructions=list(range(32)))
        program2 = vm.Program(memory_size=32, instructions=list(range(32)))
        self.os.start_process(program=program1)
        self.os.start_process(program=program2)

        self.assertEqual(len(self.os.process_table), 2)

        process1 = self.os.process_table[0]
        process2 = self.os.process_table[1]

        self.assertEqual(process1.id, 0)
        self.assertEqual(process2.id, 1)
        self.assertEqual(program1.instructions, process1.instructions)
        self.assertEqual(
            process2.instructions, [x + process1.size for x in program2.instructions]
        )

    def test_teardown_first_process(self):
        program = vm.Program(memory_size=32, instructions=list(range(32)))
        pid = self.os.start_process(program=program)
        self.os.close_process(pid=pid)

        self.assertEqual(len(self.os.process_table), 0)
        self.assertEqual(self.os.virtual_memory.occupied_list, [])
        self.assertEqual(
            self.os.virtual_memory.free_list,
            list(range(8, vm.VIRTUAL_MEMORY_PAGES)) + list(range(0, 8)),
        )

    def test_teardown_second_process(self):
        program1 = vm.Program(memory_size=32, instructions=list(range(32)))
        program2 = vm.Program(memory_size=32, instructions=list(range(32)))
        pid1 = self.os.start_process(program=program1)
        pid2 = self.os.start_process(program=program2)
        self.os.close_process(pid=pid2)

        self.assertEqual(len(self.os.process_table), 1)
        self.assertEqual(self.os.virtual_memory.occupied_list, list(range(8)))
        self.assertEqual(
            self.os.virtual_memory.free_list,
            list(range(16, vm.VIRTUAL_MEMORY_PAGES)) + list(range(8, 16)),
        )

    def test_translate_virtual_address_throws_page_fault(self):
        program = vm.Program(memory_size=32, instructions=list(range(32)))
        pid = self.os.start_process(program=program)
        first_instruction_address = self.os.process_table[
            self.os.process_table.index(pid)
        ].instructions[0]

        with self.assertRaises(vm.PageFaultError):
            self.os.translate_address(first_instruction_address)

    def test_page_can_be_loaded_into_physical_memory(self):
        program = vm.Program(memory_size=32, instructions=list(range(32)))
        pid = self.os.start_process(program=program)
        process = self.os.process_table[self.os.process_table.index(pid)]
        first_virtual_address = self.os.get_virtual_address(process.instructions[0])
        self.os.load_page(first_virtual_address.page)
        # Test: address translation does not throw PageFaultError
        first_physical_address = self.os.translate_address(process.instructions[0])
        second_physical_address = self.os.translate_address(process.instructions[1])
        self.assertEqual(first_physical_address + 1, second_physical_address)
        with self.assertRaises(vm.PageFaultError):
            # Next page not loaded yet
            self.os.translate_address(process.instructions[4])

    def test_page_cannot_be_loaded_into_physical_memory_twice(self):
        program = vm.Program(memory_size=32, instructions=list(range(32)))
        pid = self.os.start_process(program=program)
        process = self.os.process_table[self.os.process_table.index(pid)]
        first_virtual_address = self.os.get_virtual_address(process.instructions[0])
        self.os.load_page(first_virtual_address.page)
        with self.assertRaises(vm.PageAllocationError):
            self.os.load_page(first_virtual_address.page)

    def test_two_pages_can_be_loaded_into_physical_memory(self):
        program = vm.Program(memory_size=32, instructions=list(range(32)))
        pid = self.os.start_process(program=program)
        process = self.os.process_table[self.os.process_table.index(pid)]
        first_virtual_address = self.os.get_virtual_address(process.instructions[0])
        fifth_virtual_address = self.os.get_virtual_address(process.instructions[4])
        self.os.load_page(first_virtual_address.page)
        self.os.load_page(fifth_virtual_address.page)
        # Test: address translation does not throw PageFaultError
        first_physical_address = self.os.translate_address(process.instructions[0])
        second_physical_address = self.os.translate_address(process.instructions[1])
        self.assertEqual(first_physical_address + 1, second_physical_address)
        fifth_physical_address = self.os.translate_address(process.instructions[4])

    def test_page_can_be_deallocated(self):
        program = vm.Program(memory_size=32, instructions=list(range(32)))
        pid = self.os.start_process(program=program)
        process = self.os.process_table[self.os.process_table.index(pid)]
        first_virtual_address = self.os.get_virtual_address(process.instructions[0])
        self.os.load_page(first_virtual_address.page)

        # Test
        self.os.unlink_page(first_virtual_address.page)
        with self.assertRaises(vm.PageFaultError):
            self.os.translate_address(process.instructions[0])
    
    def test_deallocation_of_two_pages(self):
        program = vm.Program(memory_size=32, instructions=list(range(32)))
        pid = self.os.start_process(program=program)
        process = self.os.process_table[self.os.process_table.index(pid)]
        first_virtual_address = self.os.get_virtual_address(process.instructions[0])
        fifth_virtual_address = self.os.get_virtual_address(process.instructions[4])
        self.os.load_page(first_virtual_address.page)
        self.os.translate_address(process.instructions[0])
        self.os.unlink_page(first_virtual_address.page)

        self.os.load_page(fifth_virtual_address.page)
        self.os.translate_address(process.instructions[5])
        self.os.unlink_page(fifth_virtual_address.page)

        with self.assertRaises(vm.PageFaultError):
            self.os.translate_address(process.instructions[0])
        with self.assertRaises(vm.PageFaultError):
            self.os.translate_address(process.instructions[5])

