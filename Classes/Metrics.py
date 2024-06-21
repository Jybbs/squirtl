import matplotlib.pyplot as plt

from json    import dump
from pathlib import Path
from time    import time

class Metrics:
    def __init__(self, settings, save_directory):
        self.episode_metrics = \
        {
            "elapsed_time" : [],
            "length"       : [],
            "loss"         : [],
            "q_value"      : [],
            "reward"       : []
        }
        self.save_directory = Path(save_directory)
        self.settings       = settings
        self.start_time     = time()

    def log_episode(self, episode_length, episode_reward, episode_loss, episode_q_value):
        elapsed_time = time() - self.start_time
        self.episode_metrics["elapsed_time"].append(elapsed_time)
        self.episode_metrics["length"].append(episode_length)
        self.episode_metrics["loss"].append(episode_loss)
        self.episode_metrics["q_value"].append(episode_q_value)
        self.episode_metrics["reward"].append(episode_reward)

        episode_count = len(self.episode_metrics["length"]) - 1
        self._print_episode_summary(episode_count, episode_length, episode_reward, 
                                    episode_loss, episode_q_value, elapsed_time)

        self._save_metrics()

    def plot_metrics(self):
        _, axes = plt.subplots(2, 2, figsize = (12, 8))
        flattened_axes = axes.flatten()

        metrics_to_plot = ["length", "reward", "loss", "q_value"]
        for index, metric in enumerate(metrics_to_plot):
            flattened_axes[index].plot(self.episode_metrics[metric])
            flattened_axes[index].set_title(f"Episode {metric.capitalize()}")
            flattened_axes[index].set_xlabel("Episode")
            flattened_axes[index].set_ylabel(metric.capitalize())
        
        plt.tight_layout()
        plt.savefig(self.save_directory / "metrics_plot.png")
        plt.close()

    def _print_episode_summary(self, episode, length, reward, loss, q_value, elapsed_time):
        print \
        (
            f"Episode {episode:4d} - "
            f"Length: {length} - "
            f"Reward: {reward:.2f} - "
            f"Loss: {loss:.4f} - "
            f"Q-Value: {q_value:.4f} - "
            f"Elapsed Time: {elapsed_time:.2f}s"
        )

    def _save_metrics(self):
        with open(self.save_directory / "metrics.json", "w") as file:
            dump(self.episode_metrics, file, indent = 4)