import torch
import torch.nn as nn

from collections              import deque
from torch.jit                import script
from torch.optim              import Adam
from torch.optim.lr_scheduler import ExponentialLR
from torch.utils.data         import Dataset, DataLoader

class Memory(Dataset):
    def __init__(self, capacity):
        self.actions = deque(maxlen = capacity)

    def __len__(self):
        return len(self.actions)

    def __getitem__(self, idx):
        return self.actions[idx]

    def add_action(self, action):
        self.actions.append(action)

    @staticmethod
    def batch_actions(actions, device):
        return \
        {
            'actions'        : torch.tensor([a.action_index for a in actions], dtype = torch.long, device = device),
            'current_frames' : torch.stack([torch.FloatTensor(a.current_frame) for a in actions]).to(device),
            'dones'          : torch.tensor([a.done for a in actions], dtype = torch.bool, device = device),
            'next_frames'    : torch.stack([torch.FloatTensor(a.next_frame) for a in actions]).to(device),
            'rewards'        : torch.tensor([a.reward for a in actions], dtype = torch.float, device = device),
        }

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
            nn.Linear(64 * 10 * 9, 256),
            nn.ReLU(),
            nn.Linear(256, action_count)
        )

    def forward(self, frame):
        return self.network(frame.permute(0, 3, 1, 2))

class Agent(nn.Module):
    def __init__(self, settings):
        super().__init__()
        self.action_space_size = len(settings.action_space)
        self.batch_size        = settings.batch_size
        self.device            = settings.device
        self.loss_function     = nn.HuberLoss()
        self.main_network      = script(DQN(self.action_space_size)).to(self.device)
        self.memory            = Memory(settings.memory_capacity)
        self.optimizer         = Adam(self.main_network.parameters(), lr = settings.learning_rate)
        self.scheduler         = ExponentialLR(self.optimizer, gamma = settings.learning_rate_decay)
        self.settings          = settings
        self.target_network    = script(DQN(self.action_space_size)).to(self.device)
        self.target_network.load_state_dict(self.main_network.state_dict())
        self.target_network.eval()

    def learn(self, action):
        if len(self.memory) < self.batch_size:
            action.loss    = 0
            action.q_value = 0
            return

        dataloader = DataLoader(self.memory, 
                                batch_size  = self.batch_size, 
                                shuffle     = True,
                                pin_memory  = True if self.device == 'mps' else False)

        batched_actions  = Memory.batch_actions(next(iter(dataloader)), self.device)
        current_q_values = self.main_network(batched_actions['current_frames']).gather(1, batched_actions['actions'].unsqueeze(-1))

        with torch.no_grad():
            next_actions    = self.main_network(batched_actions['next_frames']).max(1)[1].unsqueeze(-1)
            next_q_values   = self.target_network(batched_actions['next_frames']).gather(1, next_actions)
            target_q_values = batched_actions['rewards'] + (1 - batched_actions['dones'].float()) * self.settings.discount_factor * next_q_values

        loss = self.loss_function(current_q_values, target_q_values)

        self.optimizer.zero_grad(set_to_none = True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.main_network.parameters(), max_norm = self.settings.max_norm)
        self.optimizer.step()
        self.update_learning_parameters()
        
        action.loss    = loss.item()
        action.q_value = current_q_values.mean().item()

    def load_checkpoint(self, path):
        checkpoint = torch.load(path, map_location = self.device)
        self.settings.exploration_rate = checkpoint['exploration_rate']
        self.main_network = torch.jit.load(checkpoint['model_path'], map_location = self.device)
        self.optimizer.load_state_dict(checkpoint['optimizer'])
        self.scheduler.load_state_dict(checkpoint['scheduler'])

    def save_checkpoint(self, path, total_actions):
        model_path = path.with_suffix('.pt')
        torch.jit.save(self.main_network, model_path)
        torch.save \
        (
            {
                'exploration_rate' : self.settings.exploration_rate,
                'model_path'       : str(model_path),
                'optimizer'        : self.optimizer.state_dict(),
                'scheduler'        : self.scheduler.state_dict(),
                'total_actions'    : total_actions,
            }, 
        path)

    def select_action(self, current_frame):
        if torch.rand(1).item() < self.settings.exploration_rate:
            return torch.randint(self.action_space_size, (1,)).item()
        
        frame_tensor = torch.FloatTensor(current_frame).unsqueeze(0).to(self.device)
        return self.main_network(frame_tensor).argmax().item()

    def store_action(self, action):
        self.memory.add_action(action)

    def update_learning_parameters(self):
        self.scheduler.step()
        self.settings.exploration_rate = max \
        (
            self.settings.exploration_min,
            self.settings.exploration_rate * self.settings.exploration_decay
        )

    def update_target_network(self, total_actions):
        if total_actions % self.settings.target_update_interval == 0:
            self.target_network.load_state_dict(self.main_network.state_dict())