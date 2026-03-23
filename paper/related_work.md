# Related Work — Key Papers to Read

## LLM Forecasting Benchmarks & Performance

1. **ForecastBench: A Dynamic Benchmark of AI Forecasting Capabilities**
   Karger, Bastani, Yueh-Han, Jacobs, Halawi, Zhang, Tetlock. ICLR 2025.
   Continuously-updated benchmark of 1,000 questions. Expert forecasters significantly outperform top LLMs. Projects LLM-superforecaster parity by late 2026.
   https://arxiv.org/abs/2409.19839

2. **Approaching Human-Level Forecasting with Language Models**
   Halawi, Zhang, Yueh-Han, Steinhardt. NeurIPS 2024.
   Retrieval-augmented LLM system tested on 914 questions. Nears crowd aggregate but LLMs are poor zero-shot forecasters.
   https://arxiv.org/abs/2402.18563

3. **Wisdom of the Silicon Crowd: LLM Ensemble Prediction Capabilities Rival Human Crowd Accuracy**
   Schoenegger et al. Science Advances, November 2024.
   Ensemble of 12 LLMs on 31 binary questions matches crowd of 925 human forecasters.
   https://www.science.org/doi/10.1126/sciadv.adp1528

4. **KalshiBench: A New Benchmark for Evaluating Epistemic Calibration via Prediction Markets**
   NeurIPS 2024.
   300 questions from Kalshi. Systematic overconfidence across all frontier LLMs. Enhanced reasoning models show *worse* calibration.
   https://arxiv.org/pdf/2512.16030

5. **Evaluating LLMs on Real-World Forecasting Against Expert Forecasters**
   Lu. July 2025.
   464 Metaculus questions. Experts achieve Brier 0.023 vs o3's 0.135. Narrative/superforecasting prompts hurt performance.
   https://arxiv.org/abs/2507.04562

6. **Future Is Unevenly Distributed: Forecasting Ability of LLMs Depends on What We're Asking**
   November 2025.
   ~10,000 questions across platforms. Forecasting varies sharply by domain. News context helps some domains but hurts others.
   https://arxiv.org/abs/2511.18394

7. **Scaling Open-Ended Reasoning to Predict the Future**
   December 2025.
   52k synthetic forecasting questions (OpenForesight). RL-trained 8B model matches GPT-OSS 120B. Forecasting training reduces hallucinations.
   https://arxiv.org/abs/2512.25070

## LLM Belief Updating & Bayesian Reasoning

8. **Assessing Large Language Models in Updating Their Forecasts with New Information (EVOLVECAST)**
   September 2025.
   Tests whether LLMs revise predictions given post-training-cutoff info. Updates are often inconsistent or overly conservative.
   https://arxiv.org/abs/2509.23936

9. **Are LLM Belief Updates Consistent with Bayes' Theorem?**
   ICML 2025.
   Introduces Bayesian Coherence Coefficient (BCC). Strong correlation between BCC and log(parameters). All models update more consistently than chance but none fully Bayesian.
   https://arxiv.org/abs/2507.17951

10. **Martingale Score: An Unsupervised Metric for Bayesian Rationality in LLM Reasoning**
    NeurIPS 2025.
    Measures violations of the martingale property. Finds widespread "belief entrenchment" — future beliefs are predictable from current beliefs.
    https://arxiv.org/abs/2512.02914

11. **Bayesian Teaching Enables Probabilistic Reasoning in Large Language Models**
    Nature Communications, 2025.
    LLMs fail at Bayesian updating natively but can be taught through exposure to a Bayesian Assistant.
    https://www.nature.com/articles/s41467-025-67998-6

12. **LLMs are Bayesian, In Expectation, Not in Realization**
    July 2025.
    Transformers systematically violate the martingale property. Representative LLMs unable to form and update probabilistic beliefs adequately.
    https://arxiv.org/html/2507.11768v1

## LLM Belief Consistency & Confidence

13. **Do LLMs Act Like Rational Agents? Measuring Belief Coherence in Probabilistic Decision Making**
    February 2026.
    Tests coherence of beliefs vs decisions. LLMs consistently violate complementarity (>5% deviations in >80% of cases). Scaling does not guarantee rationality.
    https://arxiv.org/html/2602.06286

14. **Are LLM Decisions Faithful to Verbal Confidence?**
    January 2026.
    LLMs do not adapt decision policies in response to changing risk. Stated confidence and behavioral decisions are decoupled.
    https://arxiv.org/html/2601.07767v1

15. **Do LLMs Estimate Uncertainty Well in Instruction-Following?**
    ICLR 2025.
    Verbalized confidence is entangled with task execution quality. Internal-state probes outperform both logit-based and verbalized confidence.
    https://proceedings.iclr.cc/paper_files/paper/2025/file/ef472869c217bf693f2d9bbde66a6b07-Paper-Conference.pdf

16. **On Verbalized Confidence Scores for LLMs**
    ICLR 2025.
    Reliability of verbalized confidence depends heavily on prompt method. Well-calibrated scores are possible with right elicitation.
    https://openreview.net/forum?id=CVRdNQvFPE

## Sycophancy & Argument-Driven Shifts

17. **Sycophancy Is Not One Thing: Causal Separation of Sycophantic Behaviors in LLMs**
    September 2025.
    Decomposes sycophancy into agreement vs praise using mechanistic interpretability. These are encoded along distinct linear directions.
    https://arxiv.org/abs/2509.21305

18. **Argument-Driven Sycophancy in Large Language Models**
    Findings of EMNLP 2025.
    Examines how argumentation context affects opinion shifts in multi-turn vs single-turn settings.
    https://aclanthology.org/2025.findings-emnlp.1241.pdf

19. **Anchoring Bias in Large Language Models: An Experimental Study**
    December 2024.
    LLM predictions retain ~37% of the difference between low and high anchors. CoT and reflection are insufficient mitigations.
    https://arxiv.org/abs/2412.06593

## Causal Reasoning in LLMs

20. **Unveiling Causal Reasoning in Large Language Models: Reality or Mirage?**
    NeurIPS 2024.
    Introduces CausalProbe 2024. LLMs only perform shallow (level-1) causal reasoning from parametric memory; lack genuine level-2 reasoning.
    https://proceedings.neurips.cc/paper_files/paper/2024/file/af2bb2b2280d36f8842e440b4e275152-Paper-Conference.pdf

21. **CausalGraph2LLM: Evaluating LLMs for Causal Queries**
    Findings of NAACL 2025.
    700k+ queries across causal graph settings. LLMs highly sensitive to graph encoding format (~60% deviation even for GPT-4).
    https://aclanthology.org/2025.findings-naacl.110/

22. **Large Language Models for Causal Discovery: Current Landscape and Future Directions**
    IJCAI 2025 survey.
    LLMs enhance causal discovery via direct inference, prior knowledge integration, structural refinement. Hybrid LLM + statistical methods needed.
    https://arxiv.org/abs/2402.11068

23. **Think Locally, Explain Globally: Graph-Guided LLM Investigations via Local Reasoning and Belief Propagation**
    January 2026.
    Uses graph structure + belief propagation to guide LLM reasoning. Addresses how ReAct-style agents lack belief bookkeeping/revision.
    https://www.arxiv.org/pdf/2601.17915

## Prompting Strategies for Forecasting

24. **Can Language Models Use Forecasting Strategies?**
    June 2024.
    Tests superforecasting-inspired prompts (base rates, comparison classes, consider-the-opposite). LLM superforecasting approaches do not consistently outperform baselines.
    https://arxiv.org/abs/2406.04446

25. **Prompt Engineering Large Language Models' Forecasting Capabilities**
    June 2025.
    Tests 38 prompts across Claude 3.5, GPT-4o, Llama 405B. Small prompt modifications rarely help. Explicit Bayesian reasoning prompts hurt accuracy.
    https://arxiv.org/abs/2506.01578

---

## Priority Reading Order

**Must read (directly relevant to our contribution):**
- #9 (BCC — ICML 2025) — our Bayesian coherence analysis connects to this
- #10 (Martingale Score — NeurIPS 2025) — our belief entrenchment finding connects to this
- #8 (EVOLVECAST) — closest to our setup, but whole-question not causal-node level
- #1 (ForecastBench — ICLR 2025) — our data source
- #17 (Sycophancy separation) — we need to distinguish structural sensitivity from sycophancy
- #20 (CausalProbe 2024) — tests causal reasoning, we extend to forecasting context
- #21 (CausalGraph2LLM) — causal graph comprehension, complementary

**Should read (important context):**
- #2 (Halawi et al.) — sets the stage for LLM forecasting
- #13 (Belief coherence 2026) — probability axiom violations
- #19 (Anchoring bias) — relevant to our Bayesian coherence finding
- #18 (Argument-driven sycophancy) — our probes are structured arguments

**Good to know (broader context):**
- #3, #4, #5, #6, #7 — other forecasting benchmarks/evaluations
- #11, #12 — Bayesian reasoning limitations
- #22, #23 — causal discovery with LLMs
- #24, #25 — prompting strategies (our superforecasting analysis)
