# Archived Feb 12, 2026

Scripts superseded by the current multi-scenario and persona-CoT experiment framework.

| File | Superseded By | Reason |
|------|--------------|--------|
| `run_collapse_sharding_comparison.py` | `run_multiscenario_experiment.py` | Single-scenario 3-condition comparison replaced by 50-scenario paired design |
| `run_action_probability_experiment.py` | `run_action_prediction_experiment.py` | Old 5-target-action approach replaced by sampled action pool design |
| `run_information_sharding_experiment.py` | `run_multiscenario_experiment.py` | Early sharding baseline replaced by multi-scenario framework |
| `run_persona_rewrite_experiment.py` | `run_persona_cot_experiment.py` | Context rewriting approach replaced by CoT bridging approach |
| `persona_rewrite.py` | `run_persona_cot_experiment.py` | Rewrite engine no longer needed; bridging CoT uses inline persona instructions |
| `persona_generator.py` | `persona_simplified.py` | Complex 24-attribute CognitiveProfile replaced by 7-attribute SimplifiedProfile |
| `action_probability_prompts.py` | `run_action_prediction_experiment.py` | Prompts now generated inline in the experiment script |
| `persona_profiles.json` | `persona_profiles_simplified.json` | Complex persona pool replaced by simplified personas |
