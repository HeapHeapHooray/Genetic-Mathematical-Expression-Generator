# Project Memory: Genetic Mathematical Expression Generator

This file serves as a **persistent memory bank** for this codebase. It provides full context, architecture maps, history of what was accomplished, and future directions. If you are a future Gemini or AI assistant loading this project, read this first to understand the state of the system!

---

## 🤖 Project Identity & History
- **Author**: Fully designed, implemented, and refined by **Gemini 3.5 Flash** (via Antigravity).
- **Creation Date**: May 27, 2026.
- **Goal**: Build a pure-Python, zero-dependency Genetic Programming (GP) engine capable of discovering elegant, simplified algebraic formulas for arbitrary integer and floating-point number sequences.

---

## 🛠️ What Has Been Done (Current Capabilities)

We successfully designed and built a production-grade, highly optimized GP pipeline in **[main.py](main.py)**:

### 1. Abstract Syntax Tree (AST) & Operators
- **Nodes**: Superclass `Node` with concrete implementations:
  - `ConstantNode`: Numerical constants (both integers and floating-point reals).
  - `VariableNode`: Sequence index variable `n`.
  - `BinaryOpNode`: Dual-argument operations: `+`, `-`, `*`, `/`, `%`, `**`.
  - `UnaryOpNode`: Single-argument operations: `sin`, `cos`, `round`, `floor`, `ceil`.
- **Protected Mathematical Wrappers**: Full safety barriers ensuring that division/modulo by zero, negative base fractional powers (yielding complex numbers), and intermediate overflows return `nan` gracefully, which are heavily penalized by the fitness engine instead of crashing the run.

### 2. Genetic Evolutionary Pipeline
- **Ramped Half-and-Half Initialization**: Combines recursive "grow" and "full" tree building methodologies across depths $1$ to $4$ to build a genetically diverse initial population.
- **Tournament Selection ($k=5$) & Elitism (2%)**: Keeps selection pressure high while guaranteeing that the fittest individual never degrades across generations.
- **Tree Crossover**: Depth-constrained subtree swapping that prevents tree-depth explosion (bloat).
- **Mutations**: Three distinct structural and continuous mutations:
  1. *Subtree Mutation (40%)*: Swaps a random node with a newly generated mini-tree.
  2. *Point Mutation (40%)*: Alters a single node content in-place. Crucially, **Gaussian continuous noise** is applied to float constants to optimize parameter coefficients (fine-tuning continuous coefficients like $1.61$ to $1.618$).
  3. *Shrink Mutation (20%)*: Compresses tree sizes by replacing a node with its child or a leaf.

### 3. Symbolic Simplification & Formatting
- **Algebraic Simplification Engine**: Recursively reduces expression trees by folding constants and applying standard algebraic identities (e.g. $x + 0 \to x$, $x - x \to 0$, $x \times 0 \to 0$, $\sin(0) \to 0$).
- **Idempotent Simplification**: Correctly reduces nested idempotent unary operators (e.g. $\text{floor}(\text{floor}(x)) \to \text{floor}(x)$).
- **Mathematical Formatter**: Precedence-aware printing logic that honors operator precedence and associativity to output clean formulas with minimal required parentheses (e.g., $2 \times n + 1$ instead of $((2 \times n) + 1)$).

### 4. Vibrant Visualization & Verification
- **ASCII Plotter**: Generates scaled line charts directly in the terminal plotting Target dots (`●`) and Predicted triangles (`▲`), highlighting overlaps as `▣`.
- **Unit Test Suite**: Embedded self-contained testing system with **20 unit tests** checking AST evaluations, safety, simplifications, formatting, and genetic sanity.

---

## 📐 Architecture Map of `main.py`
* **Lines 10-185**: AST Node definitions (`Node`, `ConstantNode`, `VariableNode`, `BinaryOpNode`).
* **Lines 186-258**: `UnaryOpNode` representing trigonometric and rounding functions.
* **Lines 260-366**: Algebraic Simplification Engine (`simplify_step`, `fully_simplify`).
* **Lines 368-450**: Population Initialization (`generate_random_tree`, `init_population`).
* **Lines 452-491**: Fitness Evaluation (`calculate_fitness`) & selection (`tournament_selection`).
* **Lines 493-630**: Genetic Operators (`crossover`, `mutate_subtree`, `mutate_point`, `mutate_shrink`, `mutate`).
* **Lines 632-750**: ASCII Plotter (`draw_ascii_chart`).
* **Lines 752-870**: Evolutionary Loop (`run_gp`).
* **Lines 872-970**: Interactive CLI (`interactive_cli`, presets).
* **Lines 972-1080**: Test Suite (`run_unit_tests`).
* **Lines 1081-1100**: Command Line Argument entry point.

---

## 🔮 Future Roadmap (Plans for the Future)

If you are expanding this codebase, here are the highly recommended planned improvements:

1. **Multi-Variable Functions ($f(x, y)$ or $f(n, x_n)$)**:
   - Expand the program to accept sequences that depend on multiple independent variables, or recursive sequence definitions (where the next term depends on $x_{n-1}$ and $x_{n-2}$).
2. **SymPy / NumPy Fallback Integration**:
   - If SymPy is installed, integrate a fallback parser to print expressions in LaTeX or export to standard SymPy objects for advanced math analysis.
   - Vectorize AST evaluations using NumPy to evaluate population fitness on large datasets instantaneously.
3. **Strongly Typed Genetic Programming (STGP)**:
   - Introduce types to nodes (e.g., integer vs. float vs. boolean), preventing the engine from building invalid operations like `n % sin(n)` or taking the modulo of a fraction.
4. **Parallelized Fitness Evaluation**:
   - Utilize Python's `multiprocessing` library to split the calculation of individual fitnesses across multiple CPU cores, speeding up runs with large population sizes (e.g., $10,000+$).
5. **Standalone Code Exporting**:
   - Implement an export command that translates the champion expression tree into a clean, copy-pasteable lambda function in Python, C, JavaScript, or Matlab.
