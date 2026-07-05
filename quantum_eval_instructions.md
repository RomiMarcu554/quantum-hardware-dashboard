# Quantum Hardware Literature Evaluation — Skill Instructions

---

## 1. Purpose

This skill receives a scientific paper as a PDF file and extracts quantum hardware parameter values from it into the appropriate platform database (Excel file). It operates in five sequential steps: platform identification, parameter discovery from the live database columns, disqualification gating, reliability scoring, and output.

The skill must never invent, estimate, or infer values. It only records what is explicitly stated or unambiguously shown in the paper text or figures.

---

## 2. Database File Paths

| Platform | File path |
|----------|-----------|
| Superconducting Circuits | `/Users/romimarcu/שנה ד סמסטר ב/project -Sivan - claude/Final/Superconducting Circuits.xlsx` |
| Trapped Ions | `/Users/romimarcu/שנה ד סמסטר ב/project -Sivan - claude/Final/Trapped Ions.xlsx` |
| Neutral Atoms | `/Users/romimarcu/שנה ד סמסטר ב/project -Sivan - claude/Final/Neutral Atoms.xlsx` |
| Photonics | `/Users/romimarcu/שנה ד סמסטר ב/project -Sivan - claude/Final/Photonics.xlsx` |

---

## 3. Step 1 — Platform Identification

Identify which hardware platform the paper reports experiments on. Use the keyword lists below as guidance, but also rely on the overall context of the paper — do not keyword-match blindly.

**Superconducting Circuits**
Transmon, fluxonium, charge qubit, circuit QED, Josephson junction, superconducting qubit, dilution refrigerator, dispersive readout, parametric amplifier, SQUID, cross-resonance gate, CZ gate via flux tuning

**Trapped Ions**
Ion trap, Paul trap, linear trap, surface trap, ⁴⁰Ca⁺, ⁴³Ca⁺, ¹⁷¹Yb⁺, ⁹Be⁺, ⁸⁸Sr⁺, hyperfine qubit, optical qubit, Mølmer-Sørensen gate, fluorescence detection, laser-cooled ions, microwave-driven gates

**Neutral Atoms**
Optical tweezer, optical lattice, Rydberg, neutral atom, ultracold atoms, MOT (magneto-optical trap), ⁸⁷Rb, ¹³³Cs, ⁸⁸Sr, ¹⁷⁴Yb, tweezer array, Rydberg blockade, CZ gate via Rydberg

**Photonics**
Single photon, photonic qubit, linear optical, SPDC (spontaneous parametric downconversion), quantum dot photon source, Hong-Ou-Mandel (HOM), beamsplitter, SNSPD, photon indistinguishability, optical fiber, silicon photonics, boson sampling, measurement-based quantum computing (MBQC)

**If the platform cannot be identified** → the paper-level gate "Platform clearly identified" fails → stop, do not proceed.

**If a paper reports experiments on more than one platform** → treat each platform independently: run the full extraction process once per platform and write to each relevant database file separately.

---

## 4. Step 2 — Read Target Parameters from the Database

Open the Excel file for the identified platform. Read all column headers from row 1.

- Columns 1–6 are fixed metadata (**Paper Title, Authors, Research Group / Institution, Journal, Year, URL**). These are not parameters to search for.
- Every column from column 7 onward is a **parameter to search for** in the paper.

**This list is dynamic.** Do not use a hardcoded parameter list. Always read the actual column headers from the Excel file at run time. If a new column has been added since the last run, it will automatically be included.

---

## 5. Step 3 — Stage 1: Disqualification Gates

### 5.1 Paper-Level Gates

Checked once for the whole paper, before any parameter extraction. If any one of these fails, stop — do not extract anything from this paper.

---

**Gate 1: Quantum hardware characterization**

Passes if: The paper reports experimental measurements performed on a physical quantum hardware system.

Fails if: The paper contains only:
- Numerical simulations or computational modeling with no physical experiment
- Theoretical derivations or proposals with no experimental section
- Reviews or surveys of other papers' results (secondary sources)

A paper that combines theory AND experiment passes this gate if the experimental section reports original measurements.

---

**Gate 2: Platform clearly identified**

Passes if: Step 1 succeeded and the hardware platform is unambiguous.

Fails if: The paper describes hardware that does not clearly belong to any of the four supported platforms, or if the experimental platform is never stated.

---

**Gate 3: Sufficient experimental detail**

Passes if: The paper describes, at minimum, how the measurements were performed — including what was measured, the general procedure or apparatus, and the experimental conditions. The description does not need to be exhaustive, but it must allow a reader to understand how the reported numbers were obtained.

Fails if:
- The paper states results as conclusions only (e.g., "we achieved T₁ = 100 µs") with no description of how the measurement was done anywhere in the paper, appendix, or supplementary material
- The paper redirects entirely to another paper for the methodology with no summary provided

---

### 5.2 Parameter-Level Gates

Checked for each parameter column individually. A parameter that fails either gate is left empty — no value, no score is written. If the parameter is not mentioned in the paper at all, leave the cell empty.

---

**Gate 4: Valid units**

The reported value must carry units that are physically appropriate for that parameter. Use the reference table below.

| Parameter | Valid units | Notes |
|-----------|------------|-------|
| T₁ | µs, ms, s | ns is acceptable only for photonic loss analogues; flag if ns reported for SC/TI/NA |
| T₂* (Ramsey) | µs, ms, s | Same as T₁ |
| T₂ (Hahn Echo) | µs, ms, s | Same as T₁ |
| T₂ (CPMG) | µs, ms, s | Same as T₁ |
| Single-Qubit Gate Fidelity | % or dimensionless [0, 1] | Must not exceed 100% or 1.0 |
| Single-Qubit Gate Time | ns (SC), µs (TI, NA) | ms is unusual and should be noted |
| Two-Qubit Gate Fidelity | % or dimensionless [0, 1] | Must not exceed 100% or 1.0 |
| Two-Qubit Gate Time | ns–µs (SC), µs–ms (TI, NA) | |
| Readout Fidelity | % or dimensionless [0, 1] | Must not exceed 100% or 1.0 |
| Readout Time | ns–µs (SC), µs–ms (TI, NA) | |
| Transport Time | µs, ms | Neutral atoms only |
| Photon Indistinguishability (HOM Visibility) | % or dimensionless [0, 1] | |
| Single-Photon Purity — g²(0) | Dimensionless | Valid range [0, 2]; ideal single photon = 0 |
| Detector Efficiency | % or dimensionless [0, 1] | |
| Dark Count Rate | Hz, kHz, counts per second | |
| Photon Loss Rate | dB/km, dB/cm, or dB per component | Must include what the denominator refers to (per meter, per element, etc.) |
| Coupling / Collection Efficiency | % or dimensionless [0, 1] | |

Fails if: No units are stated, or the stated units are not in the valid list for that parameter.

---

**Gate 5: Measurement protocol identified**

The method used to obtain the value must be stated, described, cited, or unambiguously inferable from a labeled figure in the paper. Use the reference table below to know which protocols are valid for each parameter.

| Parameter | Valid protocols / how it is measured |
|-----------|--------------------------------------|
| T₁ | Inversion-recovery experiment: qubit initialized to excited state, delay time varied, excited-state population fitted to exponential decay. May be named "T₁ measurement," "energy relaxation," or shown as an exponential decay curve vs. delay time labeled "T₁." |
| T₂* (Ramsey) | Ramsey interferometry / free induction decay: two π/2 pulses separated by a variable delay, with no refocusing pulse. Must be labeled "Ramsey," "T₂*," or shown as an oscillating-decaying signal vs. delay. |
| T₂ (Hahn Echo) | Hahn echo / spin echo: a single π refocusing pulse placed between the two π/2 pulses. Must be labeled "echo," "Hahn echo," "T₂ (echo)," or show the single-refocusing-pulse sequence. |
| T₂ (CPMG) | CPMG / dynamical decoupling: multiple refocusing pulses applied during the delay. Must name "CPMG," "dynamical decoupling," "DD," or specify the number of π pulses used. |
| Single-Qubit Gate Fidelity | Randomized Benchmarking (RB), Interleaved RB (IRB), Gate Set Tomography (GST), Process Tomography (QPT), or Cross-Entropy Benchmarking (XEB). The protocol name must be stated or cited. |
| Two-Qubit Gate Fidelity | Same as single-qubit gate fidelity protocols. The specific two-qubit gate being characterized must be identified (CNOT, CZ, iSWAP, Mølmer-Sørensen, Rydberg CZ, etc.). |
| Single-Qubit Gate Time | The specific gate (e.g., π pulse, X gate, DRAG pulse) and its duration must be stated. |
| Two-Qubit Gate Time | The specific two-qubit gate and its duration must be stated. |
| Readout Fidelity | Single-shot state discrimination: the paper must describe the readout mechanism (dispersive readout for SC; fluorescence detection for TI/NA; single-photon detection for photonics) and state how the fidelity is defined (e.g., F = 1 − P(e\|g) − P(g\|e), or assignment fidelity). |
| Readout Time | The readout integration window or measurement duration must be explicitly stated. |
| Transport Time | The time to physically move an atom or ion between trapping sites must be stated and associated with a specific transport operation. |
| Photon Indistinguishability (HOM Visibility) | Hong-Ou-Mandel (HOM) interference experiment: two photons interfered on a beamsplitter, coincidence counts measured. Must name "HOM," "indistinguishability," or "two-photon interference." |
| Single-Photon Purity — g²(0) | Hanbury Brown–Twiss (HBT) experiment / second-order autocorrelation measurement. Must name "g²(0)," "autocorrelation," or "HBT." |
| Detector Efficiency | The probability of detecting a photon that arrives at the detector. Must be stated as a percentage or fraction associated with a specific detector type. |
| Dark Count Rate | False detection events per unit time in the absence of signal photons. Must be stated with a time unit (per second, per measurement window). |
| Photon Loss Rate | Optical transmission loss. Must state the loss value AND the medium or path length it applies to. A loss rate without context (e.g., "0.5 dB" with no reference to per-cm or per-element) fails this gate. |
| Coupling / Collection Efficiency | The fraction of photons successfully coupled into or collected from the optical mode of interest. Must be stated as a percentage or fraction. |

**Inferred protocols:** If the paper does not name the protocol explicitly but shows a clearly labeled figure from which the protocol is unambiguous (e.g., an exponential decay curve labeled "T₁" with delay time on the x-axis), the protocol is considered identifiable and the gate passes. Add a note in the cell: "(protocol inferred from figure)".

Fails if: No measurement method is named, described, cited, or inferable from a labeled figure.

---

## 6. Step 4 — Stage 2: Reliability Scoring

Applied only to parameters that passed all five Stage 1 gates.

Every parameter starts at a score of **10**. Check each flag below and subtract the stated deduction if the flag applies. Multiple flags can apply to the same parameter.

**Final score = 10 − sum of applicable deductions. Minimum = 0.**

---

**Flag 1 — Undemonstrated scalability claims (−4)**

Applies to the parameter if: The paper makes a **specific claim** that a result demonstrated in the paper — a measured value, a technique, or a demonstrated approach — will hold at a larger qubit or photon count, in a multiplexed architecture, or in a different system configuration, **without providing experimental demonstration of that scaling in the paper itself**.

The key test: does the paper link a **specific reported result** to a larger or different system, without demonstrating it? If yes → flag.

Concrete examples that **trigger** this flag:
- "Our readout scheme is expected to be compatible with multiplexed architectures" — flag (claims the readout result transfers to a different architecture)
- "This gate fidelity should scale to 50-qubit systems" — flag (claims the fidelity value holds at larger scale)
- "We demonstrated this on 2 qubits; the approach generalizes to N qubits" — flag (unless the N-qubit data is also in the paper)

Concrete examples that **do NOT trigger** this flag:
- General background motivation: "Ion traps are a promising platform for large-scale quantum computing" — does NOT flag (this is a field-level statement, not a claim about this paper's specific results)
- Future hope: "We hope future improvements will increase fidelity" — does NOT flag (no specific result is being linked to a larger system)
- Comparison context: "Our result is comparable to state-of-the-art systems" — does NOT flag

**The distinction:** A general statement that a technology or field is promising for scaling is NOT the same as claiming that a specific measured result in this paper will hold at larger scale. Only the latter triggers this flag.

Does NOT trigger if: The paper demonstrates the result at the claimed scale experimentally within the same paper.

Note: This flag is assessed at the paper level but applied to each parameter entry. If the paper contains a qualifying scalability claim, subtract −4 from every parameter extracted from that paper.

---

**Flag 2 — Raw vs. corrected values (−3)**

Applies to: **Readout Fidelity, Single-Qubit Gate Fidelity, Two-Qubit Gate Fidelity** only.
Does not apply to coherence times, gate times, readout time, or photon source metrics.

Triggered if any of the following is true:
- The paper reports a fidelity or error rate but does not state whether the value is raw (direct hardware measurement) or corrected (a calibration matrix or post-processing correction has been applied)
- The paper reports only a software-corrected fidelity value for a claim about hardware performance, with no raw value provided

Does NOT trigger if:
- The paper explicitly states the value is raw (e.g., "raw assignment fidelity," "uncorrected readout error")
- The paper explicitly states the value is corrected AND also reports the raw value alongside it
- The paper provides the full definition of how the fidelity was calculated (e.g., the formula F = 1 − P(e|g) − P(g|e) applied directly to measurement outcomes, with no correction matrix applied)

---

**Flag 3 — Design parameter vs. fitted parameter (−2)**

Triggered if: The value is a quantity the experimenter programmed or chose, not a quantity extracted from fitting experimental data.

The following columns are almost always design parameters — apply this flag by default unless the paper explicitly demonstrates that the value was optimized or characterized experimentally:
- Single-Qubit Gate Time
- Two-Qubit Gate Time
- Readout Time
- Transport Time

The following columns are almost always fitted/measured quantities — do not apply this flag unless the paper explicitly states the value is a design choice:
- T₁, T₂* (Ramsey), T₂ (Hahn Echo), T₂ (CPMG)
- Single-Qubit Gate Fidelity, Two-Qubit Gate Fidelity
- Readout Fidelity
- All photonic parameters

---

**Flag 4 — Incidental vs. primary parameter (−1)**

Triggered if: The value appears only as background context or a supporting detail, and characterizing this parameter is not a stated goal of the paper.

Concrete examples that trigger this flag:
- A readout paper mentions "our qubit has T₁ = 7.6 µs" in one sentence with no decay curve, no fit details, and no further discussion → T₁ is incidental
- A coherence paper mentions "we used an 18 ns DRAG pulse for state preparation" with no gate fidelity measurement → gate time is incidental
- A gate fidelity paper mentions readout fidelity only as a footnote → readout fidelity is incidental

Does NOT trigger if:
- The paper's title, abstract, or conclusion identifies this parameter as a primary result
- The paper dedicates a section, figure, or supplementary material to characterizing this parameter
- The paper's main narrative depends on this parameter value

---

## 7. Step 5 — Output to Database

### 7.1 Cell format

Each parameter value is written into its column cell in the following format, all in one cell:

```
value ± uncertainty (F1, F2, F3, F4, total)
```

The parenthetical contains **five comma-separated numbers**:
- **F1**: deduction from Flag 1 (0 if not applied, −4 if applied)
- **F2**: deduction from Flag 2 (0 if not applied, −3 if applied)
- **F3**: deduction from Flag 3 (0 if not applied, −2 if applied)
- **F4**: deduction from Flag 4 (0 if not applied, −1 if applied)
- **total**: the final reliability score (10 + F1 + F2 + F3 + F4, minimum 0)

Examples:
- With uncertainty, no flags: `98.42 ± 0.07% (0,0,0,0,10)`
- With uncertainty, Flag 2 applied: `0.973 ± 0.002 (0,-3,0,0,7)`
- No uncertainty, Flags 3 and 4 applied: `10 µs (0,0,-2,-1,7)`
- Approximate value from paper, Flag 3 applied: `~200 µs (0,0,-2,0,8)`
- With inferred protocol: `7.6 µs (0,0,0,-1,9) [protocol inferred]`

**On approximate values:** If the paper states a value as approximate (e.g., "approximately 200 µs") and no more precise value or range is given anywhere in the paper, write the value using the `~` symbol (e.g., `~200 µs`). Do not write the word "approximately." Do not invent a more precise number. An approximate value does **not** fail any gate — it is recorded as-is. If the paper gives a range (e.g., "600–700 µs"), write the range exactly as stated.

- If the parameter failed a gate or was not found in the paper → leave the cell **empty** (no value, no score)

### 7.2 Row structure

Each row = one source paper.

Fill the six metadata columns:
| Column | What to write |
|--------|--------------|
| Paper Title | Full title as written in the paper |
| Authors | Full author list |
| Research Group / Institution | Laboratory or university affiliation |
| Journal | Leave empty — the user fills this in |
| Year | Publication year as a number |
| URL | Leave empty — the user fills this in |

Then fill each parameter column with its value in the format above.

Always append a new row at the bottom of the existing data. Never overwrite an existing row.

### 7.3 Multiple values for one parameter

If the paper reports more than one value for the same parameter (e.g., readout fidelity at three different operating points), write the primary or most precisely stated value. If other values are relevant, note them in the same cell:

```
98.42 ± 0.07% (also: 98.25%, 99.2%) (0,0,0,0,10)
```

---

## 8. Execution Order Summary

```
1. Identify platform → select the correct Excel file
2. Read column headers from that file (columns 7 onward) → build parameter list dynamically
3. Check paper-level gates (Gates 1–3):
      → Any fail: stop entirely, do not extract
4. For each parameter column:
      a. Search the paper for that value
      b. Check Gate 4 (valid units) → fail: leave empty
      c. Check Gate 5 (protocol identified) → fail: leave empty
      d. Calculate reliability score:
            Start at 10
            Flag 1 (specific scalability claim for this result): −4
            Flag 2 (raw/corrected ambiguous, fidelity params only): −3
            Flag 3 (design parameter, applies to gate/readout times): −2
            Flag 4 (incidental mention): −1
      e. Write: value ± uncertainty (F1, F2, F3, F4, total) into the cell
            where F1–F4 are 0 or the negative deduction, and total = 10+F1+F2+F3+F4
5. Write metadata into columns 1–6
6. Append the completed row to the bottom of the database
```
