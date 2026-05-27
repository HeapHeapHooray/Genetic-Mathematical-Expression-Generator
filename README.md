# Genetic Mathematical Expression Generator

An elegant, pure Python program that uses **Genetic Programming (GP)** to discover mathematical formulas that match arbitrary number sequences (both integer and floating-point real numbers).

## Features

- **No External Dependencies**: Pure standard library implementation (fast, lightweight, and works out-of-the-box on any system running Python 3.6+).
- **Real & Integer Sequence Support**: Auto-detects floating-point sequences and adjusts constant boundaries and genetic mutation spaces dynamically.
- **Robust Math Safety**: Employs mathematically protected operations (for division, modulo, power) to prevent division-by-zero, negative bases in fractional powers (which yield complex numbers), and float overflows (`inf`/`nan`).
- **Ramped Half-and-Half Initialization**: Standard Genetic Programming population generation technique utilizing combinations of "full" and "grow" tree configurations.
- **Parsimony Pressure Control**: Integrates a configurable size penalty to favor shorter, cleaner, and more elegant formulas over long, bloated algebraic equivalents.
- **Symbolic Algebraic Simplifier**: Features a recursive symbolic engine that performs algebraic identity reductions (e.g. $x + 0 \to x$, $x \times 0 \to 0$, constant folding, double negation removal) repeatedly to yield human-readable expressions.
- **Vibrant Terminal Visualizations**: Interactive ANSI CLI containing:
  - Real-time evolutionary search progress bar.
  - A nicely formatted side-by-side comparison table of target vs predicted values with error calculation.
  - An **ASCII Line Chart** displaying curves for Target vs. Predicted values in the terminal using vibrant colored icons (●, ▲, ▣).
- **Self-contained Unit Test Suite**: Comprehensive embedded tests verifying AST evaluations, protected operators, simplifications, formatting, and genetic integrity.

---

## Quick Start

### 1. Run the Interactive CLI
Simply run the Python script to open the interactive generator:
```bash
python3 main.py
```
You will be prompted with several preset options (Fibonacci, Quadratic, decaying exponentials, ratios, etc.) or you can input your own arbitrary comma-separated number sequence!

### 2. Run the Automated Test Suite
To verify execution correctness across the math engine and genetic operations, run:
```bash
python3 main.py --test
```

---

## Architectural Details

### 1. Abstract Syntax Tree (AST) Nodes
Mathematical formulas are represented as tree structures:
- `ConstantNode`: Numerical numbers, such as `5` or `-1.618`.
- `VariableNode`: The index variable `n` (0-based or 1-based index).
- `BinaryOpNode`: Algebraic binary operators: `+`, `-`, `*`, `/`, `%`, `**`.
- `UnaryOpNode`: Trigonometric unary operators: `sin`, `cos`.

### 2. Protected Mathematical Operations
To ensure the genetic algorithm does not crash due to mathematical edge cases, operators are wrapped with safety logic:
* **Division (`/`)**: Returns `1.0` if $|divisor| < 10^{-9}$.
* **Modulo (`%`)**: Returns `0.0` if $|divisor| < 10^{-9}$.
* **Power (`**`)**: 
  * Returns `1.0` if base is 0 and exponent is negative.
  * If the base is negative and the exponent is not a whole integer, the absolute value of the base is raised to avoid generating complex numbers.
  * Caps exponent scale to avoid floating-point overflow.
  * Detects and returns `nan` for invalid domains which are heavily penalized by the fitness engine.

### 3. Evolutionary Search Pipeline
* **Selection**: Tournament Selection ($k=5$) selects the fittest candidate for reproduction.
* **Elitism**: Top 2% of the fittest individuals are kept untouched in the next generation to ensure performance monotonically improves.
* **Crossover (Subtree Crossover)**: Swaps random subtrees between two parent trees, discarding attempts that exceed depth limits.
* **Mutation**: Uses three distinct mutations:
  1. **Subtree Mutation (40% weight)**: Replaces a random subtree with a new random mini-tree.
  2. **Point Mutation (40% weight)**: Alters a single node in-place. If a float constant is picked, it applies **Gaussian continuous noise** to fine-tune constant coefficients (e.g. optimizing $1.61$ to $1.618$). If a unary operator is picked, it swaps with the other unary operator.
  3. **Shrink Mutation (20% weight)**: Replaces a node with one of its child nodes or a leaf, reducing formula size.

### 4. Custom Algebraic Simplifier
Standard GP often produces expressions like `((sin(n) + 0) * 1) + 2`. The symbolic engine simplifies this to `sin(n) + 2` by applying recursive reductions:
- **Folding**: $c_1 \text{ op } c_2 \to C_{\text{computed}}$ (e.g., $3 \times 4 \to 12$).
- **Identities**: $x + 0 \to x$, $x - 0 \to x$, $x - x \to 0$, $x \times 1 \to x$, $x \times 0 \to 0$, $x / 1 \to x$, $x / x \to 1$, $x^{1} \to x$, $x^{0} \to 1$.
- **Trig Identities**: $\sin(0) \to 0$, $\cos(0) \to 1$.

---

## File Contents
* **[main.py](file:///home/heap/Documents/Playground/genetic-algo/main.py)**: The complete source code containing AST, Evolution pipeline, Visualizations, and test suites.
* **[README.md](file:///home/heap/Documents/Playground/genetic-algo/README.md)**: User guide and technical specifications (this file).
