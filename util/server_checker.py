import subprocess


async def can_connect_ssh(server_ip: str) -> bool:
    """
    Check if we can establish an SSH connection to the server with the given IP.

    Parameters
    ----------
    server_ip: `str`
        The IP of the server

    Returns
    -------
    `bool`
        True if the given IP is valid and if an SSH connection can be established; False otherwise
    """

    try:
        # Command from https://stackoverflow.com/a/47166507
        output = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "PubkeyAuthentication=no", "-o",
                                 "PasswordAuthentication=no", "-o", "KbdInteractiveAuthentication=no",
                                 "-o", "ChallengeResponseAuthentication=no", server_ip,
                                 "2>&1"], capture_output=True, timeout=5).stderr.decode("utf-8")

        return "Permission denied" in output or "verification failed" in output
    except subprocess.TimeoutExpired:
        return False
