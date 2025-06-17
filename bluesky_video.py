# You will need to install atproto: pip install atproto
from atproto import AsyncClient
import os

class BlueskyVideo:
    """
    A specialized class to handle video uploads to Bluesky using the atproto library.
    """
    def __init__(self, pds_url: str, handle: str, password: str):
        """
        Initializes the video uploader with an atproto AsyncClient.

        Args:
            pds_url: The URL of the Bluesky PDS (e.g., 'https://bsky.social').
            handle: The user's Bluesky handle.
            password: The user's app password.
        """
        self.client = AsyncClient(base_url=pds_url)
        self._handle = handle
        self._password = password
        self._is_logged_in = False

    async def _ensure_logged_in(self):
        """A private method to ensure the atproto client is logged in before use."""
        if not self._is_logged_in:
            try:
                print("Logging into atproto client for video upload...")
                profile = await self.client.login(self._handle, self._password)
                print(f"atproto client logged in as {profile.handle}.")
                self._is_logged_in = True
            except Exception as e:
                print(f"Failed to log in atproto client: {e}")
                raise

    async def upload(self, media_path: str):
        """
        Uploads a video file from the given path and returns the blob.

        Args:
            media_path: The full local path to the video file.

        Returns:
            The blob object required for embedding, or None if the upload fails.
        """
        if not os.path.exists(media_path):
            print(f"Video file does not exist: {media_path}")
            return None

        try:
            # Ensure the client is authenticated
            await self._ensure_logged_in()

            # Read the video file and upload it
            with open(media_path, 'rb') as f:
                video_data = f.read()
                print(f"Uploading video blob from {media_path}...")
                response = await self.client.com.atproto.repo.upload_blob(video_data)
                print("Video blob uploaded successfully.")
                return response.blob

        except Exception as e:
            print(f"An error occurred during atproto video upload: {e}")
            return None