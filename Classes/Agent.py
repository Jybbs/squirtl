from collections         import deque
from DQN                 import DQN
from torch.nn.functional import smooth_l1_loss
from torch.optim         import Adam, lr_scheduler

import random
import torch

class Agent:
    def __init__(self, settings, save_directory):
        self.action_dimensions = len(settings.action_space)
        self.current_step      = 0
        self.dqn               = DQN(self.action_dimensions, settings.state_dimensions).to(self.settings.device)
        self.hyperparameters   = settings.hyperparameters
        self.memory            = deque(maxlen = self.hyperparameters['deque_size'])
        self.optimizer         = Adam(self.dqn.parameters(), lr = self.hyperparameters['learning_rate'])
        self.scheduler         = lr_scheduler.ExponentialLR(self.optimizer, gamma = self.hyperparameters['learning_rate_decay'])
        self.save_directory    = save_directory
        self.settings          = settings
        self.target_dqn        = DQN(self.action_dimensions, settings.state_dimensions).to(self.settings.device)
        
        self.initialize_target_dqn()

    def act(self, state):
        if random.random() < self.hyperparameters['exploration_rate']:
            action_idx = random.randint(0, self.action_dimensions - 1)
        else:
            state      = torch.tensor(state, dtype = torch.float32).unsqueeze(0).to(self.settings.device)
            q_values   = self.dqn(state)
            action_idx = torch.argmax(q_values, dim = 1).item()

        self.update_exploration_rate()
        self.current_step += 1
        return action_idx

    def cache(self, experience):
        experience.to_device(self.settings.device)
        self.memory.append(experience)

    def calculate_loss(self, experiences):
        q_values          = self.dqn(experiences['state']).gather(1, experiences['action'].unsqueeze(1)).squeeze(1)
        next_q_values     = self.target_dqn(experiences['next_state']).max(1)[0]
        expected_q_values = experiences['reward'] + self.hyperparameters['gamma'] * next_q_values * (1 - experiences['done'].float())
        return smooth_l1_loss(q_values, expected_q_values.detach())
    
    def initialize_target_dqn(self):
        self.target_dqn.load_state_dict(self.dqn.state_dict())
        self.target_dqn.eval()

    def learn(self, episode):
        if not self.should_learn():
            return None, None

        self.sync_target_dqn()
        experiences = self.sample_experiences()
        loss = self.calculate_loss(experiences)
        self.optimize(loss)

        if self.should_save(episode):
            self.save(episode + 1)

        return self.dqn(experiences['state']).mean().item(), loss.item()

    def load_model(self, path):
        checkpoint = torch.load(path, map_location = self.settings.device)
        self.dqn.load_state_dict(checkpoint["model"])
        self.hyperparameters['exploration_rate'] = checkpoint["exploration_rate"]

        print(f"Loading model at {path} with exploration rate {self.hyperparameters['exploration_rate']}")

    def optimize(self, loss):
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        self.scheduler.step()

    def sample_experiences(self):
        experiences = random.sample(self.memory, self.hyperparameters['batch_size'])
        return self.stack_experiences(experiences)
    
    def save(self, episode):
        save_path = f"{self.save_directory}/dqn_net_{episode}.chkpt"
        torch.save({"model"            : self.dqn.state_dict(),
                    "exploration_rate" : self.hyperparameters['exploration_rate']}, save_path)
        
        print(f"DQN Net saved to {save_path} at step {self.current_step}")
    
    def should_learn(self):
        return \
        (
            self.current_step >= self.hyperparameters['burnin'] and
            self.current_step % self.hyperparameters['learn_every'] == 0
        )
    
    def should_save(self, episode):
        return (episode + 1) % self.hyperparameters['save_every'] == 0
    
    def stack_experiences(self, experiences):
        tensor_dicts = [e.to_tensor_dict() for e in experiences]
        return {k: torch.stack([td[k] for td in tensor_dicts]) for k in tensor_dicts[0]}

    def sync_target_dqn(self):
        if self.current_step % self.hyperparameters['sync_every'] == 0:
            self.target_dqn.load_state_dict(self.dqn.state_dict())

    def update_exploration_rate(self):
        self.hyperparameters['exploration_rate'] = max \
        (
            self.hyperparameters['exploration_rate_min'],
            self.hyperparameters['exploration_rate'] * self.hyperparameters['exploration_rate_decay']
        )