from time import time
from torch.utils.tensorboard import SummaryWriter

class Metrics:
    def __init__(self, settings, save_directory):
        self.episode_count = 0
        self.start_time    = time()
        self.writer        = SummaryWriter(log_dir=save_directory)

    def close_writer(self):
        self.writer.close()

    def log_episode(self, episode_length, total_reward, average_loss, average_q_value):
        elapsed_time = time() - self.start_time
        self.writer.add_scalar('Episode Length',  episode_length,  self.episode_count)
        self.writer.add_scalar('Total Reward',    total_reward,    self.episode_count)
        self.writer.add_scalar('Average Loss',    average_loss,    self.episode_count)
        self.writer.add_scalar('Average Q-value', average_q_value, self.episode_count)
        self.writer.add_scalar('Elapsed Time',    elapsed_time,    self.episode_count)
        
        print \
        (
            f"Episode {self.episode_count:4d}\n"
            f"Length:  {episode_length}\n"
            f"Reward:  {total_reward:.2f}\n"
            f"Loss:    {average_loss:.4f}\n"
            f"Q-Value: {average_q_value:.4f}\n"
            f"Time:    {elapsed_time:.2f}s\n"
        )
        
        self.episode_count += 1