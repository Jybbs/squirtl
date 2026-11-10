"""
Defines `GitHub`, which stands in for GitHub's REST API and the
files its releases attach, answering each address `urlopen` reads in
`squirtl.releases.schemas` without reaching the network.
"""

from email.message  import Message
from hashlib        import sha256
from io             import BytesIO
from json           import dumps
from urllib.error   import HTTPError
from urllib.request import Request

from squirtl.releases.schemas import ReleaseManifest

ADDRESS = "https://api.github.com/repos/Jybbs/squirtl/releases"


class GitHub:
    """
    Answers each address from `served`, raising GitHub's 404 for any other,
    and records the User-Agent of each request in `agents`.
    """

    def __call__(self, request: Request) -> BytesIO:
        """
        Answers `request` from `served`, as `urlopen` would.

        Raises:
            HTTPError: Where `served` holds nothing at the request's
                       address.
        """
        self.agents.append(request.get_header("User-agent"))

        if request.full_url not in self.served:
            raise HTTPError(request.full_url, 404, "Not Found", Message(), BytesIO())

        return BytesIO(self.served[request.full_url])

    def __init__(self):
        """
        Starts serving nothing.
        """
        self.agents = []
        self.served = {}

    def publish(self, manifest: ReleaseManifest, tag: str = "0.2.0"):
        """
        Publishes the release `tag`, as the latest release and under its
        tag, attaching every file `manifest` lists, each under the digest
        GitHub computes for it.
        """
        assets = []

        for path in manifest.files:
            url = f"https://example.invalid/{path.name}"
            body = self.served[url] = path.read_bytes()
            assets.append(
                {
                    "browser_download_url" : url,
                    "digest"               : f"sha256:{sha256(body).hexdigest()}",
                    "name"                 : path.name,
                    "size"                 : len(body)
                }
            )

        self.served[f"{ADDRESS}/latest"] = self.served[f"{ADDRESS}/tags/{tag}"] = dumps(
            {"assets": assets, "published_at": "2026-11-10T00:00:00Z", "tag_name": tag}
        ).encode()
