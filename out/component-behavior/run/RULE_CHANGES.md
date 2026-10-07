# Behavior audit rule changes

Changes use a fenced `rule-change` JSON object containing old_sha256, new_sha256, classification (`add` or `tighten`), reason and reviewer.

```rule-change
{
  "id": "RULE_CHANGE-001",
  "old_sha256": "730f651999bc31c7e9db55deb1beac59d05da9aa2d9d9a89ec6f1f20eb53a1c7",
  "new_sha256": "f240b5f2beb9b8d56d2901fa5b663c5d877d0d6c68c84209b8e61301aafc21d3",
  "classification": "tighten",
  "reason": "Add the complete Stage 1 fast repository gate to every checkpoint, in addition to the existing focused and UI regressions. The first checkpoint ran focused regressions only; this corrects that omission without removing a check or changing any expected value, tolerance, canary or baseline.",
  "reviewer": "implementation-agent; listed for final human review"
}
```
