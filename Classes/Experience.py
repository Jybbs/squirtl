from dataclasses import dataclass
from numpy       import array
from torch       import BoolTensor, FloatTensor, LongTensor

@dataclass
class Experience:
    state      : list
    action     : int
    next_state : list
    reward     : float
    done       : bool

    def __iter__(self):
        return iter((self.state, self.action, self.next_state, self.reward, self.done))

    @staticmethod
    def batch_to_tensor(experiences, device):
        batch = zip(*experiences)
        return Experience \
        (
            state      = FloatTensor(array(next(batch))).to(device),
            action     = LongTensor(array(next(batch))).to(device),
            next_state = FloatTensor(array(next(batch))).to(device),
            reward     = FloatTensor(array(next(batch))).to(device),
            done       = BoolTensor(array(next(batch))).to(device)
        )