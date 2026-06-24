from orbinspect_gazebo.image_video_recorder import ImageVideoRecorder
import pytest
from sensor_msgs.msg import Image


def test_channels_for_encoding() -> None:
    assert ImageVideoRecorder._channels_for_encoding('rgb8') == 3
    assert ImageVideoRecorder._channels_for_encoding('rgba8') == 4
    assert ImageVideoRecorder._channels_for_encoding('mono8') == 1


def test_unsupported_encoding_raises() -> None:
    with pytest.raises(ValueError):
        ImageVideoRecorder._channels_for_encoding('16UC1')


def test_rgb_image_to_bgr() -> None:
    msg = Image()
    msg.height = 1
    msg.width = 1
    msg.encoding = 'rgb8'
    msg.step = 3
    msg.data = bytes([10, 20, 30])

    frame = ImageVideoRecorder._image_to_bgr(msg)

    assert frame.shape == (1, 1, 3)
    assert frame[0, 0].tolist() == [30, 20, 10]
