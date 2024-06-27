import torch
import torch.nn as nn

from collections     import deque
from DQN             import DQN
from Gymnasium       import Experience
from random          import randint, random, sample
from torch.optim     import Adam, lr_scheduler

class Memory:
    def __init__(self, capacity):
        self.capacity    = capacity
        self.experiences = deque(maxlen = capacity)

    def sample_batch(self, batch_size):
        return sample(self.experiences, min(batch_size, len(self.experiences)))

    def store(self, experience):
        self.experiences.append(experience)

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

    def compute_loss(self, batch):
        current_q_values  = self(batch.state).gather(1, batch.action.unsqueeze(1))
        expected_q_values = batch.reward + (self.settings.discount_factor * self.compute_next_q_values(batch) * (~batch.done).float())
        loss              = nn.functional.smooth_l1_loss(current_q_values, expected_q_values.unsqueeze(1))
        return current_q_values.mean(), loss

    def compute_next_q_values(self, batch):
        next_q_values  = torch.zeros(self.batch_size, device = self.device)
        non_final_mask = ~batch.done
        next_q_values[non_final_mask] = self.target_network(batch.next_state[non_final_mask]).max(1)[0]
        return next_q_values

    def forward(self, state):
        return self.main_network(state)

    def learn_from_experience(self):
        if len(self.replay_memory.experiences) < self.batch_size:
            return 0, 0

        batch       = Experience.batch_to_tensor(self.replay_memory.sample_batch(self.batch_size), self.device)
        q_mean, loss = self.compute_loss(batch)
        self.update_networks(loss)
        
        return loss.item(), q_mean.item()

    def load_checkpoint(self, path):
        checkpoint = torch.load(path, map_location = self.device)

        self.actions_taken             = checkpoint['actions_taken']
        self.main_network.load_state_dict(checkpoint['main_network'])
        self.optimizer.load_state_dict(checkpoint['optimizer'])
        self.scheduler.load_state_dict(checkpoint['lr_scheduler'])
        self.settings.exploration_rate = checkpoint['exploration_rate']
        self.target_network.load_state_dict(checkpoint['target_network'])

    def save_checkpoint(self, path):
        torch.save(
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
            return self(state_tensor).argmax(dim = 1).item()

    def store_experience(self, experience):
        self.actions_taken += 1
        self.replay_memory.store(experience)

    def update_exploration_rate(self):
        self.settings.exploration_rate = max \
        (
            self.settings.exploration_min,
            self.settings.exploration_rate * self.settings.exploration_decay
        )

    def update_networks(self, loss):
        loss.backward()
        nn.utils.clip_grad_value_(self.main_network.parameters(), 100)
        self.optimizer.step()
        self.optimizer.zero_grad()

        if self.actions_taken % self.settings.target_update_interval == 0:
            self.target_network.load_state_dict(self.main_network.state_dict())

        self.scheduler.step()
        self.update_exploration_rate()