
# Copyright 2020 MONAI Consortium
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.



from monai.data.streams.datastream import DataStream, BatchStream, OrderType
from multiprocessing.pool import ThreadPool
import numpy as np


class AugmentStream(DataStream):
    """Applies the given augmentations in generate() to each given value and yields the results."""

    def __init__(self, src, augments=[]):
        super().__init__(src)
        self.augments = list(augments)

    def generate(self, val):
        yield self.applyAugments(val)

    def applyAugments(self, arrays):
        """Applies augments to the data tuple `arrays` and returns the result."""
        toTuple = isinstance(arrays, np.ndarray)
        arrays = (arrays,) if toTuple else arrays

        for aug in self.augments:
            arrays = aug(*arrays)

        return arrays[0] if toTuple else arrays


class ThreadAugmentStream(BatchStream, AugmentStream):
    """
    Applies the given augmentations to each value from the source using multiple threads. Resulting batches are yielded
    synchronously so the client must wait for the threads to complete. 
    """

    def __init__(self, src, batchSize, numThreads=None, augments=[], orderType=OrderType.LINEAR):
        BatchStream.__init__(self, src, batchSize, False, orderType)
        AugmentStream.__init__(self, src, augments)
        self.numThreads = numThreads
        self.pool = None

    def _augmentThreadFunc(self, index, arrays):
        self.buffer[index] = self.applyAugments(arrays)

    def applyAugmentsThreaded(self):
        self.pool.starmap(self._augmentThreadFunc, enumerate(self.buffer))

    def bufferFull(self):
        self.applyAugmentsThreaded()
        super().bufferFull()

    def __iter__(self):
        with ThreadPool(self.numThreads) as self.pool:
            for srcVal in super().__iter__():
                yield srcVal
