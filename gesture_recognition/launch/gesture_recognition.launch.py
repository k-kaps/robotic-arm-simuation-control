import os

from ament_index_python.packages import get_package_share_directory


from launch import LaunchDescription
from launch.actions import ExecuteProcess, IncludeLaunchDescription, RegisterEventHandler
from launch.event_handlers import (OnProcessStart, OnProcessExit)
from launch.launch_description_sources import PythonLaunchDescriptionSource

from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder

import xacro

def generate_launch_description():

    image_publisher_node = Node(
        package = "gesture_recognition",
        executable = "image_publisher_node",
        name = "image_publisher_node"
    )

    image_subscriber_node = Node(
        package = "gesture_recognition",
        executable = "image_subscriber_node",
        name = "image_subscriber_node"
    )

    moveit_config = (
        MoveItConfigsBuilder("six_dof_arm")
        .robot_description(file_path="config/six_dof_arm.urdf.xacro")
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .planning_scene_monitor(publish_robot_description= True, publish_robot_description_semantic=True)
        .planning_pipelines(pipelines=["ompl"])
        .to_moveit_configs()
	)
    
    moveit_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        name="move_group",
        output="screen",
        parameters=[moveit_config.to_dict()]
	)
    
    gazebo = IncludeLaunchDescription(
			PythonLaunchDescriptionSource([os.path.join(
				get_package_share_directory('gazebo_ros'), 'launch'), '/gazebo.launch.py']),
		)
    
    package_path = os.path.join(
                    get_package_share_directory('six_dof_arm'))
    
    xacro_file = os.path.join(package_path, 
					'urdf', 
					'six_dof_arm.urdf')
    
    doc = xacro.parse(open(xacro_file))
    xacro.process_doc(doc)
    params = {'robot_description' : doc.toxml()}
    
    node_robot_state_publisher = Node(
		package = 'robot_state_publisher',
		executable = 'robot_state_publisher',
		output = 'screen',
        parameters = [params]
		)
    
    load_joint_state_controller = ExecuteProcess(
					cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
					'joint_state_broadcaster'],
					output='screen'
					)
    
    load_arm_controller = ExecuteProcess(
					cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
					'arm_controller'],
					output='screen'
					)
    
    spawn_entity = Node(package = 'gazebo_ros', executable = 'spawn_entity.py', 
			arguments = ['-topic', '/robot_description',
					'-entity', 'six_dof_arm.urdf'], 
			output = 'screen')
	
    return LaunchDescription([
		RegisterEventHandler(
				event_handler=OnProcessExit(
					target_action=spawn_entity,
					on_exit=[load_joint_state_controller],)
					),
		RegisterEventHandler(
				event_handler=OnProcessExit(
					target_action=load_joint_state_controller,
					on_exit=[load_arm_controller],)
					),
        	RegisterEventHandler(
				event_handler=OnProcessExit(
					target_action=load_arm_controller,
					on_exit=[image_publisher_node, image_subscriber_node],)
					),
		gazebo, 
        moveit_node,
		node_robot_state_publisher,
		spawn_entity,
    ])
