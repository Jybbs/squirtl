import matplotlib.pyplot as plt

from collections import Counter
from dataclasses import dataclass, asdict
from json        import dump
from time        import time

@dataclass
class Metrics:
    action_number : int
    action_index  : int
    action        : str
    is_effective  : bool
    action_type   : str
    reward        : float
    total_reward  : float
    loss          : float
    q_value       : float
    elapsed_time  : float

    def to_dict(self):
        return asdict(self)

class Logging:
    def __init__(self, settings):
        self.action_metrics = {}
        self.settings       = settings
        self.start_time     = time()

    def log_action(self, episode, metrics: Metrics):
        self.action_metrics.setdefault(episode, []).append(metrics)

    def calculate_episode_metrics(self, episode):
        episode_metrics = self.action_metrics[episode]
        total_actions = len(episode_metrics)
        
        action_type_counts = Counter(m.action_type for m in episode_metrics)
        
        return {
            "episode"              : episode,
            "total_actions"        : total_actions,
            "total_reward"         : episode_metrics[-1].total_reward,
            "average_loss"         : sum(m.loss for m in episode_metrics) / total_actions,
            "average_q_value"      : sum(m.q_value for m in episode_metrics) / total_actions,
            "effective_actions"    : sum(m.is_effective for m in episode_metrics),
            "unexplored_actions"   : action_type_counts["unexplored"],
            "backtracking_actions" : action_type_counts["backtracking"],
            "revisit_actions"      : action_type_counts["revisit"],
            "elapsed_time"         : episode_metrics[-1].elapsed_time - episode_metrics[0].elapsed_time
        }

    def print_episode_summary(self, episode):
        summary = self.calculate_episode_metrics(episode)
        print(
            f"Episode {summary['episode']:4d} - "
            f"Actions: {summary['total_actions']} - "
            f"Reward: {summary['total_reward']:.2f} - "
            f"Loss: {summary['average_loss']:.4f} - "
            f"Q-Value: {summary['average_q_value']:.4f} - "
            f"Elapsed Time: {summary['elapsed_time']:.2f}s\n"
            f"  Effective: {summary['effective_actions']} - "
            f"Ineffective: {summary['total_actions'] - summary['effective_actions']} - "
            f"Unexplored: {summary['unexplored_actions']} - "
            f"Backtracking: {summary['backtracking_actions']} - "
            f"Revisit: {summary['revisit_actions']}"
        )

    def plot_metrics(self):
        episode_summaries = [self.calculate_episode_metrics(episode) for episode in sorted(self.action_metrics.keys())]
        
        metrics_to_plot = ["total_actions", "total_reward", "average_loss", "average_q_value", "effective_actions", 
                           "unexplored_actions", "backtracking_actions", "revisit_actions", "elapsed_time"]
        
        fig, axes = plt.subplots(3, 3, figsize = (18, 18))
        for metric, ax in zip(metrics_to_plot, axes.flatten()):
            values = [summary[metric] for summary in episode_summaries]
            ax.plot(values)
            ax.set_title(f"{metric.replace('_', ' ').capitalize()}")
            ax.set_xlabel("Episode")
            ax.set_ylabel(metric.replace('_', ' ').capitalize())
        
        plt.tight_layout()
        plt.savefig(self.settings.metrics_directory / "metrics_plot.png")
        plt.close(fig)

    def save_metrics(self):
        with open(self.settings.metrics_directory / "action_metrics.json", "w") as file:
            dump({episode: [m.to_dict() for m in metrics] for episode, metrics in self.action_metrics.items()}, file, indent=4)

        episode_summaries = {episode: self.calculate_episode_metrics(episode) for episode in self.action_metrics.keys()}
        with open(self.settings.metrics_directory / "episode_summaries.json", "w") as file:
            dump(episode_summaries, file, indent=4)