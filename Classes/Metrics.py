import matplotlib.pyplot as plt

from json    import dump
from os      import makedirs
from pathlib import Path
from time    import time

class Metrics:
    def __init__(self, settings):
        self.episode_metrics = \
        {
            "elapsed_time"         : [],
            "length"               : [],
            "loss"                 : [],
            "q_value"              : [],
            "reward"               : [],
            "effective_actions"    : [],
            "ineffective_actions"  : [],
            "unexplored_actions"   : [],
            "backtracking_actions" : [],
            "revisit_actions"      : []
        }
        self.save_directory = Path(settings.save_directory)
        self.settings = settings
        self.start_time = time()
        
        makedirs(self.save_directory, exist_ok = True) # Ensure the save directory exists

    def log_episode(self, episode_length, episode_reward, episode_loss, episode_q_value, 
                    effective_actions, ineffective_actions, unexplored_actions, 
                    backtracking_actions, revisit_actions):
        elapsed_time = time() - self.start_time
        self.episode_metrics["elapsed_time"].append(elapsed_time)
        self.episode_metrics["length"].append(episode_length)
        self.episode_metrics["loss"].append(episode_loss)
        self.episode_metrics["q_value"].append(episode_q_value)
        self.episode_metrics["reward"].append(episode_reward)
        self.episode_metrics["effective_actions"].append(effective_actions)
        self.episode_metrics["ineffective_actions"].append(ineffective_actions)
        self.episode_metrics["unexplored_actions"].append(unexplored_actions)
        self.episode_metrics["backtracking_actions"].append(backtracking_actions)
        self.episode_metrics["revisit_actions"].append(revisit_actions)

        episode_count = len(self.episode_metrics["length"]) - 1
        self.print_episode_summary(episode_count, episode_length, episode_reward, 
                                   episode_loss, episode_q_value, elapsed_time,
                                   effective_actions, ineffective_actions, unexplored_actions, 
                                   backtracking_actions, revisit_actions)

        self._save_metrics()

    def plot_metrics(self):
        _, axes = plt.subplots(3, 3, figsize = (18, 18))
        flattened_axes = axes.flatten()

        metrics_to_plot = ["length", "reward", "loss", "q_value", "effective_actions", 
                           "ineffective_actions", "unexplored_actions", "backtracking_actions", "revisit_actions"]
        for index, metric in enumerate(metrics_to_plot):
            flattened_axes[index].plot(self.episode_metrics[metric])
            flattened_axes[index].set_title(f"Episode {metric.replace('_', ' ').capitalize()}")
            flattened_axes[index].set_xlabel("Episode")
            flattened_axes[index].set_ylabel(metric.replace('_', ' ').capitalize())
        
        plt.tight_layout()
        plt.savefig(self.save_directory / "metrics/metrics_plot.png")
        plt.close()

    def print_episode_summary(self, episode, length, reward, loss, q_value, elapsed_time,
                              effective_actions, ineffective_actions, unexplored_actions, 
                              backtracking_actions, revisit_actions):
        print(
            f"Episode {episode:4d} - "
            f"Length: {length} - "
            f"Reward: {reward:.2f} - "
            f"Loss: {loss:.4f} - "
            f"Q-Value: {q_value:.4f} - "
            f"Elapsed Time: {elapsed_time:.2f}s\n"
            f"  Effective: {effective_actions} - "
            f"Ineffective: {ineffective_actions} - "
            f"Unexplored: {unexplored_actions} - "
            f"Backtracking: {backtracking_actions} - "
            f"Revisit: {revisit_actions}"
        )

    def _save_metrics(self):
        with open(self.save_directory / "metrics/metrics.json", "w") as file:
            dump(self.episode_metrics, file, indent = 4)