import torch

class Experience:
    def __init__(self, state, action, next_state, reward, done):
        self.state      = state
        self.action     = action
        self.next_state = next_state
        self.reward     = reward
        self.done       = done

    def to_tensor(self, device):
        return Experience \
        (
            state      = torch.FloatTensor(self.state).unsqueeze(0).to(device),
            action     = torch.LongTensor([self.action]).to(device),
            next_state = torch.FloatTensor(self.next_state).unsqueeze(0).to(device),
            reward     = torch.FloatTensor([self.reward]).to(device),
            done       = torch.BoolTensor([self.done]).to(device)
        )

    @staticmethod
    def batch_to_tensor(experiences, device):
        return Experience \
        (
            state      = torch.FloatTensor([e.state for e in experiences]).to(device),
            action     = torch.LongTensor([e.action for e in experiences]).to(device),
            next_state = torch.FloatTensor([e.next_state for e in experiences]).to(device),
            reward     = torch.FloatTensor([e.reward for e in experiences]).to(device),
            done       = torch.BoolTensor([e.done for e in experiences]).to(device)
        )

    def __repr__(self):
        return f"Experience(state={self.state.shape}, action={self.action}, " \
               f"next_state={self.next_state.shape}, reward={self.reward}, done={self.done})"