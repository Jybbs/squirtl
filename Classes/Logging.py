import matplotlib.pyplot as plt

from dataclasses import dataclass
from json import dump
from time import time

@dataclass
class Metrics:
    backtracking_actions : int
    effective_actions    : int
    elapsed_time         : float
    episode              : int
    ineffective_actions  : int
    length               : int
    loss                 : float
    q_value              : float
    revisit_actions      : int
    reward               : float
    unexplored_actions   : int

    def to_dict(self):
        return \
        {
            "backtracking_actions" : self.backtracking_actions,
            "effective_actions"    : self.effective_actions,
            "elapsed_time"         : self.elapsed_time,
            "episode"              : self.episode,
            "ineffective_actions"  : self.ineffective_actions,
            "length"               : self.length,
            "loss"                 : self.loss,
            "q_value"              : self.q_value,
            "revisit_actions"      : self.revisit_actions,
            "reward"               : self.reward,
            "unexplored_actions"   : self.unexplored_actions
        }

class Logging:
    def __init__(self, settings):
        self.episode_metrics = []
        self.settings = settings
        self.start_time = time()

    def log_episode(self, metrics: Metrics):
        self.episode_metrics.append(metrics)
        self.print_episode_summary(metrics)
        self.save_metrics()

    def plot_metrics(self):
        _, axes = plt.subplots(3, 3, figsize=(18, 18))
        flattened_axes = axes.flatten()

        metrics_to_plot = ["length", "reward", "loss", "q_value", "effective_actions", 
                           "ineffective_actions", "unexplored_actions", "backtracking_actions", "revisit_actions"]
        for index, metric in enumerate(metrics_to_plot):
            values = [getattr(m, metric) for m in self.episode_metrics]
            flattened_axes[index].plot(values)
            flattened_axes[index].set_title(f"Episode {metric.replace('_', ' ').capitalize()}")
            flattened_axes[index].set_xlabel("Episode")
            flattened_axes[index].set_ylabel(metric.replace('_', ' ').capitalize())
        
        plt.tight_layout()
        plt.savefig(self.settings.metrics_directory / "metrics_plot.png")
        plt.close()

    def print_episode_summary(self, metrics: Metrics):
        print(
            f"Episode {metrics.episode:4d} - "
            f"Length: {metrics.length} - "
            f"Reward: {metrics.reward:.2f} - "
            f"Loss: {metrics.loss:.4f} - "
            f"Q-Value: {metrics.q_value:.4f} - "
            f"Elapsed Time: {metrics.elapsed_time:.2f}s\n"
            f"  Effective: {metrics.effective_actions} - "
            f"Ineffective: {metrics.ineffective_actions} - "
            f"Unexplored: {metrics.unexplored_actions} - "
            f"Backtracking: {metrics.backtracking_actions} - "
            f"Revisit: {metrics.revisit_actions}"
        )

    def save_metrics(self):
        metrics_data = [metric.to_dict() for metric in self.episode_metrics]
        with open(self.settings.metrics_directory / "metrics.json", "w") as file:
            dump(metrics_data, file, indent = 4)