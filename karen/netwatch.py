import asyncio, socket

class NetWatch:
    def __init__(self, host='1.1.1.1', port=53, timeout=0.6):
        self.host, self.port, self.timeout = host, port, timeout

    async def ok(self):
        try:
            fut = asyncio.get_running_loop().run_in_executor(
                None,
                self._try_connect
            )
            await asyncio.wait_for(fut, timeout=self.timeout+0.2)
            return True
        except Exception:
            return False

    def _try_connect(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(self.timeout)
            s.connect((self.host, self.port))
