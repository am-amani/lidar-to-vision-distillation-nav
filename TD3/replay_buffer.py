# import random
# from collections import deque

# import numpy as np


# class ReplayBuffer(object):
#     def __init__(self, buffer_size, random_seed=123):
#         """
#         The right side of the deque contains the most recent experiences
#         """
#         self.buffer_size = buffer_size
#         self.count = 0
#         self.buffer = deque()
#         random.seed(random_seed)

#     def add(self, s, a, r, t, s2, camera_data, scan_data):
#         experience = (s, a, r, t, s2, camera_data, scan_data)
#         if self.count < self.buffer_size:
#             self.buffer.append(experience)
#             self.count += 1
#         else:
#             self.buffer.popleft()
#             self.buffer.append(experience)

#     def size(self):
#         return self.count

#     #### sample_batch function not modified#####
#     def sample_batch(self, batch_size):
#         batch = []

#         if self.count < batch_size:
#             batch = random.sample(self.buffer, self.count)
#         else:
#             batch = random.sample(self.buffer, batch_size)

#         s_batch = np.array([_[0] for _ in batch])
#         a_batch = np.array([_[1] for _ in batch])
#         r_batch = np.array([_[2] for _ in batch]).reshape(-1, 1)
#         t_batch = np.array([_[3] for _ in batch]).reshape(-1, 1)
#         s2_batch = np.array([_[4] for _ in batch])
#         camera_data_batch = np.array([_[5] for _ in batch])
#         scan_data_batch = np.array([_[6] for _ in batch])

#         return s_batch, a_batch, r_batch, t_batch, s2_batch, camera_data_batch, scan_data_batch #added by me

#     #### sample_batch function modified to include the previous and next experiences#####
#     # def sample_batch(self, batch_size):
#     #     batch = []
#     #     adjusted_batch_size = batch_size // 3  # Adjusting to try and keep the final batch size close to request

#     #     # Ensure we don't exceed the actual number of available experiences
#     #     num_samples = min(self.count - 2, adjusted_batch_size) if self.count >= 3 else 0

#     #     if num_samples > 0:
#     #         start_points = sorted(random.sample(range(1, self.count - 1), num_samples))
#     #         for start in start_points:
#     #             batch.append(self.buffer[start-1])  # Previous experience
#     #             batch.append(self.buffer[start])    # Selected experience
#     #             batch.append(self.buffer[start+1])  # Next experience

#     #     # Convert each part of experience into separate arrays as before
#     #     s_batch = np.array([_[0] for _ in batch])
#     #     a_batch = np.array([_[1] for _ in batch])
#     #     r_batch = np.array([_[2] for _ in batch]).reshape(-1, 1)
#     #     t_batch = np.array([_[3] for _ in batch]).reshape(-1, 1)
#     #     s2_batch = np.array([_[4] for _ in batch])
#     #     camera_data_batch = np.array([_[5] for _ in batch])
#     #     scan_data_batch = np.array([_[6] for _ in batch])

#     #     return s_batch, a_batch, r_batch, t_batch, s2_batch, camera_data_batch, scan_data_batch

#     # #### sample_batch function modified to include two previous and two next experiences#####
#     # def sample_batch(self, batch_size):
#     #     batch = []
#     #     # Since each selected experience now potentially adds 5 experiences to the batch,
#     #     # adjust the batch size to try and keep the final size close to the requested size.
#     #     adjusted_batch_size = batch_size // 5

#     #     # Ensure we don't select starting points too close to the start or end
#     #     num_samples = min(self.count - 4, adjusted_batch_size) if self.count >= 5 else 0

#     #     if num_samples > 0:
#     #         # Only select starting points that allow for two before and two after experiences
#     #         start_points = sorted(random.sample(range(2, self.count - 2), num_samples))
#     #         # print("start_points:", start_points)
#     #         for start in start_points:
#     #             batch.append(self.buffer[start-2])
#     #             batch.append(self.buffer[start-1])  # Previous experience
#     #             batch.append(self.buffer[start])    # Selected experience
#     #             batch.append(self.buffer[start+1])  # Next experience
#     #             batch.append(self.buffer[start+2])

#     #     # Convert each part of experience into separate arrays as before
#     #     s_batch = np.array([_[0] for _ in batch])
#     #     a_batch = np.array([_[1] for _ in batch])
#     #     r_batch = np.array([_[2] for _ in batch]).reshape(-1, 1)
#     #     t_batch = np.array([_[3] for _ in batch]).reshape(-1, 1)
#     #     s2_batch = np.array([_[4] for _ in batch])
#     #     camera_data_batch = np.array([_[5] for _ in batch])
#     #     scan_data_batch = np.array([_[6] for _ in batch])

#     #     return s_batch, a_batch, r_batch, t_batch, s2_batch, camera_data_batch, scan_data_batch



#     def clear(self):
#         self.buffer.clear()
#         self.count = 0

#     def __add__(self, other):
#         if isinstance(other, ReplayBuffer):
#             new_buffer = ReplayBuffer(max(self.buffer_size, other.buffer_size))
#             new_buffer.buffer = self.buffer + other.buffer
#             new_buffer.count = len(new_buffer.buffer)
#             return new_buffer
#         else:
#             raise ValueError("Can only add a ReplayBuffer to another ReplayBuffer")

import random
from collections import deque
import numpy as np

class ReplayBuffer(object):
    def __init__(self, buffer_size, random_seed=123):
        """
        The right side of the deque contains the most recent experiences
        """
        self.buffer_size = buffer_size
        self.count = 0
        self.buffer = deque()
        random.seed(random_seed)

    def add(self, s, a, r, t, s2, camera_data, scan_data):
        experience = (s, a, r, t, s2, camera_data, scan_data)
        if self.count < self.buffer_size:
            self.buffer.append(experience)
            self.count += 1
        else:
            self.buffer.popleft()
            self.buffer.append(experience)

    def size(self):
        return self.count

    def sample_batch(self, batch_size, start_index=0, end_index=None):
        """
        Samples a batch of experiences from a specified range within the buffer.

        :param batch_size: Size of the sample batch.
        :param start_index: Start index of the range to sample from.
        :param end_index: End index of the range to sample from (inclusive).
        """
        if end_index is None or end_index > self.count:
            end_index = self.count

        if start_index > end_index - batch_size:
            raise ValueError("Start index too high for batch size")

        # Calculate the slice of the buffer to sample from and then sample randomly from it
        batch = random.sample(list(self.buffer)[start_index:end_index], batch_size)

        s_batch = np.array([_[0] for _ in batch])
        a_batch = np.array([_[1] for _ in batch])
        r_batch = np.array([_[2] for _ in batch]).reshape(-1, 1)
        t_batch = np.array([_[3] for _ in batch]).reshape(-1, 1)
        s2_batch = np.array([_[4] for _ in batch])
        camera_data_batch = np.array([_[5] for _ in batch])
        scan_data_batch = np.array([_[6] for _ in batch])

        return s_batch, a_batch, r_batch, t_batch, s2_batch, camera_data_batch, scan_data_batch

    def clear(self):
        self.buffer.clear()
        self.count = 0

    def __add__(self, other):
        if isinstance(other, ReplayBuffer):
            new_buffer = ReplayBuffer(max(self.buffer_size, other.buffer_size))
            new_buffer.buffer = self.buffer + other.buffer
            new_buffer.count = len(new_buffer.buffer)
            return new_buffer
        else:
            raise ValueError("Can only add a ReplayBuffer to another ReplayBuffer")