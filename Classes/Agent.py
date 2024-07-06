import torch
import torch.nn as nn

from torch.jit                import script
from torch.optim              import Adam
from torch.optim.lr_scheduler import ExponentialLR
from torch.utils.data         import Dataset, DataLoader

class Memory(Dataset):
    def __init__(self, capacity):
        self.capacity = capacity
        self.memory   = []
        self.position = 0

    def push(self, state, action, next_state, reward, done):
        if len(self.memory) < self.capacity:
            self.memory.append(None)
        self.memory[self.position] = (state, action, next_state, reward, done)
        self.position = (self.position + 1) % self.capacity

    def __len__(self):
        return len(self.memory)

    def __getitem__(self, idx):
        return self.memory[idx]

@script
class DQN(nn.Module):
    def __init__(self, action_count):
        super().__init__()
        self.network = nn.Sequential \
        (
            nn.Conv2d(4, 32, kernel_size = 8, stride = 4),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size = 4, stride = 2),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.Flatten(),
            nn.LazyLinear(256),
            nn.ReLU(),
            nn.Linear(256, action_count)
        )

    def forward(self, state):
        return self.network(state.permute(0, 3, 1, 2))

class Agent(nn.Module):
    def __init__(self, settings):
        super().__init__()
        self.settings          = settings
        self.action_space_size = len(settings.action_space)
        self.actions_taken     = 0
        self.batch_size        = settings.batch_size
        self.device            = settings.device

        # Network initialization
        self.main_network   = DQN(self.action_space_size).to(self.device)
        self.target_network = DQN(self.action_space_size).to(self.device)
        self.target_network.load_state_dict(self.main_network.state_dict())
        self.target_network.eval()

        # Optimizer and loss function
        self.optimizer     = Adam(self.main_network.parameters(), lr = settings.learning_rate)
        self.loss_function = nn.HuberLoss()
        self.scheduler     = ExponentialLR(self.optimizer, gamma = settings.learning_rate_decay)

        # Memory and data loading
        self.memory     = Memory(settings.memory_capacity)
        self.dataloader = DataLoader(self.memory, 
                                     batch_size  = self.batch_size, 
                                     shuffle     = True,
                                     pin_memory  = True if self.device == 'mps' else False)
    
    def learn_from_experience(self):
        if len(self.memory) < self.batch_size:
            return 0, 0

        batch = next(iter(self.dataloader))
        states, actions, next_states, rewards, dones = [b.to(self.device) for b in batch]

        current_q_values = self.main_network(states).gather(1, actions.unsqueeze(-1))

        with torch.no_grad():
            next_actions    = self.main_network(next_states).max(1)[1].unsqueeze(-1)
            next_q_values   = self.target_network(next_states).gather(1, next_actions)
            target_q_values = rewards + (1 - dones.float()) * self.settings.discount_factor * next_q_values

        loss = self.loss_function(current_q_values, target_q_values)

        self.optimizer.zero_grad(set_to_none = True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.main_network.parameters(), max_norm = self.settings.max_norm)
        self.optimizer.step()
        self.update_target_network()
        self.update_learning_parameters(loss)
        
        return loss.item(), current_q_values.mean().item()

    def load_checkpoint(self, path):
        checkpoint = torch.load(path, map_location = self.device)
        self.actions_taken             = checkpoint['actions_taken']
        self.settings.exploration_rate = checkpoint['exploration_rate']
        self.main_network              = torch.jit.load(checkpoint['model_path'], map_location = self.device)
        self.optimizer.load_state_dict(checkpoint['optimizer'])
        self.scheduler.load_state_dict(checkpoint['scheduler'])

    def save_checkpoint(self, path):
        model_path = path.with_suffix('.pt')
        torch.jit.save(self.main_network, model_path)
        torch.save \
        (
            {
                'actions_taken'    : self.actions_taken,
                'exploration_rate' : self.settings.exploration_rate,
                'model_path'       : str(model_path),
                'optimizer'        : self.optimizer.state_dict(),
                'scheduler'        : self.scheduler.state_dict(),
            }, 
        path)

    @torch.no_grad()
    def select_action(self, state):
        if torch.rand(1).item() < self.settings.exploration_rate:
            return torch.randint(self.action_space_size, (1,)).item()
        
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        return self.main_network(state_tensor).argmax().item()

    def store_experience(self, state, action, next_state, reward, done):
        self.actions_taken += 1
        self.memory.push \
        (
            torch.FloatTensor(state),
            torch.tensor(action),
            torch.FloatTensor(next_state),
            torch.tensor(reward),
            torch.tensor(done)
        )

    def update_learning_parameters(self):
        self.scheduler.step()
        self.settings.exploration_rate = max \
        (
            self.settings.exploration_min,
            self.settings.exploration_rate * self.settings.exploration_decay
        )

    def update_target_network(self):
        if self.actions_taken % self.settings.target_update_interval == 0:
            self.target_network.load_state_dict(self.main_network.state_dict())