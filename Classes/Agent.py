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
        action = self.actions[idx]
        return \
        {
            'action_index'  : torch.tensor(action.action_index, dtype = torch.long),
            'current_frame' : torch.FloatTensor(action.current_frame),
            'next_frame'    : torch.FloatTensor(action.next_frame),
            'reward'        : torch.tensor(action.reward,       dtype = torch.float),
            'done'          : torch.tensor(float(action.done),  dtype = torch.float)
        }

    def add_action(self, action):
        self.actions.append(action)

class DQN(nn.Module):
    def __init__(self, action_count):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(4, 32, kernel_size = 8, stride = 4),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size = 4, stride = 2),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size = 3, stride = 1),
            nn.BatchNorm2d(64),
            nn.ReLU()
        )

        with torch.no_grad():
            sample_input = torch.zeros(1, 4, 144, 160)
            sample_output = self.features(sample_input)
            self.feature_size = sample_output.view(1, -1).size(1)
        
        self.fc = nn.Sequential(
            nn.Linear(self.feature_size, 512),
            nn.ReLU(),
            nn.Linear(512, action_count)
        )

    def forward(self, frame):
        x = frame.permute(0, 3, 1, 2)
        x = self.features(x)
        x = x.view(x.size(0), -1) 
        x = self.fc(x)
        return x

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

        batch = next(iter(dataloader))
        
        current_frames   = batch['current_frame'].to(self.device)
        next_frames      = batch['next_frame'].to(self.device)
        actions          = batch['action_index'].long().to(self.device)
        rewards          = batch['reward'].to(self.device)
        dones            = batch['done'].to(self.device)
        current_q_values = self.main_network(current_frames).gather(1, actions.unsqueeze(-1))

        with torch.no_grad():
            next_q_values   = self.target_network(next_frames).max(1)[0]
            target_q_values = rewards + (1 - dones) * self.settings.discount_factor * next_q_values

        target_q_values = target_q_values.unsqueeze(1)
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