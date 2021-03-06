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


from gym_ignition.scenario import model_wrapper, model_with_file
from gym_ignition.utils.scenario import get_unique_model_name
from scenario import core as scenario
from scenario import gazebo as scenario_gazebo
from typing import List, Tuple
from os import path


class UR5RG2(model_wrapper.ModelWrapper,
             model_with_file.ModelWithFile):

    def __init__(self,
                 world: scenario.World,
                 name: str = 'ur5_rg2',
                 position: List[float] = (0, 0, 0),
                 orientation: List[float] = (1, 0, 0, 0),
                 model_file: str = None,
                 use_fuel: bool = True,
                 arm_collision: bool = True,
                 hand_collision: bool = True,
                 separate_gripper_controller: bool = True,
                 initial_joint_positions: List[float] = (0.0, 0.0, 1.57, 0.0, -1.57, -1.57, 0.0, 0.0)):

        # Get a unique model name
        model_name = get_unique_model_name(world, name)

        # Initial pose
        initial_pose = scenario.Pose(position, orientation)

        # Get the default model description (URDF or SDF) allowing to pass a custom model
        if model_file is None:
            model_file = self.get_model_file(fuel=use_fuel)

        if not arm_collision or not hand_collision:
            model_file = self.disable_collision(model_file=model_file,
                                                arm_collision=arm_collision,
                                                hand_collision=hand_collision)

        # Insert the model
        ok_model = world.to_gazebo().insert_model(model_file,
                                                  initial_pose,
                                                  model_name)
        if not ok_model:
            raise RuntimeError("Failed to insert " + model_name)

        # Get the model
        model = world.get_model(model_name)

        self.__separate_gripper_controller = separate_gripper_controller

        # Set initial joint configuration
        self.__set_initial_joint_positions(initial_joint_positions)
        if not model.to_gazebo().reset_joint_positions(self.get_initial_joint_positions(),
                                                       self.get_joint_names()):
            raise RuntimeError("Failed to set initial robot joint positions")

        # Add JointStatePublisher to UR5 + RG2
        self.__add_joint_state_publisher(model)

        # Add JointTrajectoryController to UR5 + RG2
        self.__add_joint_trajectory_controller(model)

        # Initialize base class
        super().__init__(model=model)

    @classmethod
    def get_model_file(self, fuel=True) -> str:
        if fuel:
            return scenario_gazebo.get_model_file_from_fuel(
                "https://fuel.ignitionrobotics.org/1.0/AndrejOrsula/models/ur5_rg2")
        else:
            return "ur5_rg2"

    @classmethod
    def get_joint_names(self) -> List[str]:
        return ["shoulder_pan_joint",
                "shoulder_lift_joint",
                "elbow_joint",
                "wrist_1_joint",
                "wrist_2_joint",
                "wrist_3_joint",
                "rg2_finger_joint1",
                "rg2_finger_joint2"]

    @classmethod
    def get_joint_limits(self) -> List[Tuple[float, float]]:
        return [(-6.28319, 6.28319),
                (-6.28319, 6.28319),
                (-6.28319, 6.28319),
                (-6.28319, 6.28319),
                (-6.28319, 6.28319),
                (-6.28319, 6.28319),
                (0.0, 0.52359878),
                (0.0, 0.52359878)]

    @classmethod
    def get_base_link_name(self) -> str:
        return "base_link"

    @classmethod
    def get_ee_link_name(self) -> str:
        return "tool0"

    @classmethod
    def get_gripper_link_names(self) -> List[str]:
        return ["rg2_leftfinger",
                "rg2_rightfinger"]

    @classmethod
    def get_finger_count(self) -> int:
        return 2

    def get_initial_joint_positions(self) -> List[float]:
        return self.__initial_joint_positions

    def __set_initial_joint_positions(self, initial_joint_positions):
        self.__initial_joint_positions = initial_joint_positions

    def __add_joint_state_publisher(self, model) -> bool:
        """Add JointTrajectoryController"""
        model.to_gazebo().insert_model_plugin(
            "libignition-gazebo-joint-state-publisher-system.so",
            "ignition::gazebo::systems::JointStatePublisher",
            self.__get_joint_state_publisher_config()
        )

    @classmethod
    def __get_joint_state_publisher_config(self) -> str:
        return \
            """
            <sdf version="1.7">
            %s
            </sdf>
            """ \
            % " ".join(("<joint_name>" + joint + "</joint_name>" for joint in self.get_joint_names()))

    def __add_joint_trajectory_controller(self, model) -> bool:
        """Add JointTrajectoryController"""
        if self.__separate_gripper_controller:
            model.to_gazebo().insert_model_plugin(
                "libignition-gazebo-joint-trajectory-controller-system.so",
                "ignition::gazebo::systems::JointTrajectoryController",
                self.__get_joint_trajectory_controller_config_joints_only()
            )
            model.to_gazebo().insert_model_plugin(
                "libignition-gazebo-joint-trajectory-controller-system.so",
                "ignition::gazebo::systems::JointTrajectoryController",
                self.__get_joint_trajectory_controller_config_gripper_only()
            )
        else:
            model.to_gazebo().insert_model_plugin(
                "libignition-gazebo-joint-trajectory-controller-system.so",
                "ignition::gazebo::systems::JointTrajectoryController",
                self.__get_joint_trajectory_controller_config()
            )

    def __get_joint_trajectory_controller_config(self) -> str:
        # TODO: refactor into something more sensible
        return \
            """
            <sdf version="1.7">
            <topic>joint_trajectory</topic>
            
            <joint_name>%s</joint_name>
            <initial_position>%s</initial_position>
            <position_p_gain>3000</position_p_gain>
            <position_d_gain>15</position_d_gain>
            <position_i_gain>1650</position_i_gain>
            <position_i_min>-15</position_i_min>
            <position_i_max>15</position_i_max>
            <position_cmd_min>-150</position_cmd_min>
            <position_cmd_max>150</position_cmd_max>

            <joint_name>%s</joint_name>
            <initial_position>%s</initial_position>
            <position_p_gain>9500</position_p_gain>
            <position_d_gain>47.5</position_d_gain>
            <position_i_gain>5225</position_i_gain>
            <position_i_min>-47.5</position_i_min>
            <position_i_max>47.5</position_i_max>
            <position_cmd_min>-150</position_cmd_min>
            <position_cmd_max>150</position_cmd_max>

            <joint_name>%s</joint_name>
            <initial_position>%s</initial_position>
            <position_p_gain>6500</position_p_gain>
            <position_d_gain>32.5</position_d_gain>
            <position_i_gain>3575</position_i_gain>
            <position_i_min>-32.5</position_i_min>
            <position_i_max>32.5</position_i_max>
            <position_cmd_min>-150</position_cmd_min>
            <position_cmd_max>150</position_cmd_max>

            <joint_name>%s</joint_name>
            <initial_position>%s</initial_position>
            <position_p_gain>5000</position_p_gain>
            <position_d_gain>20</position_d_gain>
            <position_i_gain>1200</position_i_gain>
            <position_i_min>-30</position_i_min>
            <position_i_max>30</position_i_max>
            <position_cmd_min>-28</position_cmd_min>
            <position_cmd_max>28</position_cmd_max>

            <joint_name>%s</joint_name>
            <initial_position>%s</initial_position>
            <position_p_gain>4250</position_p_gain>
            <position_d_gain>10</position_d_gain>
            <position_i_gain>250</position_i_gain>
            <position_i_min>-6.88</position_i_min>
            <position_i_max>6.88</position_i_max>
            <position_cmd_min>-28</position_cmd_min>
            <position_cmd_max>28</position_cmd_max>

            <joint_name>%s</joint_name>
            <initial_position>%s</initial_position>
            <position_p_gain>3000</position_p_gain>
            <position_d_gain>2.5</position_d_gain>
            <position_i_gain>775</position_i_gain>
            <position_i_min>-6.25</position_i_min>
            <position_i_max>6.25</position_i_max>
            <position_cmd_min>-28</position_cmd_min>
            <position_cmd_max>28</position_cmd_max>

            <joint_name>%s</joint_name>
            <initial_position>%s</initial_position>
            <position_p_gain>300</position_p_gain>
            <position_d_gain>0.5</position_d_gain>
            <position_i_gain>100</position_i_gain>
            <position_i_min>-10</position_i_min>
            <position_i_max>10</position_i_max>
            <position_cmd_min>-10.6</position_cmd_min>
            <position_cmd_max>10.6</position_cmd_max>

            <joint_name>%s</joint_name>
            <initial_position>%s</initial_position>
            <position_p_gain>300</position_p_gain>
            <position_d_gain>0.5</position_d_gain>
            <position_i_gain>100</position_i_gain>
            <position_i_min>-10</position_i_min>
            <position_i_max>10</position_i_max>
            <position_cmd_min>-10.6</position_cmd_min>
            <position_cmd_max>10.6</position_cmd_max>
            </sdf>
            """ % \
            (self.get_joint_names()[0],
             str(self.get_initial_joint_positions()[0]),
             self.get_joint_names()[1],
             str(self.get_initial_joint_positions()[1]),
             self.get_joint_names()[2],
             str(self.get_initial_joint_positions()[2]),
             self.get_joint_names()[3],
             str(self.get_initial_joint_positions()[3]),
             self.get_joint_names()[4],
             str(self.get_initial_joint_positions()[4]),
             self.get_joint_names()[5],
             str(self.get_initial_joint_positions()[5]),
             self.get_joint_names()[6],
             str(self.get_initial_joint_positions()[6]),
             self.get_joint_names()[7],
             str(self.get_initial_joint_positions()[7]))

    def __get_joint_trajectory_controller_config_joints_only(self) -> str:
        # TODO: refactor into something more sensible
        return \
            """
            <sdf version="1.7">
            <topic>joint_trajectory</topic>
            
            <joint_name>%s</joint_name>
            <initial_position>%s</initial_position>
            <position_p_gain>3000</position_p_gain>
            <position_d_gain>15</position_d_gain>
            <position_i_gain>1650</position_i_gain>
            <position_i_min>-15</position_i_min>
            <position_i_max>15</position_i_max>
            <position_cmd_min>-150</position_cmd_min>
            <position_cmd_max>150</position_cmd_max>

            <joint_name>%s</joint_name>
            <initial_position>%s</initial_position>
            <position_p_gain>9500</position_p_gain>
            <position_d_gain>47.5</position_d_gain>
            <position_i_gain>5225</position_i_gain>
            <position_i_min>-47.5</position_i_min>
            <position_i_max>47.5</position_i_max>
            <position_cmd_min>-150</position_cmd_min>
            <position_cmd_max>150</position_cmd_max>

            <joint_name>%s</joint_name>
            <initial_position>%s</initial_position>
            <position_p_gain>6500</position_p_gain>
            <position_d_gain>32.5</position_d_gain>
            <position_i_gain>3575</position_i_gain>
            <position_i_min>-32.5</position_i_min>
            <position_i_max>32.5</position_i_max>
            <position_cmd_min>-150</position_cmd_min>
            <position_cmd_max>150</position_cmd_max>

            <joint_name>%s</joint_name>
            <initial_position>%s</initial_position>
            <position_p_gain>5000</position_p_gain>
            <position_d_gain>20</position_d_gain>
            <position_i_gain>1200</position_i_gain>
            <position_i_min>-30</position_i_min>
            <position_i_max>30</position_i_max>
            <position_cmd_min>-28</position_cmd_min>
            <position_cmd_max>28</position_cmd_max>

            <joint_name>%s</joint_name>
            <initial_position>%s</initial_position>
            <position_p_gain>4250</position_p_gain>
            <position_d_gain>10</position_d_gain>
            <position_i_gain>250</position_i_gain>
            <position_i_min>-6.88</position_i_min>
            <position_i_max>6.88</position_i_max>
            <position_cmd_min>-28</position_cmd_min>
            <position_cmd_max>28</position_cmd_max>

            <joint_name>%s</joint_name>
            <initial_position>%s</initial_position>
            <position_p_gain>3000</position_p_gain>
            <position_d_gain>2.5</position_d_gain>
            <position_i_gain>775</position_i_gain>
            <position_i_min>-6.25</position_i_min>
            <position_i_max>6.25</position_i_max>
            <position_cmd_min>-28</position_cmd_min>
            <position_cmd_max>28</position_cmd_max>
            </sdf>
            """ % \
            (self.get_joint_names()[0],
             str(self.get_initial_joint_positions()[0]),
             self.get_joint_names()[1],
             str(self.get_initial_joint_positions()[1]),
             self.get_joint_names()[2],
             str(self.get_initial_joint_positions()[2]),
             self.get_joint_names()[3],
             str(self.get_initial_joint_positions()[3]),
             self.get_joint_names()[4],
             str(self.get_initial_joint_positions()[4]),
             self.get_joint_names()[5],
             str(self.get_initial_joint_positions()[5]))

    def __get_joint_trajectory_controller_config_gripper_only(self) -> str:
        # TODO: refactor into something more sensible
        return \
            """
            <sdf version="1.7">
            <topic>gripper_trajectory</topic>

            <joint_name>%s</joint_name>
            <initial_position>%s</initial_position>
            <position_p_gain>150</position_p_gain>
            <position_d_gain>0.05</position_d_gain>
            <position_i_gain>50</position_i_gain>
            <position_i_min>-10</position_i_min>
            <position_i_max>10</position_i_max>
            <position_cmd_min>-10.6</position_cmd_min>
            <position_cmd_max>10.6</position_cmd_max>

            <joint_name>%s</joint_name>
            <initial_position>%s</initial_position>
            <position_p_gain>150</position_p_gain>
            <position_d_gain>0.05</position_d_gain>
            <position_i_gain>50</position_i_gain>
            <position_i_min>-10</position_i_min>
            <position_i_max>10</position_i_max>
            <position_cmd_min>-10.6</position_cmd_min>
            <position_cmd_max>10.6</position_cmd_max>
            </sdf>
            """ % \
            (self.get_joint_names()[6],
             str(self.get_initial_joint_positions()[6]),
             self.get_joint_names()[7],
             str(self.get_initial_joint_positions()[7]))

    @classmethod
    def disable_collision(self,
                          model_file: str,
                          arm_collision: bool,
                          hand_collision: bool) -> str:

        new_model_file = path.join(path.dirname(model_file),
                                   'model_without_arm_collision.sdf')

        # Remove collision geometry
        with open(model_file, "r") as original_sdf_file:
            with open(new_model_file, "w") as new_sdf_file:
                while True:
                    # Read a new line and make sure it is not the end of the file
                    line = original_sdf_file.readline()
                    if not line.rstrip():
                        break

                    # Once `<collision>` for lower links is encountered, skip that and all lines until `</collision>` is reached
                    if not arm_collision:
                        if ('<collision name="base_link_collision"' in line or
                            '<collision name="shoulder_link_collision"' in line or
                            '<collision name="upper_arm_link_collision"' in line or
                            '<collision name="forearm_link_collision"' in line or
                            '<collision name="wrist_1_link_collision"' in line or
                                '<collision name="wrist_2_link_collision"' in line):
                            line = original_sdf_file.readline()
                            while not '</collision>' in line:
                                line = original_sdf_file.readline()
                            continue

                    # Same as for arm, but check for hand and both fingers
                    if not hand_collision:
                        if ('<collision name="rg2_hand_collision"' in line or
                            '<collision name="rg2_leftfinger_collision"' in line or
                                '<collision name="rg2_rightfinger_collision"' in line):
                            line = original_sdf_file.readline()
                            while not '</collision>' in line:
                                line = original_sdf_file.readline()
                            continue

                    # Write all other lines into the new file
                    new_sdf_file.write(line)

        # Return path to the new file
        return new_model_file
