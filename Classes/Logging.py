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
    def __init__(self, settings, debug = False):
        self.action_metrics = {}
        self.settings       = settings
        self.start_time     = time()
        self.debug          = debug

    def log_action(self, episode: int, metrics: Metrics):
        if episode not in self.action_metrics:
            self.action_metrics[episode] = []
        self.action_metrics[episode].append(metrics)
        if self.debug:
            self.print_action_debug(episode, metrics)

    def calculate_episode_metrics(self, episode):
        episode_metrics = self.action_metrics[episode]
        total_actions   = len(episode_metrics)
        
        action_type_counts = Counter(m.action_type for m in episode_metrics)
        
        return \
        {
            "episode"              : episode,
            "total_actions"        : total_actions,
            "total_reward"         : episode_metrics[-1].total_reward,
            "average_loss"         : sum(m.loss         for m in episode_metrics) / total_actions,
            "average_q_value"      : sum(m.q_value      for m in episode_metrics) / total_actions,
            "effective_actions"    : sum(m.is_effective for m in episode_metrics),
            "unexplored_actions"   : action_type_counts["unexplored"],
            "backtracking_actions" : action_type_counts["backtracking"],
            "revisit_actions"      : action_type_counts["revisit"],
            "elapsed_time"         : episode_metrics[-1].elapsed_time - episode_metrics[0].elapsed_time
        }
    
    def print_action_debug(self, episode, metrics: Metrics):
        print(f"Episode {episode:4d} | " +
              f"Action {metrics.action_number:4d} | " +
              f"Button: {metrics.action:10s} | " +
              f"Index: {metrics.action_index:2d} | " +
              f"Type: {metrics.action_type:11s} | " +
              f"Effective: {str(metrics.is_effective):5s} | " +
              f"Reward: {metrics.reward:6.2f} | " +
              f"Total Reward: {metrics.total_reward:8.2f} | " +
              f"Loss: {metrics.loss:8.4f} | " +
              f"Q-Value: {metrics.q_value:8.4f} | " +
              f"Time: {metrics.elapsed_time:6.2f}s")

    def print_episode_summary(self, episode):
        summary = self.calculate_episode_metrics(episode)
        
        print("\nEpisode Summary:")
        print(f"Episode: {summary['episode']:4d} | " +
              f"Actions: {summary['total_actions']:4d} | " +
              f"Total Reward: {summary['total_reward']:8.2f} | " +
              f"Avg Loss: {summary['average_loss']:8.4f} | " +
              f"Avg Q-Value: {summary['average_q_value']:8.4f} | " +
              f"Time: {summary['elapsed_time']:6.2f}s")
        print(f"Effective: {summary['effective_actions']:4d} | " +
              f"Ineffective: {summary['total_actions'] - summary['effective_actions']:4d} | " +
              f"Unexplored: {summary['unexplored_actions']:4d} | " +
              f"Backtracking: {summary['backtracking_actions']:4d} | " +
              f"Revisit: {summary['revisit_actions']:4d}")
        print("-" * 100) # Separator line for legibility

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