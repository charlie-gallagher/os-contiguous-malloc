import unittest
import virtual_memory.virtual_memory as vm


class VirtualMemoryAddressTestCase(unittest.TestCase):
    def test_virtual_address_translation_works_as_expected(self):
        bits = 8
        page_size = 4
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
        )

    def test_initialize_first_process(self):
        program = vm.Program(
            memory_size=32,
            instructions=list(range(32))
        )
        self.os.start_process(program=program)
        self.assertEqual(len(self.os.process_table), 1)

        process = self.os.process_table[0]
        self.assertEqual(
            process.id,
            0
        )
        self.assertEqual(
            program.instructions,
            process.instructions
        )



