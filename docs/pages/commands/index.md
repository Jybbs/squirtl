# Commands

*SquiRtL* runs as the `squirtl` command, which trains an agent, stops a run, plays an episode back in the emulator's window, evaluates a trained agent against random presses, prints a source's citation, and writes the files the docs site reads from the package. Each page in this section is written from the help its command prints, so every setting below carries the default and the description `squirtl <command> --help` shows.

## At the Terminal

A run starts from a fresh clone once the ROM sits at `data/rom.gb`, trains for the steps `--steps` names, and prints its directory under `data/runs/`, which `squirtl evaluate` then reads. `squirtl stop` ends a run in another terminal with a checkpoint, and `squirtl train --resume` continues it from there.

## Every Setting Is a Flag

Each setting of a run is one flag of `squirtl train`, named for the subject it belongs to and the field it sets, such as `--agent.discount` or `--reward.starter`. A setting on by default turns off as `--agent.double-q=false` does, and a pair such as `--environment.frame-shape` takes both its values in turn.
