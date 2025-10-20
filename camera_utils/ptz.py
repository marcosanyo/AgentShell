import time
import asyncio
import logging

from onvif import ONVIFCamera
from zeep.exceptions import Fault

logger = logging.getLogger(__name__)


class PTZController:
    """PTZ (Pan-Tilt-Zoom) control class"""

    def __init__(self, onvif_camera: ONVIFCamera):
        self.onvif_camera = onvif_camera
        self.ptz_service = None
        self.media_service = None
        self.media_profile = None
        self.is_connected = False

    async def connect(self) -> bool:
        """Connect to camera and initialize"""
        try:
            # Create services
            self.media_service = self.onvif_camera.create_media_service()
            self.ptz_service = self.onvif_camera.create_ptz_service()

            # Get the first media profile
            profiles = self.media_service.GetProfiles()
            if not profiles:
                logger.error("No media profiles found")
                return False

            self.media_profile = profiles[0]
            self.is_connected = True
            logger.info("PTZ Controller connected successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to connect PTZ Controller: {e}")
            self.is_connected = False
            return False

    async def move_absolute(
        self,
        pan: float = 0.0,
        tilt: float = 0.0,
        zoom: float = 0.0,
        wait_seconds: float = 2.0,
    ) -> bool:
        """Move to absolute position and wait for specified duration"""
        if not self.is_connected:
            logger.error("PTZ Controller not connected")
            return False

        try:
            self.ptz_service.AbsoluteMove(
                {
                    "ProfileToken": self.media_profile.token,
                    "Position": {"PanTilt": {"x": pan, "y": tilt}, "Zoom": {"x": zoom}},
                }
            )

            # Wait for a specified duration to allow the camera to complete its movement.
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)

            logger.info(f"Completed absolute move to pan={pan}, tilt={tilt}")
            return True

        except Exception as e:
            logger.error(f"Failed to move to absolute position: {e}")
            return False

    async def get_position(self) -> dict:
        """Get current position"""
        if not self.is_connected:
            logger.error("PTZ Controller not connected")
            return {}

        try:
            status = self.ptz_service.GetStatus({
                "ProfileToken": self.media_profile.token
            })

            if status and status.Position:
                position = {
                    "pan": status.Position.PanTilt.x if status.Position.PanTilt else 0.0,
                    "tilt": status.Position.PanTilt.y if status.Position.PanTilt else 0.0,
                    "zoom": status.Position.Zoom.x if status.Position.Zoom else 0.0
                }
                return position

            return {}

        except Exception as e:
            logger.error(f"Failed to get position: {e}")
            return {}

    async def disconnect(self):
        """Disconnect"""
        self.is_connected = False
        self.ptz_service = None
        self.media_service = None
        self.media_profile = None
        logger.info("PTZ Controller disconnected")


def ptz_control(ip, port, user, password):
    """Connects to an ONVIF camera and performs PTZ (Pan-Tilt-Zoom) movements."""
    try:
        print(f"Connecting to camera at {ip}:{port}...")
        camera = ONVIFCamera(ip, port, user, password)
        print("Successfully connected to the camera.")

        # Create media service
        media_service = camera.create_media_service()

        # Get the first media profile
        profiles = media_service.GetProfiles()
        if not profiles:
            print("No media profiles found.")
            return
        media_profile = profiles[0]

        # Create PTZ service
        ptz_service = camera.create_ptz_service()

        # Get PTZ configuration options
        request = ptz_service.create_type("GetConfigurationOptions")
        request.ConfigurationToken = media_profile.PTZConfiguration.token
        ptz_configuration_options = ptz_service.GetConfigurationOptions(request)

        # --- Absolute Move ---
        print("Performing AbsoluteMove...")

        # Define positions to move to
        positions = {
            "Center": {"x": 0, "y": 0},
            "Top-Left": {"x": -0.5, "y": 0.5},
            "Bottom-Right": {"x": 0.5, "y": -0.5},
        }

        # Note: If the camera image is inverted, you might need to negate the x and y values.

        for name, pos in positions.items():
            print(f"Moving to {name} at (x={pos['x']}, y={pos['y']})...")
            ptz_service.AbsoluteMove(
                {"ProfileToken": media_profile.token, "Position": {"PanTilt": pos}}
            )
            # Wait for the move to complete. Adjust sleep time if necessary.
            time.sleep(3)
            print("Move complete.")

        # Return to center
        print("Returning to Center...")
        ptz_service.AbsoluteMove(
            {
                "ProfileToken": media_profile.token,
                "Position": {"PanTilt": positions["Center"]},
            }
        )
        time.sleep(3)
        print("Move complete.")

        print("PTZ control test finished.")

    except Fault as e:
        print(f"ONVIF Fault: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    # --- Camera Credentials ---
    # Set these via environment variables: CAMERA_IP, CAMERA_PORT, CAMERA_USER, CAMERA_PASSWORD
    import os
    IP_ADDRESS = os.getenv("CAMERA_IP", "192.168.11.34")
    PORT = int(os.getenv("CAMERA_PORT", "2020"))
    USERNAME = os.getenv("CAMERA_USER", "admin")
    PASSWORD = os.getenv("CAMERA_PASSWORD", "")

    if not PASSWORD:
        raise ValueError("CAMERA_PASSWORD environment variable must be set")

    ptz_control(IP_ADDRESS, PORT, USERNAME, PASSWORD)
