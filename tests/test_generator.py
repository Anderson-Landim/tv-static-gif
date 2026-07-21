from PIL import Image
import pytest

from tv_static_gif import generate_tv_static_gif


def test_generates_five_second_gif(tmp_path):
    output = generate_tv_static_gif(
        tmp_path / "static", width=82, height=74, fps=24, text="TV", font_size=24
    )

    assert output.name == "static.gif"
    with Image.open(output) as gif:
        assert gif.format == "GIF"
        assert gif.size == (82, 74)
        assert gif.n_frames == 120
        assert sum(
            (gif.seek(frame), gif.info["duration"])[1]
            for frame in range(gif.n_frames)
        ) == 5000


@pytest.mark.parametrize(
    "kwargs",
    [{"width": 0}, {"height": 0}, {"duration": 0}, {"fps": 0}],
)
def test_rejects_invalid_settings(tmp_path, kwargs):
    with pytest.raises(ValueError):
        generate_tv_static_gif(tmp_path / "static.gif", **kwargs)
