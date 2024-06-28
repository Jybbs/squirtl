import json
import matplotlib.pyplot as plt
import numpy as np

from collections import Counter, defaultdict
from cv2         import COLOR_RGB2BGR, cvtColor, VideoWriter, VideoWriter_fourcc
from dataclasses import dataclass, asdict
from pandas      import DataFrame
from seaborn     import regplot, scatterplot
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
    def __init__(self, debug, frames, settings, start_episode):
        self.action_metrics  = defaultdict(list)
        self.current_episode = start_episode
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
    
    def get_frames_for_video(self, frames, filename):
        if not frames:
            return
        
        fourcc       = VideoWriter_fourcc(*'mp4v')
        frame_shape  = frames[0].shape[:2][::-1]
        video_path   = self.settings.video_directory / filename
        video_writer = VideoWriter(str(video_path), fourcc, 60, frame_shape)

        for frame in frames:
            video_writer.write(cvtColor(frame, COLOR_RGB2BGR))

        video_writer.release()

    def load_all_episode_metrics(self):
        all_metrics = []
        for episode in range(1, self.current_episode + 1):
            metrics_path = self.settings.metrics_directory / f"episode_{episode}_metrics.json"
            if metrics_path.exists():
                with open(metrics_path, 'r') as file:
                    all_metrics.append(json.load(file))
        return all_metrics

    def log_action(self, metrics):
        self.action_metrics[self.current_episode].append(metrics)
        if self.debug:
            self.print_debug(self.current_episode, metrics)

    def log_episode(self):
        metrics = self.calculate_episode_metrics(self.current_episode)
        self.save_episode_data(self.current_episode, metrics)
        self.save_episode_videos(self.current_episode)
        self.print_episode_summary(self.current_episode)
        self.plot_metrics()
        self.current_episode += 1
        return metrics

    def plot_metrics(self):
        self.setup_plot_params()
        episode_summaries = self.load_all_episode_metrics()
        df = DataFrame(episode_summaries)
        
        metrics = ["total_actions", "total_reward", "average_loss", "average_q_value",
                   "effective_actions", "new_actions", "backtracking_actions", "wait_actions", "elapsed_time"]
        
        fig, axes = plt.subplots(3, 3, figsize = (15, 10), sharex = True)
        colors = plt.cm.viridis(np.linspace(0.1, 1, len(metrics)))
        
        for metric, ax, color in zip(metrics, axes.flatten(), colors):
            regplot(x = 'episode', y = metric, data = df, ax = ax, scatter = False, 
                    lowess = True, line_kws = {'color': color})
            scatterplot(x = 'episode', y = metric, data = df, ax = ax, alpha = 0.3, color = color)
            
            ax.set_title(metric.replace('_', ' ').title())
            ax.set_ylabel('')
            ax.set_xlabel('Episode' if ax == axes[2, 1] else '')
            
            if ax.get_ylim()[0] <= 0 <= ax.get_ylim()[1]:
                ax.axhline(y = 0, color = 'white', linestyle = '--', linewidth = 1, alpha = 0.5)
        
        plt.tight_layout()
        plt.savefig(self.settings.metrics_directory / f"plot_episode_{self.current_episode}.png")
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

    def save_episode_data(self, episode, metrics):
        metrics_path = self.settings.metrics_directory / f"episode_{episode}_metrics.json"
        with open(metrics_path, 'w') as file:
            json.dump(metrics, file, indent = 4)

        actions_path = self.settings.metrics_directory / f"episode_{episode}_actions.json"
        with open(actions_path, 'w') as file:
            json.dump([m.to_dict() for m in self.action_metrics[episode]], file, indent = 4)

    def save_episode_videos(self, episode):
        self.get_frames_for_video(self.frames.get_episode_frames(), f"episode_{episode}.mp4")

    def setup_plot_params(self):
        plt.rcParams.update({# Axes parameters                            # Tick parameters
                             'axes.facecolor'     : '.05',                'xtick.labelsize'    : 8,
                             'axes.grid'          : True,                 'xtick.color'        : '1',
                             'axes.labelcolor'    : 'white',              'xtick.major.size'   : 0,
                             'axes.spines.left'   : False,                'ytick.labelsize'    : 8,
                             'axes.spines.right'  : False,                'ytick.color'        : '1',
                             'axes.spines.top'    : False,                'ytick.major.size'   : 0,
                             'axes.labelsize'     : 10,
                             'axes.labelweight'   : 'bold',               # Figure parameters
                             'axes.titlesize'     : 13,                   'figure.facecolor'   : 'black',
                             'axes.titleweight'   : 'bold',               'figure.figsize'     : (15, 10),
                             'axes.labelpad'      : 15,                   'figure.autolayout'  : True,
                             'axes.titlepad'      : 15,

                             # Font and text parameters                   # Legend parameters
                             'font.family'        : 'DejaVu Sans Mono',   'legend.facecolor'   : '0.3',
                             'font.size'          : 8,                    'legend.edgecolor'   : '0.3',
                             'font.style'         : 'normal',             'legend.borderpad'   : 0.75,
                             'text.color'         : 'white',              'legend.framealpha'  : '0.5',

                             # Grid parameters
                             'grid.linestyle'     : ':',
                             'grid.color'         : '0.2'})