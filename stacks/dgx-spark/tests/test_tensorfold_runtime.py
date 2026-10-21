"""Run inside the built image against TensorFold's installed scheduler, without a GPU."""

from types import SimpleNamespace
import unittest

from tensorfold.families.qwen4_exp.cuda.multi import MultiDecoder


class SchedulerTests(unittest.TestCase):
    def test_completed_short_prefill_returns_before_unrelated_long_prefill(self):
        decoder = object.__new__(MultiDecoder)
        short, long = object(), object()
        decoder.filling, decoder.streams = [short, long], {}
        decoder.arrived = lambda: False
        calls = []

        def run_pass():
            calls.append(True)
            done = decoder.filling.pop(0)
            return [done]

        decoder._pass = run_pass
        self.assertEqual(decoder._fill(), [short])
        self.assertEqual(decoder.filling, [long])
        self.assertEqual(len(calls), 1)

    def test_round_releases_completed_requests_before_another_decode_pass(self):
        decoder = object.__new__(MultiDecoder)
        done = object()
        decoder.filling, decoder.streams, decoder.converged = [object()], {}, True
        decoder._make_room = lambda: []

        def fill():
            decoder.streams[1] = SimpleNamespace(done=False, waiting=False)
            return [done]

        decoder._fill = fill
        self.assertEqual(decoder.round(), [done])


if __name__ == "__main__":
    unittest.main()
