FROM osrf/ros:noetic-desktop-full

ENV DEBIAN_FRONTEND=noninteractive \
    LIBGL_ALWAYS_SOFTWARE=1 \
    GAZEBO_HEADLESS_RENDERING=1 \
    ROS_HOSTNAME=localhost \
    ROS_MASTER_URI=http://localhost:11311 \
    ROS_PORT_SIM=11311 \
    PYTHONUNBUFFERED=1 \
    DISPLAY=:99

RUN apt-get update && apt-get install -y --no-install-recommends \
      python3-pip \
      python3-rosdep \
      ros-noetic-cv-bridge \
      ros-noetic-gazebo-ros-pkgs \
      ros-noetic-hls-lfcd-lds-driver \
      ros-noetic-joint-state-publisher \
      ros-noetic-openslam-gmapping \
      ros-noetic-robot-state-publisher \
      ros-noetic-rosserial-python \
      ros-noetic-turtlebot3-msgs \
      ros-noetic-velodyne-msgs \
      ros-noetic-xacro \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY requirements.txt /workspace/requirements.txt
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Gazebo camera sensors and RViz need an X display: docker/entrypoint.sh starts a
# virtual one (Xvfb) so the simulation runs without a GUI or GPU.
RUN apt-get update && apt-get install -y --no-install-recommends curl xvfb \
    && rm -rf /var/lib/apt/lists/*

# The Pioneer world references two meshes from Gazebo's online model database.
# Without a local copy Gazebo downloads them on every container start (~60 s, needs
# internet) and the fire hydrant has no collision mesh while offline.
RUN mkdir -p /root/.gazebo/models && cd /root/.gazebo/models \
    && for m in fire_hydrant cardboard_box; do \
         curl -fsSL "http://models.gazebosim.org/${m}/model.tar.gz" | tar xz; \
       done

COPY . /workspace
RUN /bin/bash -c "source /opt/ros/noetic/setup.bash && cd catkin_ws && catkin_make"

ENV GAZEBO_RESOURCE_PATH=/workspace/catkin_ws/src/multi_robot_scenario/launch
RUN echo 'source /opt/ros/noetic/setup.bash' >> /root/.bashrc \
    && echo 'source /workspace/catkin_ws/devel/setup.bash' >> /root/.bashrc \
    && chmod +x /workspace/docker/entrypoint.sh /workspace/scripts/*.sh

ENTRYPOINT ["/workspace/docker/entrypoint.sh"]
CMD ["bash"]
