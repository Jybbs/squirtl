import matplotlib.pyplot as plt
import time

class Metrics:
    def __init__(self, save_directory):
        self.save_directory = save_directory
        self.log_file       = save_directory / "metrics_log.txt"
        self.start_time     = time.time()

        self.episode_metrics = {"lengths"  : [],
                                "losses"   : [],
                                "q_values" : [],
                                "rewards"  : []}

        self.current_episode_metrics = {"length"  : 0,
                                        "loss"    : 0,
                                        "q_value" : 0,
                                        "reward"  : 0}

        self.create_log_file()

    def create_log_file(self):
        with open(self.log_file, "w") as f:
            f.write(
                f"{'Episode':>8}{'Elapsed Time':>15}{'Length':>10}"
                f"{'Loss':>10}{'Q-Value':>10}{'Reward':>10}\n"
            )

    def log_step(self, reward, loss, q_value):
        self.current_episode_metrics["length"]  += 1
        self.current_episode_metrics["loss"]    += loss
        self.current_episode_metrics["q_value"] += q_value
        self.current_episode_metrics["reward"]  += reward

    def log_episode(self):
        for metric, value in self.current_episode_metrics.items():

            if metric in ["loss", "q_value"]:
                value /= self.current_episode_metrics["length"]

            self.episode_metrics[metric + "s"].append(value)
            self.current_episode_metrics[metric] = 0

    def record_episode(self, episode):
        elapsed_time = time.time() - self.start_time
        metrics      = [f"{m.capitalize()}: {v[-1]:8.2f}" for m, v in self.episode_metrics.items()]
        log_entry    = \
        (
            f"Episode {episode:4d} - " + " - ".join(metrics) +
            f" - Elapsed Time: {elapsed_time:10.2f}s"
        )

        print(log_entry)

        with open(self.log_file, "a") as f:
            f.write(log_entry.replace(" - ", "") + "\n")

    def plot_metrics(self):
        _, axs = plt.subplots(2, 2, figsize = (12, 8))
        axs    = axs.flatten()

        for i, (metric, values) in enumerate(self.episode_metrics.items()):
            axs[i].plot(values)
            axs[i].set_title(f"Episode {metric.capitalize()}")
            axs[i].set_xlabel("Episode")
            axs[i].set_ylabel(metric.capitalize()[:-1])
        plt.tight_layout()
        plt.savefig(self.save_directory / "metrics_plot.png")
        plt.close()