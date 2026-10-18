"""Manual stall-protection test. Run it, then gently hold the head while it moves.

Expect an "event: stall" line and the head to stop pushing. Afterwards the
blocked direction stays limited until reset_limits (done at the end here).
"""
import json
import sys
import time

from stackchan import StackChan

with StackChan() as bot:
    bot.reset_limits()
    bot.face("thinking")
    print("Hold the head lightly when it moves. Ctrl+C to stop.", file=sys.stderr)
    try:
        for axis, moves in (("pitch", [(0, 60), (0, 10)] * 3), ("yaw", [(60, 30), (-60, 30)] * 3)):
            print(f"-- {axis}", file=sys.stderr)
            for yaw, pitch in moves:
                bot.pose(yaw, pitch, ms=1200)
                time.sleep(2.0)
                for ev in bot.poll_events():
                    print("event:", json.dumps(ev))
            print("limits now:", json.dumps(bot.state()["limits"]))
    finally:
        bot.reset_limits()
        bot.pose(0, 20, ms=800)
        bot.face("neutral")
