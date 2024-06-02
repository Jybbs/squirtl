from torch import bool, float32, long, tensor

class Experience:
    def __init__(self, action, done, next_state, reward, state):
        self.action     = tensor([action],   dtype = long)
        self.done       = tensor([done],     dtype = bool)
        self.next_state = tensor(next_state, dtype = float32)
        self.reward     = tensor([reward],   dtype = float32)
        self.state      = tensor(state,      dtype = float32)

    def to_device(self, device):
        self.action     = self.action.to(device)
        self.done       = self.done.to(device)
        self.next_state = self.next_state.to(device)
        self.reward     = self.reward.to(device)
        self.state      = self.state.to(device)

    def to_tensor_dict(self):
        return \
            {
                "action"     : self.action,
                "done"       : self.done,
                "next_state" : self.next_state,
                "reward"     : self.reward,
                "state"      : self.state
            }