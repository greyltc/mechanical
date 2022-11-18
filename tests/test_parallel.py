import unittest
import concurrent.futures
import cadquery as cq
from geometrics.toolbox.cq_serialize import register as register_cq_helper


class ParallelTestCase(unittest.TestCase):
    """parallel testing"""

    @staticmethod
    def make_box(size: float):
        return cq.Workplane("XY").box(size, size, size).findSolid()

    def test_parallel(self):
        n_parallel = 5

        register_cq_helper()

        with concurrent.futures.ProcessPoolExecutor(max_workers=n_parallel) as executor:
            box_sizes = [2]
            fs = [executor.submit(ParallelTestCase.make_box, box_size) for box_size in box_sizes]
            for future in concurrent.futures.as_completed(fs):
                try:
                    rslt = future.result()
                except Exception as e:
                    self.fail(repr(e))
                else:
                    print(f"done with {rslt}")
