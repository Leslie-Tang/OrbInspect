"""Record a ROS image topic to an MP4 video file."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Image


class ImageVideoRecorder(Node):
    """Subscribe to a ROS image topic and save frames as MP4."""

    def __init__(self) -> None:
        super().__init__('image_video_recorder')

        self.declare_parameter('image_topic', '/orbinspect/chaser_follow_camera/image')
        self.declare_parameter('output_path', 'data/results/chaser_follow_view.mp4')
        self.declare_parameter('fps', 12.0)
        self.declare_parameter('max_frames', 360)

        image_topic = str(self.get_parameter('image_topic').value)
        self.output_path = Path(str(self.get_parameter('output_path').value))
        self.fps = self._positive_parameter('fps')
        self.max_frames = self._positive_int_parameter('max_frames')
        self.writer: cv2.VideoWriter | None = None
        self.frames_written = 0

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.create_subscription(Image, image_topic, self._image_callback, 10)
        self.get_logger().info(f'recording {image_topic} to {self.output_path}')

    def _image_callback(self, msg: Image) -> None:
        if self.frames_written >= self.max_frames:
            return
        frame = self._image_to_bgr(msg)
        if self.writer is None:
            self._open_writer(frame.shape[1], frame.shape[0])
        assert self.writer is not None
        self.writer.write(frame)
        self.frames_written += 1
        if self.frames_written >= self.max_frames:
            self.get_logger().info(
                f'wrote {self.frames_written} frames to {self.output_path}'
            )

    def _open_writer(self, width: int, height: int) -> None:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(
            str(self.output_path),
            fourcc,
            self.fps,
            (width, height),
        )
        if not self.writer.isOpened():
            raise RuntimeError(f'failed to open video writer for {self.output_path}')

    @staticmethod
    def _image_to_bgr(msg: Image) -> Any:
        channels = ImageVideoRecorder._channels_for_encoding(msg.encoding)
        array = np.frombuffer(msg.data, dtype=np.uint8)
        image = array.reshape((msg.height, msg.step))[:, :msg.width * channels]
        image = image.reshape((msg.height, msg.width, channels))
        if msg.encoding.lower() in ('rgb8', 'rgba8'):
            return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        if msg.encoding.lower() in ('bgr8', 'bgra8'):
            return image[:, :, :3]
        if channels == 1:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        return image[:, :, :3]

    @staticmethod
    def _channels_for_encoding(encoding: str) -> int:
        normalized = encoding.lower()
        if normalized in ('rgb8', 'bgr8'):
            return 3
        if normalized in ('rgba8', 'bgra8'):
            return 4
        if normalized in ('mono8', '8uc1'):
            return 1
        raise ValueError(f'unsupported image encoding: {encoding}')

    def _positive_parameter(self, name: str) -> float:
        value = float(self.get_parameter(name).value)
        if value <= 0.0:
            raise ValueError(f'{name} must be positive')
        return value

    def _positive_int_parameter(self, name: str) -> int:
        value = int(self.get_parameter(name).value)
        if value <= 0:
            raise ValueError(f'{name} must be positive')
        return value

    def destroy_node(self) -> bool:
        if self.writer is not None:
            self.writer.release()
            self.writer = None
        return super().destroy_node()


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = ImageVideoRecorder()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            try:
                node.destroy_node()
            except KeyboardInterrupt:
                pass
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
