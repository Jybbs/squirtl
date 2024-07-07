import json
import matplotlib.pyplot as plt
import numpy             as np

from alive_progress import alive_bar
from cv2            import COLOR_RGB2BGR, VideoWriter, VideoWriter_fourcc, cvtColor
from pandas         import DataFrame
from seaborn        import regplot, scatterplot

class Logging:
    def __init__(self, debug, settings):
        self.debug        = debug
        self.episode      = None
        self.progress_bar = None
        self.settings     = settings

    @property
    def episode_metrics(self):
        return \
        {
            "average_loss"         : self.episode.average_loss,
            "average_q_value"      : self.episode.average_q_value,
            "backtracking_actions" : self.episode.action_type_counts["backtrack"],
            "effective_actions"    : self.episode.effective_actions,
            "elapsed_time"         : self.episode.elapsed_time,
            "episode"              : self.episode.episode_number,
            "new_actions"          : self.episode.action_type_counts["new"],
            "total_actions"        : self.episode.total_actions,
            "total_reward"         : self.episode.total_reward,
            "wait_actions"         : self.episode.action_type_counts["wait"],
        }

    def __call__(self, episode):
        self.episode = episode
        if self.debug:
            self.progress_bar = alive_bar(self.settings.MAX_ACTIONS)

    def __str__(self):
        metrics = self.episode_metrics
        return (
            f"\nEpisode Summary:\n"
            f"Episode:     {metrics['episode']:4d}\n"
            f"Actions:     {metrics['total_actions']:4d}\n"
            f"Total Rwd:   {metrics['total_reward']:8.2f}\n"
            f"Avg Loss:    {metrics['average_loss']:8.4f}\n"
            f"Avg Q-Value: {metrics['average_q_value']:8.4f}\n"
            f"Time:        {metrics['elapsed_time']:6.2f}s\n"
            f"Effective:   {metrics['effective_actions']:4d}\n"
            f"Ineffective: {metrics['total_actions'] - metrics['effective_actions']:4d}\n"
            f"New:         {metrics['new_actions']:4d}\n"
            f"Backtrack:   {metrics['backtracking_actions']:4d}\n"
            f"Wait:        {metrics['wait_actions']:4d}\n"
            f"{'-' * 50}"
        )

    def action_summary(self, action):
        return \
        (
            f"Episode {self.episode.episode_number:4d} | "
            f"Action {self.episode.total_actions:4d} | "
            f"Button: {action.action_name:10s} | "
            f"Type: {action.action_type:14s} | "
            f"Effective: {str(action.is_effective):5s} | "
            f"Reward: {action.reward:10.2f} | "
            f"Total Reward: {self.episode.total_reward:10.2f} | "
            f"Loss: {action.loss:8.4f} | "
            f"Q-Value: {action.q_value:8.4f} | "
            f"Time: {self.episode.elapsed_time:6.2f}s"
        )

    def log_action(self, action):
        if self.debug:
            print(self.action_summary(action))
            if self.progress_bar:
                self.progress_bar()

    def log_episode(self):
        metrics = self.episode_metrics
        self.save_episode_data(metrics)
        self.save_episode_video(metrics)
        self.plot_metrics()
        print(self)

    def plot_metrics(self):
        self.setup_plot_params()
        metrics_list = [self.episode_metrics for _ in range(1, self.episode.episode_number + 1)]
        df = DataFrame(metrics_list).drop('episode', axis = 1)
        
        fig, axes = plt.subplots(3, 3, figsize = (15, 10), sharex = True)
        colors    = plt.cm.viridis(np.linspace(0.1, 1, len(df.columns)))
        
        for (metric, data), ax, color in zip(df.items(), axes.flatten(), colors):
            ax.set_title(metric.replace('_', ' ').title())
            ax.set_ylabel('')
            ax.set_xlabel('Episode' if ax == axes[2, 1] else '')
            
            regplot \
                (x = df.index, y = data, ax = ax, scatter = False, lowess = True, line_kws = {'color': color})
            scatterplot \
                (x = df.index, y = data, ax = ax, alpha = 0.3, color = color)
            
            if ax.get_ylim()[0] <= 0 <= ax.get_ylim()[1]:
                ax.axhline(y = 0, color = 'white', linestyle = '--', linewidth = 1, alpha = 0.5)
        
        plt.tight_layout()
        plt.savefig(self.settings.metrics_directory / f"plot_episode_{self.episode.episode_number}.png")
        plt.close(fig)

    def save_episode_data(self, metrics):
        metrics_path = self.settings.metrics_directory / f"episode_{metrics['episode']}_metrics.json"
        actions_path = self.settings.metrics_directory / f"episode_{metrics['episode']}_actions.json"

        with open(metrics_path, 'w') as file:
            json.dump(metrics, file, indent = 4)

        with open(actions_path, 'w') as file:
            json.dump([vars(a) for a in self.episode.actions], file, indent = 4)

    def save_episode_video(self):
        if not self.episode.frames:
            return
        
        episode_number = self.episode.episode_number
        frame_shape    = self.episode.frames[0].shape[:2][::-1]
        video_path     = self.settings.video_directory / f"episode_{episode_number}.mp4"
        video_writer   = VideoWriter(str(video_path), VideoWriter_fourcc(*'mp4v'), 60, frame_shape)

        for frame in self.episode.frames:
            video_writer.write(cvtColor(frame, COLOR_RGB2BGR))

        video_writer.release()

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