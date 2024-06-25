import torch
import torch.nn as nn

from DQN              import DQN
from Experience       import Experience
from torch.optim      import Adam, lr_scheduler
from torch.utils.data import Dataset
from random           import randint, random, sample

class Memory(Dataset):
    def __init__(self, capacity):
        self.capacity        = capacity
        self.experiences     = []
        self.insertion_index = 0

    def __getitem__(self, idx):
        return self.experiences[idx]

    def __len__(self):
        return len(self.experiences)

    def sample_batch(self, batch_size):
        return sample(self.experiences, batch_size)

    def store(self, experience):
        if len(self.experiences) < self.capacity:
            self.experiences.append(None)
        self.experiences[self.insertion_index] = experience
        self.insertion_index = (self.insertion_index + 1) % self.capacity

class Agent(nn.Module):
    def __init__(self, settings):
        super(Agent, self).__init__()
        self.action_space_size = len(settings.action_space)
        self.actions_taken     = 0
        self.batch_size        = settings.batch_size
        self.device            = settings.device
        self.main_network      = DQN(self.action_space_size, settings.state_dimensions).to(self.device)
        self.optimizer         = Adam(self.main_network.parameters(), lr = settings.learning_rate)
        self.replay_memory     = Memory(settings.memory_capacity)
        self.scheduler         = lr_scheduler.ExponentialLR(self.optimizer, gamma = settings.learning_rate_decay)
        self.settings          = settings
        self.target_network    = DQN(self.action_space_size, settings.state_dimensions).to(self.device)

        self.target_network.load_state_dict(self.main_network.state_dict())
        self.target_network.eval()

    def forward(self, state):
        return self.main_network(state)

    def learn_from_experience(self):
        if len(self.replay_memory) < self.batch_size:
            return 0, 0  # Return 0 for both loss and q_value if not learning

        experiences = self.replay_memory.sample_batch(self.batch_size)
        batch = Experience.batch_to_tensor(experiences, self.device)

        current_q_values = self(batch.state).gather(1, batch.action.unsqueeze(1))

        next_q_values  = torch.zeros(self.batch_size, device = self.device)
        non_final_mask = ~batch.done
        next_q_values[non_final_mask] = self.target_network(batch.next_state[non_final_mask]).max(1)[0]

        expected_q_values = batch.reward + (self.settings.discount_factor * next_q_values * (~batch.done).float())

        loss = nn.functional.smooth_l1_loss(current_q_values, expected_q_values.unsqueeze(1))

        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_value_(self.main_network.parameters(), 100)
        self.optimizer.step()

        if self.actions_taken % self.settings.target_update_interval == 0:
            self.target_network.load_state_dict(self.main_network.state_dict())

        self.update_exploration_rate()
        self.scheduler.step()

        return loss.item(), current_q_values.mean().item()

    def load_checkpoint(self, path):
        checkpoint = torch.load(path, map_location = self.device)

        self.main_network.load_state_dict(checkpoint['main_networkac'])
        self.target_network.load_state_dict(checkpoint['target_networkac'])
        self.optimizer.load_state_dict(checkpoint['optimizerac'])
        self.scheduler.load_state_dict(checkpoint['lr_schedulerac'])

        self.settings.exploration_rate = checkpoint['exploration_rate']
        self.actions_taken = checkpoint['actions_taken']

    def save_checkpoint(self, path):
        torch.save \
        (
            {
                'actions_taken'    : self.actions_taken,
                'exploration_rate' : self.settings.exploration_rate,
                'lr_scheduler'     : self.scheduler.state_dict(),
                'main_network'     : self.main_network.state_dict(),
                'optimizer'        : self.optimizer.state_dict(),
                'target_network'   : self.target_network.state_dict()
            }, 
            path
        )

    def select_action(self, state):
        if random() < self.settings.exploration_rate:
            return randint(0, self.action_space_size - 1)
        
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values     = self(state_tensor)
            return q_values.argmax(dim = 1).item()

    def store_experience(self, experience):
        self.replay_memory.store(experience)
        self.actions_taken += 1

    def update_exploration_rate(self):
        self.settings.exploration_rate = max \
        (
            self.settings.exploration_min,
            self.settings.exploration_rate * self.settings.exploration_decay
        )