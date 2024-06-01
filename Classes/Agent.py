import numpy as np
import torch
import torch.nn.functional as F
import torch.optim as optim
from collections import deque
import random
from DQN import DQN

class Agent:
    def __init__(self, state_dim, action_space, save_dir, date, hyperparameters):
        self.state_dim = state_dim
        self.action_space = action_space
        self.save_dir = save_dir
        self.date = date
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.hyperparameters = hyperparameters

        self.dqn = DQN(state_dim, len(action_space)).to(self.device)
        self.target_dqn = DQN(state_dim, len(action_space)).to(self.device)
        self.target_dqn.load_state_dict(self.dqn.state_dict())
        self.target_dqn.eval()

        self.optimizer = optim.Adam(self.dqn.parameters(), lr=hyperparameters.learning_rate)
        self.scheduler = optim.lr_scheduler.ExponentialLR(self.optimizer, gamma=hyperparameters.learning_rate_decay)

        self.memory = deque(maxlen=hyperparameters.deque_size)
        self.curr_step = 0

    def act(self, state):
        if random.random() < self.hyperparameters.exploration_rate:
            action_idx = random.randint(0, len(self.action_space) - 1)
        else:
            state = np.array(state)
            state = torch.tensor(state, dtype=torch.float32).unsqueeze(0).to(self.device)
            q_values = self.dqn(state)
            action_idx = torch.argmax(q_values, dim=1).item()

        self.hyperparameters.exploration_rate *= self.hyperparameters.exploration_rate_decay
        self.hyperparameters.exploration_rate = max(self.hyperparameters.exploration_rate_min, self.hyperparameters.exploration_rate)

        self.curr_step += 1

        return action_idx

    def cache(self, state, next_state, action, reward, done):
        state = np.array(state)
        next_state = np.array(next_state)

        state = torch.tensor(state, dtype=torch.float32).to(self.device)
        next_state = torch.tensor(next_state, dtype=torch.float32).to(self.device)
        action = torch.tensor([action], dtype=torch.long).to(self.device)
        reward = torch.tensor([reward], dtype=torch.float32).to(self.device)
        done = torch.tensor([done], dtype=torch.bool).to(self.device)

        self.memory.append((state, next_state, action, reward, done))

    def recall(self):
        batch = random.sample(self.memory, self.hyperparameters.batch_size)
        state, next_state, action, reward, done = map(torch.stack, zip(*batch))
        return state, next_state, action.squeeze(), reward.squeeze(), done.squeeze()

    def learn(self):
        if self.curr_step % self.hyperparameters.sync_every == 0:
            self.target_dqn.load_state_dict(self.dqn.state_dict())

        if self.curr_step % self.hyperparameters.save_every == 0:
            self.save()

        if self.curr_step < self.hyperparameters.burnin:
            return None, None

        if self.curr_step % self.hyperparameters.learn_every != 0:
            return None, None

        state, next_state, action, reward, done = self.recall()

        q_values = self.dqn(state).gather(1, action.unsqueeze(1)).squeeze(1)
        next_q_values = self.target_dqn(next_state).max(1)[0]
        expected_q_values = reward + self.hyperparameters.gamma * next_q_values * (1 - done.float())

        loss = F.smooth_l1_loss(q_values, expected_q_values.detach())
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        self.scheduler.step()

        return q_values.mean().item(), loss.item()

    def save(self):
        save_path = (self.save_dir / f"dqn_net_{int(self.curr_step // self.hyperparameters.save_every)}.chkpt")
        torch.save(dict(model=self.dqn.state_dict(), exploration_rate=self.hyperparameters.exploration_rate), save_path)
        print(f"DQN Net saved to {save_path} at step {self.curr_step}")

    def load_model(self, path):
        checkpoint = torch.load(path, map_location=self.device)
        self.dqn.load_state_dict(checkpoint["model"])
        self.exploration_rate = checkpoint["exploration_rate"]
        print(f"Loading model at {path} with exploration rate {self.hyperparameters.exploration_rate}")