import psutil
import time


class NetworkMonitor:
    def __init__(self, interface="All"):
        self.interface = interface
        self._last = self._get_counts()
        self._last_time = time.time()

    def _get_counts(self):
        counters = psutil.net_io_counters(pernic=True)
        if self.interface == "All":
            total = psutil.net_io_counters()
            return total.bytes_sent, total.bytes_recv
        else:
            nic = counters.get(self.interface)
            return (nic.bytes_sent, nic.bytes_recv) if nic else (0, 0)

    def get_speed(self):
        now = time.time()
        sent, recv = self._get_counts()
        dt = now - self._last_time
        sent_speed = (sent - self._last[0]) / dt
        recv_speed = (recv - self._last[1]) / dt
        self._last = (sent, recv)
        self._last_time = now
        return sent_speed, recv_speed

    @staticmethod
    def list_interfaces():
        return ["All"] + list(psutil.net_io_counters(pernic=True).keys())
