from numpy import array
from torch import BoolTensor, FloatTensor, LongTensor

class Experience:
    def __init__(self, state, action, next_state, reward, done):
        self.state      = state
        self.action     = action
        self.next_state = next_state
        self.reward     = reward
        self.done       = done

    @staticmethod
    def batch_to_tensor(experiences, device):
        batch = Experience(*map(array, zip(*experiences)))
        return Experience \
        (
            state      = FloatTensor(batch.state).to(device),
            action     = LongTensor(batch.action).to(device),
            next_state = FloatTensor(batch.next_state).to(device),
            reward     = FloatTensor(batch.reward).to(device),
            done       = BoolTensor(batch.done).to(device)
        )