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


#!/usr/bin/env bash

## Random seed to use for both the environment and agent (-1 for random)
SEED="69"

## ID of the environment
## Reach
# ENV_ID="Reach-Gazebo-v0"
# ENV_ID="Reach-ColorImage-Gazebo-v0"
# ENV_ID="Reach-Octree-Gazebo-v0"
# ENV_ID="Reach-OctreeWithColor-Gazebo-v0"
## Grasp
# ENV_ID="Grasp-Octree-Gazebo-v0"
ENV_ID="Grasp-OctreeWithColor-Gazebo-v0"
#ENV_ID="IK-Gazebo-v0"
#ENV_ID="IK-WO-Gazebo-v0"
#ENV_ID="IK-WO-Gazebo-v1"
#ENV_ID="REACH-WO-Gazebo-v0"

## Robot model
ROBOT_MODEL="panda"
# ROBOT_MODEL="ur5_rg2"
# ROBOT_MODEL="kinova_j2s7s300"

## Algorithm to use
## Algorithm to use
#ALGO="sac"
# ALGO="td3"
ALGO="tqc"
# ALGO="ppo"
#ALGO="a2c"

## Args for optimization
OPTIMIZE_SAMPLER="tpe"
OPTIMIZE_PRUNER="median"
OPTIMIZE_N_TIMESTAMPS=100000
OPTIMIZE_N_STARTUP_TRIALS=5
OPTIMIZE_N_TRIALS=20
OPTIMIZE_N_EVALUATIONS=4
OPTIMIZE_EVAL_EPISODES=20

## Path to a replay buffer that should be preloaded before each trial begins
# PRELOAD_REPLAY_BUFFER="training/preloaded_buffers/"${ENV_ID}"_1/replay_buffer.pkl"

## Path to a replay buffer that should be preloaded before each trial begins
# PRELOAD_REPLAY_BUFFER="training/preloaded_buffers/"${ENV_ID}"_1/replay_buffer.pkl"

## Path the parent training directory
TRAINING_DIR="training"
## Path to logs
LOG_DIR=""${TRAINING_DIR}"/"${ENV_ID}"/optimize/logs"
## Path to tensorboard logs
TENSORBOARD_LOG_DIR=""${TRAINING_DIR}"/"${ENV_ID}"/optimize/tensorboard_logs"

## Arguments for the environment
ENV_ARGS="robot_model:\"${ROBOT_MODEL}\""

## Extra arguments to be passed into the script
EXTRA_ARGS=""

########################################################################################################################
########################################################################################################################

## Spawn ign_moveit2 subprocess in background, while making sure to forward termination signals
IGN_MOVEIT2_CMD="ros2 launch drl_grasping ign_moveit2_headless.launch.py"
if [ "$ROBOT_MODEL" = "ur5_rg2" ]; then
    IGN_MOVEIT2_CMD="ros2 launch drl_grasping ign_moveit2_headless_ur5_rg2.launch.py"
fi
if [ "$ROBOT_MODEL" = "kinova_j2s7s300" ]; then
    IGN_MOVEIT2_CMD="ros2 launch drl_grasping ign_moveit2_headless_kinova_j2s7s300.launch.py"
fi
echo "Launching ign_moveit2 in background:"
echo "${IGN_MOVEIT2_CMD}"
echo ""
${IGN_MOVEIT2_CMD} &
## Kill all subprocesses when SIGINT SIGTERM EXIT are received
subprocess_pid_ign_moveit2="${!}"
terminate_subprocesses() {
    echo "INFO: Caught signal, killing all subprocesses..."
    pkill -P "${subprocess_pid_ign_moveit2}"
}
trap 'terminate_subprocesses' SIGINT SIGTERM EXIT ERR

## Arguments
OPTIMIZE_ARGS="--env "${ENV_ID}" --algo "${ALGO}" --seed "${SEED}" --log-folder "${LOG_DIR}" --tensorboard-log "${TENSORBOARD_LOG_DIR}" --optimize-hyperparameters --sampler "${OPTIMIZE_SAMPLER}" --pruner "${OPTIMIZE_PRUNER}" --n-timesteps "${OPTIMIZE_N_TIMESTAMPS}" --n-startup-trials "${OPTIMIZE_N_STARTUP_TRIALS}" --n-trials "${OPTIMIZE_N_TRIALS}" --n-evaluations "${OPTIMIZE_N_EVALUATIONS}" --eval-episodes "${OPTIMIZE_EVAL_EPISODES}" --env-kwargs "${ENV_ARGS}" "${EXTRA_ARGS}""
## Add preload replay buffer to args in order to preload buffer with transitions that use custom heuristic (demonstration)
if [ ! -z "${PRELOAD_REPLAY_BUFFER}" ]; then
    OPTIMIZE_ARGS=""${OPTIMIZE_ARGS}" --preload-replay-buffer "${PRELOAD_REPLAY_BUFFER}""
fi

## Execute optimize script
OPTIMIZE_CMD="ros2 run drl_grasping train.py "${OPTIMIZE_ARGS}""
echo "Executing optimization command:"
echo "${OPTIMIZE_CMD}"
echo ""
${OPTIMIZE_CMD}
