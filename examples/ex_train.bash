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
SEED="42"

## ID of the environment
## Reach
# ENV_ID="Reach-Gazebo-v0"
# ENV_ID="Reach-ColorImage-Gazebo-v0"
# ENV_ID="Reach-Octree-Gazebo-v0"
# ENV_ID="Reach-OctreeWithColor-Gazebo-v0"
## Grasp
# ENV_ID="Grasp-Octree-Gazebo-v0"
#ENV_ID="Grasp-OctreeWithColor-Gazebo-v0"
#ENV_ID="IK-Gazebo-v0"
#ENV_ID="IK-WO-Gazebo-v0"
#ENV_ID="IK-WO-Gazebo-v1"
#ENV_ID="IK-WO-Gazebo-v2"
#ENV_ID="IK-WMO-Gazebo-v0"
ENV_ID="IK-WMMO-Gazebo-v0"

## Robot model
ROBOT_MODEL="panda"
# ROBOT_MODEL="ur5_rg2"
# ROBOT_MODEL="kinova_j2s7s300"

## Algorithm to use

ALGO="tqc"
#ALGO="sac"
#ALGO="td3"
#ALGO="ppo"
#ALGO="a2c"
## Path to trained agent (to continue training)
TRAINED_AGENT=""${ENV_ID}"_21/rl_model_470000_steps.zip"

## Path to a replay buffer that should be preloaded before training begins
# PRELOAD_REPLAY_BUFFER="training/preloaded_buffers/"${ENV_ID}"_1/replay_buffer.pkl"

## Continuous evaluation (-1 to disable)
EVAL_FREQUENCY=-1
EVAL_EPISODES=10

## Path the parent training directory
TRAINING_DIR="training"
## Path to logs
LOG_DIR=""${TRAINING_DIR}"/"${ENV_ID}"/logs"
## Path to tensorboard logs
TENSORBOARD_LOG_DIR=""${TRAINING_DIR}"/"${ENV_ID}"/tensorboard_logs"

## Arguments for the environment
ENV_ARGS="robot_model:\"${ROBOT_MODEL}\""

## Extra arguments to be passed into the script
EXTRA_ARGS=""
# EXTRA_ARGS="--save-replay-buffer"

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
TRAIN_ARGS="--env "${ENV_ID}" --algo "${ALGO}" --seed "${SEED}" --log-folder "${LOG_DIR}" --tensorboard-log "${TENSORBOARD_LOG_DIR}" --eval-freq "${EVAL_FREQUENCY}" --eval-episodes "${EVAL_EPISODES}" --env-kwargs "${ENV_ARGS}" "${EXTRA_ARGS}""
## Add trained agent to args in order to continue training
if [ ! -z "${TRAINED_AGENT}" ]; then
    TRAIN_ARGS=""${TRAIN_ARGS}" --trained-agent "${LOG_DIR}"/"${ALGO}"/"${TRAINED_AGENT}""
fi
## Add preload replay buffer to args in order to preload buffer with transitions that use custom heuristic (demonstration)
if [ ! -z "${PRELOAD_REPLAY_BUFFER}" ]; then
    TRAIN_ARGS=""${TRAIN_ARGS}" --preload-replay-buffer "${PRELOAD_REPLAY_BUFFER}""
fi

## Execute train script
TRAIN_CMD="ros2 run drl_grasping train.py "${TRAIN_ARGS}""
echo "Executing train command:"
echo "${TRAIN_CMD}"
echo ""
${TRAIN_CMD}
