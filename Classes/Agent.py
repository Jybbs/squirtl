import torch
import torch.nn as nn

from torch.jit                import script
from torch.nn.functional      import smooth_l1_loss
from torch.optim              import Adam
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.utils.data         import ReplayMemory

@script
class DQN(nn.Module):
    def __init__(self, action_count):
        super().__init__()
        self.network = nn.Sequential(
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
        self.action_space_size = len(settings.action_space)
        self.actions_taken     = 0
        self.batch_size        = settings.batch_size
        self.device            = settings.device
        self.experience_fields = settings.experience_fields
        self.main_network      = DQN(self.action_space_size).to(self.device)
        self.target_network    = DQN(self.action_space_size).to(self.device)
        self.optimizer         = Adam(self.main_network.parameters(), lr = settings.learning_rate)
        self.scheduler         = ReduceLROnPlateau(self.optimizer, 
                                                   mode     = 'min', 
                                                   factor   = settings.scheduler_factor, 
                                                   patience = settings.scheduler_patience)
        self.replay_memory     = ReplayMemory(settings.memory_capacity)
        self.settings          = settings

        self.target_network.load_state_dict(self.main_network.state_dict())
        self.target_network.eval()

    def learn_from_experience(self):
        if len(self.replay_memory) < self.batch_size:
            return 0, 0

        batch = self.prepare_batch()
        loss, q_values = self.update_network(batch)
        self.update_target_network()
        self.update_learning_parameters(loss)
        
        return loss.item(), q_values.mean().item()

    def load_checkpoint(self, path):
        checkpoint = torch.load(path, map_location = self.device)
        self.actions_taken = checkpoint['actions_taken']
        self.settings.exploration_rate = checkpoint['exploration_rate']
        self.load_state_dict(checkpoint['model'])
        self.optimizer.load_state_dict(checkpoint['optimizer'])
        self.scheduler.load_state_dict(checkpoint['scheduler'])

    def prepare_batch(self):
        transitions = self.replay_memory.sample(self.batch_size)
        return {f : torch.cat([getattr(t, f) for t in transitions]).to(self.device)
                for f in self.experience_fields}

    def save_checkpoint(self, path):
        torch.save \
        (
            {
                'actions_taken'    : self.actions_taken,
                'exploration_rate' : self.settings.exploration_rate,
                'model'            : self.state_dict(),
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
        experience = \
        {
            'state'      : torch.FloatTensor(state),
            'action'     : torch.tensor([action]),
            'next_state' : torch.FloatTensor(next_state),
            'reward'     : torch.tensor([reward]),
            'done'       : torch.tensor([done])
        }
        self.replay_memory.push(*[experience[f] for f in self.experience_fields])

    def update_learning_parameters(self, loss):
        self.scheduler.step(loss)
        self.settings.exploration_rate = max \
        (
            self.settings.exploration_min,
            self.settings.exploration_rate * self.settings.exploration_decay
        )

    def update_network(self, batch):
        current_q_values = self.main_network(batch['state']).gather(1, batch['action'])
        target_q_values = self.compute_target_values(batch)
        loss = smooth_l1_loss(current_q_values, target_q_values)
        
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_value_(self.main_network.parameters(), 100)
        self.optimizer.step()

        return loss, current_q_values

    def update_target_network(self):
        if self.actions_taken % self.settings.target_update_interval == 0:
            self.target_network.load_state_dict(self.main_network.state_dict())

    @torch.no_grad()
    def compute_target_values(self, batch):
        next_q_values = self.target_network(batch['next_state']).max(1)[0]
        return \
        (
            batch['reward'] + 
            (1 - batch['done'].float())   * 
            self.settings.discount_factor * 
            next_q_values
        ).unsqueeze(1)