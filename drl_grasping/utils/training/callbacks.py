## BSD 3-Clause License
##
## Copyright (c) 2021, Andrej Orsula
## All rights reserved.

## Redistribution and use in source and binary forms, with or without
## modification, are permitted provided that the following conditions are met:

## 1. Redistributions of source code must retain the above copyright notice, this
##   list of conditions and the following disclaimer.
##
## 2. Redistributions in binary form must reproduce the above copyright notice,
##   this list of conditions and the following disclaimer in the documentation
##   and/or other materials provided with the distribution.
##
## 3. Neither the name of the copyright holder nor the names of its
##   contributors may be used to endorse or promote products derived from
##   this software without specific prior written permission.
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
## AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
## IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
## DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
## FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
## DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
## SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
## CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
## OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
## OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


import os
from typing import Optional

import numpy as np
import optuna
from matplotlib import pyplot as plt
from stable_baselines3.common.callbacks import BaseCallback, EvalCallback, CheckpointCallback
from stable_baselines3.common.vec_env import DummyVecEnv, VecEnv


class TrialEvalCallback(EvalCallback):
    """
    Callback used for evaluating and reporting a trial.
    """

    def __init__(
        self,
        eval_env: VecEnv,
        trial: optuna.Trial,
        n_eval_episodes: int = 5,
        eval_freq: int = 10000,
        deterministic: bool = True,
        verbose: int = 0,
    ):

        super(TrialEvalCallback, self).__init__(
            eval_env=eval_env,
            n_eval_episodes=n_eval_episodes,
            eval_freq=eval_freq,
            deterministic=deterministic,
            verbose=verbose,
        )
        self.trial = trial
        self.eval_idx = 0
        self.is_pruned = False

    def _on_step(self) -> bool:
        if self.eval_freq > 0 and self.n_calls % self.eval_freq == 0:
            print("Evaluating trial")
            super(TrialEvalCallback, self)._on_step()
            self.eval_idx += 1
            # report best or report current ?
            # report num_timesteps or elasped time ?
            self.trial.report(self.last_mean_reward, self.eval_idx)
            # Prune trial if need
            if self.trial.should_prune():
                self.is_pruned = True
                return False
        return True


class SaveVecNormalizeCallback(BaseCallback):
    """
    Callback for saving a VecNormalize wrapper every ``save_freq`` steps

    :param save_freq: (int)
    :param save_path: (str) Path to the folder where ``VecNormalize`` will be saved, as ``vecnormalize.pkl``
    :param name_prefix: (str) Common prefix to the saved ``VecNormalize``, if None (default)
        only one file will be kept.
    """

    def __init__(self, save_freq: int, save_path: str, name_prefix: Optional[str] = None, verbose: int = 0):
        super(SaveVecNormalizeCallback, self).__init__(verbose)
        self.save_freq = save_freq
        self.save_path = save_path
        self.name_prefix = name_prefix

    def _init_callback(self) -> None:
        # Create folder if needed
        if self.save_path is not None:
            os.makedirs(self.save_path, exist_ok=True)

    def _on_step(self) -> bool:
        if self.n_calls % self.save_freq == 0:
            if self.name_prefix is not None:
                path = os.path.join(self.save_path, f"{self.name_prefix}_{self.num_timesteps}_steps.pkl")
            else:
                path = os.path.join(self.save_path, "vecnormalize.pkl")
            if self.model.get_vec_normalize_env() is not None:
                self.model.get_vec_normalize_env().save(path)
                if self.verbose > 1:
                    print(f"Saving VecNormalize to {path}")
        return True


class PlotNoiseRatioCallback(BaseCallback):
    """
    Callback for plotting noise contribution to the exploration.
    Warning: it only works with 1D action space env for now (like MountainCarContinuous)

    :param display_freq: (int) Display the plot every ``display_freq`` steps.
    :param verbose: (int)
    """

    def __init__(self, display_freq: int = 1000, verbose: int = 0):
        super(PlotNoiseRatioCallback, self).__init__(verbose)
        self.display_freq = display_freq
        # Action buffers
        self.deterministic_actions = []
        self.noisy_actions = []
        self.noises = []

    def _on_step(self) -> bool:
        # We assume this is a DummyVecEnv
        assert isinstance(self.training_env, DummyVecEnv)
        # Retrieve last observation
        obs = self.training_env._obs_from_buf()
        # Retrieve stochastic and deterministic action
        # we can extract the noise contribution from those two
        noisy_action = self.model.predict(obs, deterministic=False)[0].flatten()
        deterministic_action = self.model.predict(obs, deterministic=True)[0].flatten()
        noise = noisy_action - deterministic_action

        self.deterministic_actions.append(deterministic_action)
        self.noisy_actions.append(noisy_action)
        self.noises.append(noise)

        if self.n_calls % self.display_freq == 0:
            x = np.arange(len(self.noisy_actions))

            self.deterministic_actions = np.array(self.deterministic_actions)
            self.noises = np.array(self.noises)

            plt.figure("Deterministic action and noise during exploration", figsize=(6.4, 4.8))
            # plt.title('Deterministic action and noise during exploration', fontsize=14)
            plt.xlabel("Timesteps", fontsize=14)
            plt.xticks(fontsize=13)
            plt.ylabel("Action", fontsize=14)
            plt.plot(x, self.deterministic_actions, label="deterministic action", linewidth=2)
            plt.plot(x, self.noises, label="exploration noise", linewidth=2)
            plt.plot(x, self.noisy_actions, label="noisy action", linewidth=2)
            plt.legend(fontsize=13)
            plt.show()
            # Reset
            self.noisy_actions = []
            self.deterministic_actions = []
            self.noises = []
        return True


class CheckpointCallbackWithReplayBuffer(CheckpointCallback):
    """
    Callback for saving a model every ``save_freq`` steps
    :param save_freq:
    :param save_path: Path to the folder where the model will be saved.
    :param name_prefix: Common prefix to the saved models
    :param save_replay_buffer: If enabled, save replay buffer together with model (if supported by algorithm).
    :param verbose:
    """

    def __init__(self, save_freq: int, save_path: str, name_prefix: str = "rl_model", save_replay_buffer: bool = False, verbose: int = 0):
        super(CheckpointCallbackWithReplayBuffer, self).__init__(save_freq, save_path, name_prefix, verbose)
        self.save_replay_buffer = save_replay_buffer
        # self.save_replay_buffer = hasattr(self.model, "save_replay_buffer") and save_replay_buffer

    def _on_step(self) -> bool:
        if self.n_calls % self.save_freq == 0:
            path = os.path.join(self.save_path, f"{self.name_prefix}_{self.num_timesteps}_steps")
            self.model.save(path)
            if self.verbose > 0:
                print(f"Saving model checkpoint to {path}")
            if self.save_replay_buffer:
                path_replay_buffer = os.path.join(self.save_path, "replay_buffer.pkl")
                self.model.save_replay_buffer(path_replay_buffer)
                if self.verbose > 0:
                    print(f"Saving model checkpoint to {path_replay_buffer}")
        return True
