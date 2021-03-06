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


from gym_ignition.scenario import model_wrapper
from gym_ignition.utils import misc
from gym_ignition.utils.scenario import get_unique_model_name
from scenario import core as scenario
from typing import List
import numpy as np
import os


class RandomGround(model_wrapper.ModelWrapper):

    def __init__(self,
                 world: scenario.World,
                 name: str = 'ground',
                 position: List[float] = (0, 0, 0),
                 orientation: List[float] = (1, 0, 0, 0),
                 size: List[float] = (1.0, 1.0),
                 collision_thickness: float = 0.05,
                 friction: float = 5.0,
                 texture_dir: str = None,
                 np_random=None):

        if np_random is None:
            np_random = np.random.default_rng()

        # Get a unique model name
        model_name = get_unique_model_name(world, name)

        # Initial pose
        initial_pose = scenario.Pose(position, orientation)

        # Find random PBR texture
        albedo_map = None
        normal_map = None
        roughness_map = None
        metalness_map = None
        if texture_dir is not None:
            # Get list of the available textures
            textures = os.listdir(texture_dir)
            # Keep only texture directories if texture_dir is a git repo (ugly fix)
            try:
                textures.remove('.git')
            except:
                pass
            try:
                textures.remove('README.md')
            except:
                pass

            # Choose a random texture from these
            random_texture_dir = os.path.join(texture_dir,
                                              np_random.choice(textures))

            # List all files
            texture_files = os.listdir(random_texture_dir)

            # Extract the appropriate files
            for texture in texture_files:
                texture_lower = texture.lower()
                if 'basecolor' in texture_lower or 'albedo' in texture_lower:
                    albedo_map = os.path.join(random_texture_dir, texture)
                elif 'normal' in texture_lower:
                    normal_map = os.path.join(random_texture_dir, texture)
                elif 'roughness' in texture_lower:
                    roughness_map = os.path.join(random_texture_dir, texture)
                elif 'specular' in texture_lower or 'metalness' in texture_lower:
                    metalness_map = os.path.join(random_texture_dir, texture)

        # Create SDF string for the model
        sdf = \
            f'''<sdf version="1.7">
            <model name="{model_name}">
                <static>true</static>
                <link name="{model_name}_link">
                    <collision name="{model_name}_collision">
                        <pose>0 0 {-collision_thickness/2} 0 0 0</pose>
                        <geometry>
                            <box>
                                <size>{size[0]} {size[1]} {collision_thickness}</size>
                            </box>
                        </geometry>
                        <surface>
                            <friction>
                                <ode>
                                    <mu>{friction}</mu>
                                    <mu2>{friction}</mu2>
                                    <fdir1>0 0 0</fdir1>
                                    <slip1>0.0</slip1>
                                    <slip2>0.0</slip2>
                                </ode>
                            </friction>
                        </surface>
                    </collision>
                    <visual name="{model_name}_visual">
                        <geometry>
                            <plane>
                                <normal>0 0 1</normal>
                                <size>{size[0]} {size[1]}</size>
                            </plane>
                        </geometry>
                        <material>
                            <ambient>1 1 1 1</ambient>
                            <diffuse>1 1 1 1</diffuse>
                            <specular>1 1 1 1</specular>
                            <pbr>
                                <metal>
                                    {"<albedo_map>%s</albedo_map>"
                                        % albedo_map if albedo_map is not None else ""}
                                    {"<normal_map>%s</normal_map>"
                                        % normal_map if normal_map is not None else ""}
                                    {"<roughness_map>%s</roughness_map>"
                                        % roughness_map if roughness_map is not None else ""}
                                    {"<metalness_map>%s</metalness_map>" 
                                        % metalness_map if metalness_map is not None else ""}
                                </metal>
                            </pbr>
                        </material>
                    </visual>
                </link>
            </model>
        </sdf>'''

        # Convert it into a file
        sdf_file = misc.string_to_file(sdf)

        # Insert the model
        ok_model = world.to_gazebo().insert_model(sdf_file,
                                                  initial_pose,
                                                  model_name)
        if not ok_model:
            raise RuntimeError('Failed to insert ' + model_name)

        # Get the model
        model = world.get_model(model_name)

        # Initialize base class
        model_wrapper.ModelWrapper.__init__(self, model=model)
