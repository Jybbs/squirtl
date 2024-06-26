import matplotlib.pyplot as plt
import numpy as np

from collections import Counter, defaultdict
from cv2         import COLOR_RGB2BGR, cvtColor, VideoWriter, VideoWriter_fourcc
from dataclasses import dataclass, asdict
from json        import dump
from time        import time

@dataclass
class Metrics:
    action        : str
    action_number : int
    action_type   : str
    elapsed_time  : float
    is_effective  : bool
    loss          : float
    q_value       : float
    reward        : float
    total_reward  : float

    def to_dict(self):
        return asdict(self)

class Logging:
    def __init__(self, debug, frames, settings):
        self.action_metrics  = defaultdict(list)
        self.current_episode = 1
        self.debug           = debug
        self.frames          = frames
        self.settings        = settings
        self.start_time      = time()

    def calculate_episode_metrics(self, episode):
        episode_metrics    = self.action_metrics[episode]
        total_actions      = len(episode_metrics)
        action_type_counts = Counter(m.action_type for m in episode_metrics)
        
        return {
            "average_loss"         : np.mean([m.loss for m in episode_metrics]),
            "average_q_value"      : np.mean([m.q_value for m in episode_metrics]),
            "backtracking_actions" : action_type_counts["backtrack"],
            "effective_actions"    : sum(m.is_effective for m in episode_metrics),
            "elapsed_time"         : episode_metrics[-1].elapsed_time - episode_metrics[0].elapsed_time,
            "episode"              : episode,
            "new_actions"          : action_type_counts["new"],
            "revisit_actions"      : action_type_counts["revisit"],
            "total_actions"        : total_actions,
            "total_reward"         : episode_metrics[-1].total_reward,
            "wait_actions"         : action_type_counts["wait"],
        }

    def log_action(self, metrics):
        self.action_metrics[self.current_episode].append(metrics)
        if self.debug:
            self.print_debug(self.current_episode, metrics)

    def log_episode(self):
        self.save_episode_video(self.current_episode)
        self.print_episode_summary(self.current_episode)
        metrics = self.calculate_episode_metrics(self.current_episode)
        self.current_episode += 1
        return metrics

    def plot_metrics(self):
        episode_summaries = [self.calculate_episode_metrics(episode) for episode in sorted(self.action_metrics.keys())]
        metrics_to_plot   = ["total_actions", "total_reward", "average_loss", "average_q_value", "effective_actions", 
                             "new_actions", "backtracking_actions", "wait_actions", "elapsed_time"]
        
        fig, axes = plt.subplots(3, 3, figsize = (18, 18))
        for metric, ax in zip(metrics_to_plot, axes.flatten()):
            ax.plot([summary[metric] for summary in episode_summaries])
            ax.set_title(metric.replace('_', ' ').title())
            ax.set_xlabel("Episode")
            ax.set_ylabel(metric.replace('_', ' ').title())
        
        plt.tight_layout()
        plt.savefig(self.settings.metrics_directory / "metrics_plot.png")
        plt.close(fig)

    def print_debug(self, episode, m):
        print(f"Episode {episode:4d} | Action {m.action_number:4d} | Button: {m.action:10s} | "
              f"Type: {m.action_type:14s} | Effective: {str(m.is_effective):5s} | "
              f"Reward: {m.reward:10.2f} | Total Reward: {m.total_reward:10.2f} | "
              f"Loss: {m.loss:8.4f} | Q-Value: {m.q_value:8.4f} | Time: {m.elapsed_time:6.2f}s")

    def print_episode_summary(self, episode):
        s = self.calculate_episode_metrics(episode)
        print("\nEpisode Summary:")
        print(f"Episode: {s['episode']:4d} | Actions: {s['total_actions']:4d} | "
              f"Total Reward: {s['total_reward']:8.2f} | Avg Loss: {s['average_loss']:8.4f} | "
              f"Avg Q-Value: {s['average_q_value']:8.4f} | Time: {s['elapsed_time']:6.2f}s")
        print(f"Effective: {s['effective_actions']:4d} | "
              f"Ineffective: {s['total_actions'] - s['effective_actions']:4d} | "
              f"New: {s['new_actions']:4d} | Backtrack: {s['backtracking_actions']:4d} | "
              f"Wait: {s['wait_actions']:4d}")
        print("-" * 100)

    def save_data(self):
        self.plot_metrics()
        self.save_metrics()

    def save_episode_video(self, episode):
        episode_frames = self.frames.episode_frames
        if not episode_frames:
            return
        
        fourcc       = VideoWriter_fourcc(*'mp4v')
        frame_shape  = episode_frames[0].shape[:2][::-1]
        video_path   = self.settings.video_directory / f"episode_{episode}.mp4"
        video_writer = VideoWriter(str(video_path), fourcc, 60, frame_shape)

        for frame in episode_frames:
            video_writer.write(cvtColor(frame, COLOR_RGB2BGR))

        video_writer.release()

    def save_metrics(self):
        with open(self.settings.metrics_directory / "action_metrics.json", "w") as file:
            dump({episode: [m.to_dict() for m in metrics] for episode, metrics in self.action_metrics.items()}, file, indent = 4)

        episode_summaries = {episode: self.calculate_episode_metrics(episode) for episode in self.action_metrics.keys()}
        with open(self.settings.metrics_directory / "episode_summaries.json", "w") as file:
            dump(episode_summaries, file, indent = 4)