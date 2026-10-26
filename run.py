import sys

from anima.diagnostics import logger
from anima.utils.blender import BlenderProcess
from anima.utils.encode import encode_video
from anima.utils.render_request import RenderRequest


def run() -> int:
    """Run Anima interactively, or, if `ANIMA_RENDER` is set, render headlessly and encode the video.

    Returns:
        The process exit code.
    """
    request = RenderRequest.from_env()
    if request is None:
        BlenderProcess().start().monitor()
        return 0

    process = BlenderProcess(headless=True).start().monitor()
    if process.returncode != 0:
        logger.error("Render failed or was interrupted. Re-run to resume from the last completed frame.")
        return process.returncode or 1
    if request.frame is None:
        encode_video(request.frames_dir, request.video_path)
    return 0


if __name__ == "__main__":
    sys.exit(run())
