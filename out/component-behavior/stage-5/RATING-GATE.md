# Stage5 ratings and failure gate

Executable receipt validation: PASS.
331 class rating/failure declarations preserved across 66 classes.

Four actual ngspice42 probes exercise within-limit, violation, explicit modeled-open rerun and unknown mounting conditions. All source statuses and locked analytical contracts remain unchanged.

Stage acceptance remains partial: transient peak/RMS/pulse-energy checks, reference thermal context, unbound classes and nonquantitative failure responses remain unknown. No duration or physical damage outcome is invented.

- within_stated_conditions: simulation ran; ratings within_model_limits; failure rerun False.
- over_voltage: simulation ran; ratings violation; failure rerun False.
- modeled_open: simulation ran; ratings violation; failure rerun True.
- unknown_mounting: simulation ran; ratings unknown; failure rerun False.

Instrumented62-reference validation: {'evidence_errors': [], 'comparison_passed': 57, 'comparison_failed': 5}. The five analytical failures are the unchanged diode temperature contracts.
