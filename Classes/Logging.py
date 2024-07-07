import json
import matplotlib.pyplot as plt
import numpy             as np

from alive_progress import alive_bar
from cv2            import COLOR_RGB2BGR, VideoWriter, VideoWriter_fourcc, cvtColor
from pandas         import DataFrame
from seaborn        import regplot, scatterplot

class Logging:
    def __init__(self, debug, frames, settings):
        self.debug           = debug
        self.frames          = frames
        self.settings        = settings
        self.current_episode = None
        self.progress_bar    = None
        self.episode_metrics = []

    def get_episode_metrics(self):
        e = self.current_episode
        return {
            "average_loss"         : e.average_loss,
            "average_q_value"      : e.average_q_value,
            "backtracking_actions" : e.action_type_counts["backtrack"],
            "effective_actions"    : e.effective_actions,
            "elapsed_time"         : e.elapsed_time,
            "episode"              : e.episode_number,
            "new_actions"          : e.action_type_counts["new"],
            "revisit_actions"      : e.action_type_counts["revisit"],
            "total_actions"        : e.total_actions,
            "total_reward"         : e.total_reward,
            "wait_actions"         : e.action_type_counts["wait"],
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

    def log_action(self, action):
        if self.debug:
            self.print_debug(action)
            self.update_progress_bar()

    def log_episode(self):
        metrics = self.get_episode_metrics()
        self.episode_metrics.append(metrics)
        self.save_episode_data(metrics)
        self.save_episode_video()
        self.print_episode_summary(metrics)
        self.plot_metrics()
        return metrics

    def plot_metrics(self):
        self.setup_plot_params()
        df = DataFrame(self.episode_metrics)
        
        values = \
        [
            "average_loss", 
            "average_q_value", 
            "backtracking_actions", 
            "effective_actions", 
            "elapsed_time", 
            "new_actions", 
            "total_actions", 
            "total_reward", 
            "wait_actions"
        ]
        
        fig, axes = plt.subplots(3, 3, figsize = (15, 10), sharex = True)
        colors    = plt.cm.viridis(np.linspace(0.1, 1, len(values)))
        
        for metric, ax, color in zip(values, axes.flatten(), colors):
            regplot(x = 'episode', y = metric, data = df, ax = ax, scatter = False, 
                    lowess = True, line_kws = {'color': color})
            scatterplot(x = 'episode', y = metric, data = df, ax = ax, alpha = 0.3, color = color)
            
            ax.set_title(metric.replace('_', ' ').title())
            ax.set_ylabel('')
            ax.set_xlabel('Episode' if ax == axes[2, 1] else '')
            
            if ax.get_ylim()[0] <= 0 <= ax.get_ylim()[1]:
                ax.axhline(y = 0, color = 'white', linestyle = '--', linewidth = 1, alpha = 0.5)
        
        plt.tight_layout()
        plt.savefig(self.settings.metrics_directory / f"plot_episode_{self.current_episode.episode_number}.png")
        plt.close(fig)

    def print_debug(self, action):
        e = self.current_episode
        print(f"Episode {e.episode_number:4d} | Action {e.total_actions:4d} | Button: {action.action_name:10s} | "
              f"Type: {action.action_type:14s} | Effective: {str(action.is_effective):5s} | "
              f"Reward: {action.reward:10.2f} | Total Reward: {e.total_reward:10.2f} | "
              f"Loss: {action.loss:8.4f} | Q-Value: {action.q_value:8.4f} | "
              f"Time: {e.elapsed_time:6.2f}s")

    def print_episode_summary(self, metrics):
        print("\nEpisode Summary:")
        print(f"Episode: {metrics['episode']:4d} | Actions: {metrics['total_actions']:4d} | "
              f"Total Reward: {metrics['total_reward']:8.2f} | Avg Loss: {metrics['average_loss']:8.4f} | "
              f"Avg Q-Value: {metrics['average_q_value']:8.4f} | Time: {metrics['elapsed_time']:6.2f}s")
        print(f"Effective: {metrics['effective_actions']:4d} | "
              f"Ineffective: {metrics['total_actions'] - metrics['effective_actions']:4d} | "
              f"New: {metrics['new_actions']:4d} | Backtrack: {metrics['backtracking_actions']:4d} | "
              f"Wait: {metrics['wait_actions']:4d}")
        print("-" * 100)

    def save_episode_data(self, metrics):
        episode_number = self.current_episode.episode_number
        metrics_path = self.settings.metrics_directory / f"episode_{episode_number}_metrics.json"
        with open(metrics_path, 'w') as file:
            json.dump(metrics, file, indent = 4)

        actions_path = self.settings.metrics_directory / f"episode_{episode_number}_actions.json"
        with open(actions_path, 'w') as file:
            json.dump([vars(a) for a in self.current_episode.actions], file, indent = 4)

    def save_episode_video(self):
        episode_number = self.current_episode.episode_number
        self.get_frames_for_video(self.frames.get_episode_frames(), f"episode_{episode_number}.mp4")

    def setup_plot_params(self):
        plt.rcParams.update \
        (
            {
                # Axes parameters                            # Tick parameters
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
                'grid.color'         : '0.2'
            }
        )

    def start_episode(self, episode):
        self.current_episode = episode
        if self.debug:
            self.progress_bar = alive_bar(self.settings.MAX_ACTIONS)

    def update_progress_bar(self):
        if self.progress_bar:
            self.progress_bar()