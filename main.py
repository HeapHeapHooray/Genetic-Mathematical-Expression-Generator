#!/usr/bin/env python3
import random
import math
import sys
import argparse

# =====================================================================
# 1. AST Node Structure & Evaluation
# =====================================================================

class Node:
    """Base class for all Abstract Syntax Tree (AST) nodes."""
    def evaluate(self, n):
        raise NotImplementedError
        
    def clone(self):
        raise NotImplementedError
        
    def __str__(self):
        raise NotImplementedError

    def to_formatted_string(self):
        raise NotImplementedError

    def get_nodes_with_relations(self, parent=None, rel_idx=0):
        """
        Gathers all subnodes recursively along with parent references 
        and child relation indices (0 for left, 1 for right).
        Used for easy subtree replacement in crossover and mutation.
        """
        raise NotImplementedError

    def size(self):
        """Returns the total number of nodes in this subtree."""
        raise NotImplementedError

    def depth(self):
        """Returns the maximum depth of this subtree."""
        raise NotImplementedError


class ConstantNode(Node):
    """Represents a constant numerical value (int or float)."""
    def __init__(self, value):
        self.value = value
        
    def evaluate(self, n):
        return float(self.value)
        
    def clone(self):
        return ConstantNode(self.value)
        
    def __str__(self):
        if isinstance(self.value, float):
            if self.value.is_integer():
                return str(int(self.value))
            return f"{self.value:.4f}".rstrip('0').rstrip('.')
        return str(self.value)

    def to_formatted_string(self):
        return str(self)

    def get_nodes_with_relations(self, parent=None, rel_idx=0):
        return [(self, parent, rel_idx)]

    def size(self):
        return 1

    def depth(self):
        return 0


class VariableNode(Node):
    """Represents the sequence index variable 'n'."""
    def __init__(self, name='n'):
        self.name = name
        
    def evaluate(self, n):
        return float(n)
        
    def clone(self):
        return VariableNode(self.name)
        
    def __str__(self):
        return self.name

    def to_formatted_string(self):
        return self.name

    def get_nodes_with_relations(self, parent=None, rel_idx=0):
        return [(self, parent, rel_idx)]

    def size(self):
        return 1

    def depth(self):
        return 0


class BinaryOpNode(Node):
    """Represents a binary operator (+, -, *, /, %, **)."""
    def __init__(self, op, left, right):
        self.op = op  # '+', '-', '*', '/', '%', '**'
        self.left = left
        self.right = right
        
    def evaluate(self, n):
        l_val = self.left.evaluate(n)
        r_val = self.right.evaluate(n)
        
        # Check for invalid values in children
        if math.isnan(l_val) or math.isinf(l_val) or math.isnan(r_val) or math.isinf(r_val):
            return float('nan')
            
        # Protect mathematical operations from overflows/domain errors
        try:
            if self.op == '+':
                val = l_val + r_val
            elif self.op == '-':
                val = l_val - r_val
            elif self.op == '*':
                val = l_val * r_val
            elif self.op == '/':
                # Protected division: return 1.0 if divisor is very close to 0
                if abs(r_val) < 1e-9:
                    return 1.0
                val = l_val / r_val
            elif self.op == '%':
                # Protected modulo
                if abs(r_val) < 1e-9:
                    return 0.0
                val = l_val % r_val
            elif self.op == '**':
                # Protected power operation to avoid complex numbers & overflow
                # 1. Cap exponent magnitude to prevent massive overflows
                if abs(r_val) > 100 or (abs(l_val) > 1.0 and r_val > 50):
                    return float('nan')
                # 2. Prevent division-by-zero for negative powers
                if abs(l_val) < 1e-9 and r_val < 0:
                    return 1.0
                # 3. Real math check: negative base raised to fractional exponent
                if l_val < 0:
                    # Check if exponent is very close to an integer
                    if abs(r_val - round(r_val)) > 1e-6:
                        # Fallback: take absolute value of base to avoid complex numbers
                        val = abs(l_val) ** r_val
                    else:
                        val = l_val ** int(round(r_val))
                else:
                    val = l_val ** r_val
            else:
                return float('nan')
        except (OverflowError, ZeroDivisionError, ValueError):
            return float('nan')
            
        # Check if the final value is valid and within safe limits
        if math.isnan(val) or math.isinf(val) or abs(val) > 1e12:
            return float('nan')
            
        return val
        
    def clone(self):
        return BinaryOpNode(self.op, self.left.clone(), self.right.clone())
        
    def __str__(self):
        return f"({self.left} {self.op} {self.right})"

    def to_formatted_string(self):
        """Formats the expression with proper algebraic precedence, omitting redundant parentheses."""
        prec_dict = {'**': 3, '*': 2, '/': 2, '%': 2, '+': 1, '-': 1}
        
        def get_prec(node):
            if isinstance(node, BinaryOpNode):
                return prec_dict.get(node.op, 0)
            return 9 # Highest precedence for leaves
            
        left_str = self.left.to_formatted_string()
        right_str = self.right.to_formatted_string()
        
        self_prec = get_prec(self)
        left_prec = get_prec(self.left)
        right_prec = get_prec(self.right)
        
        # Power operator is right-associative
        if self.op == '**':
            if left_prec <= self_prec:
                left_str = f"({left_str})"
            if right_prec < self_prec:
                right_str = f"({right_str})"
        else:
            # Left-associative operators (+, -, *, /, %)
            if left_prec < self_prec:
                left_str = f"({left_str})"
            if right_prec <= self_prec:
                right_str = f"({right_str})"
                
        return f"{left_str} {self.op} {right_str}"

    def get_nodes_with_relations(self, parent=None, rel_idx=0):
        relations = [(self, parent, rel_idx)]
        relations.extend(self.left.get_nodes_with_relations(self, 0))
        relations.extend(self.right.get_nodes_with_relations(self, 1))
        return relations

    def size(self):
        return 1 + self.left.size() + self.right.size()

    def depth(self):
        return 1 + max(self.left.depth(), self.right.depth())


class UnaryOpNode(Node):
    """Represents a unary operator (sin, cos, round, floor, ceil)."""
    def __init__(self, op, child):
        self.op = op # 'sin', 'cos', 'round', 'floor', 'ceil'
        self.child = child
        
    def evaluate(self, n):
        val = self.child.evaluate(n)
        if math.isnan(val) or math.isinf(val):
            return float('nan')
            
        try:
            if self.op == 'sin':
                res = math.sin(val)
            elif self.op == 'cos':
                res = math.cos(val)
            elif self.op == 'round':
                res = float(round(val))
            elif self.op == 'floor':
                res = float(math.floor(val))
            elif self.op == 'ceil':
                res = float(math.ceil(val))
            else:
                return float('nan')
        except (ValueError, OverflowError):
            return float('nan')
            
        if math.isnan(res) or math.isinf(res) or abs(res) > 1e12:
            return float('nan')
            
        return res
        
    def clone(self):
        return UnaryOpNode(self.op, self.child.clone())
        
    def __str__(self):
        return f"{self.op}({self.child})"
        
    def to_formatted_string(self):
        return f"{self.op}({self.child.to_formatted_string()})"
        
    def get_nodes_with_relations(self, parent=None, rel_idx=0):
        relations = [(self, parent, rel_idx)]
        relations.extend(self.child.get_nodes_with_relations(self, 0))
        return relations
        
    def size(self):
        return 1 + self.child.size()
        
    def depth(self):
        return 1 + self.child.depth()


# =====================================================================
# 2. Algebraic Simplification Engine
# =====================================================================

def simplify_step(node):
    """Performs a single pass of symbolic algebraic simplification on a tree."""
    if isinstance(node, ConstantNode) or isinstance(node, VariableNode):
        return node.clone()
        
    if isinstance(node, BinaryOpNode):
        left_sim = simplify_step(node.left)
        right_sim = simplify_step(node.right)
        
        # 1. Constant folding
        if isinstance(left_sim, ConstantNode) and isinstance(right_sim, ConstantNode):
            temp = BinaryOpNode(node.op, left_sim, right_sim)
            val = temp.evaluate(0) # Variable value doesn't matter for constants
            if not math.isnan(val) and not math.isinf(val):
                if val.is_integer():
                    return ConstantNode(int(val))
                return ConstantNode(round(val, 6))
                
        # 2. Operator identity rules
        # Addition rules: x + 0 = x, 0 + x = x
        if node.op == '+':
            if isinstance(left_sim, ConstantNode) and left_sim.value == 0:
                return right_sim
            if isinstance(right_sim, ConstantNode) and right_sim.value == 0:
                return left_sim
                
        # Subtraction rules: x - 0 = x, 0 - x = -1 * x, x - x = 0
        if node.op == '-':
            if isinstance(right_sim, ConstantNode) and right_sim.value == 0:
                return left_sim
            if isinstance(left_sim, ConstantNode) and left_sim.value == 0:
                return BinaryOpNode('*', ConstantNode(-1), right_sim)
            if str(left_sim) == str(right_sim):
                return ConstantNode(0)
                
        # Multiplication rules: x * 1 = x, 1 * x = x, x * 0 = 0, 0 * x = 0
        if node.op == '*':
            if isinstance(left_sim, ConstantNode):
                if left_sim.value == 1:
                    return right_sim
                if left_sim.value == 0:
                    return ConstantNode(0)
            if isinstance(right_sim, ConstantNode):
                if right_sim.value == 1:
                    return left_sim
                if right_sim.value == 0:
                    return ConstantNode(0)
                    
        # Division rules: x / 1 = x, 0 / x = 0, x / x = 1 (protected division)
        if node.op == '/':
            if isinstance(right_sim, ConstantNode) and right_sim.value == 1:
                return left_sim
            if isinstance(left_sim, ConstantNode) and left_sim.value == 0:
                return ConstantNode(0)
            if str(left_sim) == str(right_sim):
                return ConstantNode(1)
                
        # Modulo rules: x % 1 = 0, x % x = 0
        if node.op == '%':
            if isinstance(right_sim, ConstantNode) and right_sim.value == 1:
                return ConstantNode(0)
            if str(left_sim) == str(right_sim):
                return ConstantNode(0)

        # Power rules: x ** 1 = x, x ** 0 = 1, 1 ** x = 1, 0 ** x = 0
        if node.op == '**':
            if isinstance(right_sim, ConstantNode):
                if right_sim.value == 1:
                    return left_sim
                if right_sim.value == 0:
                    return ConstantNode(1)
            if isinstance(left_sim, ConstantNode):
                if left_sim.value == 1:
                    return ConstantNode(1)
                if left_sim.value == 0:
                    return ConstantNode(0)
                    
        return BinaryOpNode(node.op, left_sim, right_sim)
        
    if isinstance(node, UnaryOpNode):
        child_sim = simplify_step(node.child)
        
        # Unary constant folding
        if isinstance(child_sim, ConstantNode):
            temp = UnaryOpNode(node.op, child_sim)
            val = temp.evaluate(0)
            if not math.isnan(val) and not math.isinf(val):
                if val.is_integer():
                    return ConstantNode(int(val))
                return ConstantNode(round(val, 6))
                
        # Unary identity reductions
        if node.op == 'sin':
            if isinstance(child_sim, ConstantNode) and child_sim.value == 0:
                return ConstantNode(0)
        if node.op == 'cos':
            if isinstance(child_sim, ConstantNode) and child_sim.value == 0:
                return ConstantNode(1)
        if node.op in ['floor', 'ceil', 'round']:
            if isinstance(child_sim, UnaryOpNode) and child_sim.op == node.op:
                return child_sim
                
        return UnaryOpNode(node.op, child_sim)
        
    return node.clone()


def fully_simplify(node):
    """Repeatedly simplifies the node tree until no further changes can be made (up to 10 passes)."""
    prev_str = ""
    curr_node = node
    for _ in range(10):
        curr_node = simplify_step(curr_node)
        curr_str = str(curr_node)
        if curr_str == prev_str:
            break
        prev_str = curr_str
    return curr_node


# =====================================================================
# 3. Tree Initialization (Ramped Half-and-Half)
# =====================================================================

def generate_random_tree(depth, max_depth, method, operators, constants_range, variables):
    """
    Generates a random AST expression tree using either 'grow' or 'full' method.
    constants_range: tuple (min, max, is_float)
    """
    min_val, max_val, is_float = constants_range
    
    # Force leaf at max depth
    if depth >= max_depth:
        if random.random() < 0.5:
            return VariableNode('n')
        else:
            val = random.uniform(min_val, max_val) if is_float else random.randint(int(min_val), int(max_val))
            return ConstantNode(val)
            
    # Force operator at root to avoid degenerate single-node expressions
    if depth == 0:
        op = random.choice(operators)
        if op in ['sin', 'cos', 'round', 'floor', 'ceil']:
            child = generate_random_tree(depth + 1, max_depth, method, operators, constants_range, variables)
            return UnaryOpNode(op, child)
        else:
            left = generate_random_tree(depth + 1, max_depth, method, operators, constants_range, variables)
            right = generate_random_tree(depth + 1, max_depth, method, operators, constants_range, variables)
            return BinaryOpNode(op, left, right)
        
    if method == 'grow':
        # 50% chance of leaf, 50% chance of operator
        if random.random() < 0.5:
            if random.random() < 0.5:
                return VariableNode('n')
            else:
                val = random.uniform(min_val, max_val) if is_float else random.randint(int(min_val), int(max_val))
                return ConstantNode(val)
        else:
            op = random.choice(operators)
            if op in ['sin', 'cos', 'round', 'floor', 'ceil']:
                child = generate_random_tree(depth + 1, max_depth, method, operators, constants_range, variables)
                return UnaryOpNode(op, child)
            else:
                left = generate_random_tree(depth + 1, max_depth, method, operators, constants_range, variables)
                right = generate_random_tree(depth + 1, max_depth, method, operators, constants_range, variables)
                return BinaryOpNode(op, left, right)
    else:
        # Full method: select operators at all intermediate levels
        op = random.choice(operators)
        if op in ['sin', 'cos', 'round', 'floor', 'ceil']:
            child = generate_random_tree(depth + 1, max_depth, method, operators, constants_range, variables)
            return UnaryOpNode(op, child)
        else:
            left = generate_random_tree(depth + 1, max_depth, method, operators, constants_range, variables)
            right = generate_random_tree(depth + 1, max_depth, method, operators, constants_range, variables)
            return BinaryOpNode(op, left, right)


def init_population(pop_size, max_depth, operators, constants_range, variables):
    """Implements Ramped Half-and-Half population initialization."""
    population = []
    depths = list(range(1, max_depth + 1))
    trees_per_depth = pop_size // len(depths)
    
    for d in depths:
        num_full = trees_per_depth // 2
        num_grow = trees_per_depth - num_full
        
        for _ in range(num_full):
            population.append(generate_random_tree(0, d, 'full', operators, constants_range, variables))
        for _ in range(num_grow):
            population.append(generate_random_tree(0, d, 'grow', operators, constants_range, variables))
            
    # Pad remainder due to integer division
    while len(population) < pop_size:
        d = random.choice(depths)
        method = random.choice(['full', 'grow'])
        population.append(generate_random_tree(0, d, method, operators, constants_range, variables))
        
    return population


# =====================================================================
# 4. Fitness & Selection
# =====================================================================

def calculate_fitness(individual, indices, target, error_metric='mae', parsimony_coeff=0.0005):
    """
    Computes fitness. Lower is better (0.0 is a perfect match).
    Contains safety filters for NaN/inf and size penalties (parsimony pressure).
    """
    total_error = 0.0
    for n, y in zip(indices, target):
        val = individual.evaluate(n)
        if math.isnan(val) or math.isinf(val):
            return 1e12  # Large penalty for invalid outputs
            
        if error_metric == 'mae':
            total_error += abs(val - y)
        elif error_metric == 'mse':
            total_error += (val - y) ** 2
            
    avg_error = total_error / len(target)
    
    if math.isnan(avg_error) or math.isinf(avg_error):
        return 1e12
        
    # Parsimony pressure: penalize larger trees slightly to encourage simplicity
    size_penalty = parsimony_coeff * individual.size()
    return avg_error + size_penalty


def tournament_selection(population, fitnesses, tournament_size=5):
    """Selects the best individual from a random tournament group."""
    selected_indices = random.sample(range(len(population)), tournament_size)
    best_idx = min(selected_indices, key=lambda idx: fitnesses[idx])
    return population[best_idx].clone()


# =====================================================================
# 5. Genetic Operators (Crossover & Mutation)
# =====================================================================

def crossover(parent1, parent2, max_depth=8):
    """Swaps random subtrees between two parents, respecting a maximum depth limit."""
    offspring1 = parent1.clone()
    offspring2 = parent2.clone()
    
    # Try up to 5 times to perform a depth-compliant crossover
    for _ in range(5):
        nodes1 = offspring1.get_nodes_with_relations()
        nodes2 = offspring2.get_nodes_with_relations()
        
        node_info1 = random.choice(nodes1)
        node_info2 = random.choice(nodes2)
        
        node1, p1, idx1 = node_info1
        node2, p2, idx2 = node_info2
        
        node1_clone = node1.clone()
        node2_clone = node2.clone()
        
        # Swap node 2 into parent 1
        if p1 is None:
            offspring1 = node2_clone
        else:
            if isinstance(p1, UnaryOpNode):
                p1.child = node2_clone
            else:
                if idx1 == 0:
                    p1.left = node2_clone
                else:
                    p1.right = node2_clone
                
        # Swap node 1 into parent 2
        if p2 is None:
            offspring2 = node1_clone
        else:
            if isinstance(p2, UnaryOpNode):
                p2.child = node1_clone
            else:
                if idx2 == 0:
                    p2.left = node1_clone
                else:
                    p2.right = node1_clone
                
        # Verify depth limits to prevent bloated trees
        if offspring1.depth() <= max_depth and offspring2.depth() <= max_depth:
            return offspring1, offspring2
            
        # Revert changes if depth violated
        offspring1 = parent1.clone()
        offspring2 = parent2.clone()
        
    return offspring1, offspring2


def mutate_subtree(individual, max_depth, operators, constants_range, variables):
    """Replaces a random subtree with a new randomly generated subtree."""
    mutant = individual.clone()
    nodes = mutant.get_nodes_with_relations()
    target_node, parent, rel_idx = random.choice(nodes)
    
    # Generate a small new subtree (depth 1 or 2)
    new_sub_depth = random.randint(1, 2)
    new_subtree = generate_random_tree(0, new_sub_depth, 'grow', operators, constants_range, variables)
    
    if parent is None:
        return new_subtree
        
    if isinstance(parent, UnaryOpNode):
        parent.child = new_subtree
    else:
        if rel_idx == 0:
            parent.left = new_subtree
        else:
            parent.right = new_subtree
        
    return mutant


def mutate_point(individual, operators, constants_range, variables):
    """
    Modifies a single node contents in place.
    If constant, adds Gaussian noise (if float) or picks a new value.
    If variable, swaps with a random constant.
    If operator, swaps with another random operator.
    """
    mutant = individual.clone()
    nodes = mutant.get_nodes_with_relations()
    target_node, parent, rel_idx = random.choice(nodes)
    
    if isinstance(target_node, ConstantNode):
        min_val, max_val, is_float = constants_range
        if is_float:
            # Gaussian perturbation: fine-tunes real number constants
            perturbation = random.gauss(0, (max_val - min_val) * 0.1)
            target_node.value = max(min_val, min(max_val, target_node.value + perturbation))
        else:
            target_node.value = random.randint(int(min_val), int(max_val))
            
    elif isinstance(target_node, VariableNode):
        # Swap Variable to Constant
        min_val, max_val, is_float = constants_range
        val = random.uniform(min_val, max_val) if is_float else random.randint(int(min_val), int(max_val))
        new_node = ConstantNode(val)
        
        if parent is None:
            return new_node
        if isinstance(parent, UnaryOpNode):
            parent.child = new_node
        else:
            if rel_idx == 0:
                parent.left = new_node
            else:
                parent.right = new_node
            
    elif isinstance(target_node, BinaryOpNode):
        # Swap binary operator
        bin_ops = [op for op in operators if op not in ['sin', 'cos', 'round', 'floor', 'ceil']]
        target_node.op = random.choice(bin_ops)
        
    elif isinstance(target_node, UnaryOpNode):
        # Swap unary operator
        unary_ops = ['sin', 'cos', 'round', 'floor', 'ceil']
        choices = [op for op in unary_ops if op != target_node.op]
        target_node.op = random.choice(choices)
        
    return mutant


def mutate_shrink(individual):
    """Replaces a random operator subtree with one of its child nodes or a leaf."""
    mutant = individual.clone()
    nodes = mutant.get_nodes_with_relations()
    
    op_nodes = [info for info in nodes if isinstance(info[0], (BinaryOpNode, UnaryOpNode))]
    if not op_nodes:
        return mutant # Return original if no operator node is present
        
    target_node, parent, rel_idx = random.choice(op_nodes)
    
    if isinstance(target_node, UnaryOpNode):
        choice = random.choice(['child', 'leaf'])
        if choice == 'child':
            new_subtree = target_node.child.clone()
        else:
            sub_nodes = target_node.get_nodes_with_relations()
            leaves = [info[0].clone() for info in sub_nodes if isinstance(info[0], (ConstantNode, VariableNode))]
            new_subtree = random.choice(leaves)
    else:
        choice = random.choice(['left', 'right', 'leaf'])
        if choice == 'left':
            new_subtree = target_node.left.clone()
        elif choice == 'right':
            new_subtree = target_node.right.clone()
        else:
            # Find a leaf anywhere inside target node's subtree
            sub_nodes = target_node.get_nodes_with_relations()
            leaves = [info[0].clone() for info in sub_nodes if isinstance(info[0], (ConstantNode, VariableNode))]
            new_subtree = random.choice(leaves)
        
    if parent is None:
        return new_subtree
        
    if isinstance(parent, UnaryOpNode):
        parent.child = new_subtree
    else:
        if rel_idx == 0:
            parent.left = new_subtree
        else:
            parent.right = new_subtree
        
    return mutant


def mutate(individual, max_depth, operators, constants_range, variables, mutation_probs=(0.4, 0.4, 0.2)):
    """Applies one of the three mutations based on relative probabilities."""
    r = random.random()
    p_sub, p_pt, p_sh = mutation_probs
    
    if r < p_sub:
        return mutate_subtree(individual, max_depth, operators, constants_range, variables)
    elif r < p_sub + p_pt:
        return mutate_point(individual, operators, constants_range, variables)
    else:
        return mutate_shrink(individual)


# =====================================================================
# 6. ASCII Visualization Plotter
# =====================================================================

def draw_ascii_chart(indices, target, predicted, width=58, height=12):
    """
    Renders an eye-catching, perfectly scaled terminal ASCII line chart 
    plotting Target values (green ●) vs Predicted values (cyan ▲). 
    Overlapping data points are highlighted in yellow ▣.
    """
    valid_predicted = [p for p in predicted if not math.isnan(p) and not math.isinf(p)]
    if not valid_predicted:
        return "   No valid predicted values to render chart."
        
    all_vals = target + valid_predicted
    min_val = min(all_vals)
    max_val = max(all_vals)
    
    # If the sequence is flat, pad it to prevent division-by-zero
    if max_val == min_val:
        max_val += 1.0
        min_val -= 1.0
        
    span = max_val - min_val
    grid = [[" " for _ in range(width)] for _ in range(height)]
    
    def get_x_col(n_val):
        if len(indices) == 1:
            return 0
        return int((n_val - indices[0]) / (indices[-1] - indices[0]) * (width - 1))
        
    def get_y_row(val):
        if math.isnan(val) or math.isinf(val):
            return None
        val_clamped = max(min_val, min(max_val, val))
        row = int((val_clamped - min_val) / span * (height - 1))
        return height - 1 - row  # grid[0] is top row in Python printing

    # Draw Target dots
    for idx, t_val in zip(indices, target):
        col = get_x_col(idx)
        row = get_y_row(t_val)
        if row is not None and 0 <= row < height and 0 <= col < width:
            grid[row][col] = '\033[92m●\033[0m' # Vibrant Green bullet
            
    # Draw Predicted triangles
    for idx, p_val in zip(indices, predicted):
        col = get_x_col(idx)
        row = get_y_row(p_val)
        if row is not None and 0 <= row < height and 0 <= col < width:
            if grid[row][col] != " ":
                grid[row][col] = '\033[93m▣\033[0m' # Overlap yellow cross-box
            else:
                grid[row][col] = '\033[96m▲\033[0m' # Vibrant Cyan triangle
                
    chart_lines = []
    chart_lines.append("   " + "┌" + "─" * width + "┐")
    for r in range(height):
        row_val = max_val - (r / (height - 1)) * span
        row_lbl = f"{row_val:7.2f} │"
        grid_row = "".join(grid[r])
        chart_lines.append(f"{row_lbl}{grid_row}│")
    chart_lines.append("   " + "└" + "─" * width + "┘")
    
    x_lbl_start = f"{indices[0]:.1f}"
    x_lbl_end = f"{indices[-1]:.1f}"
    padding = width - len(x_lbl_start) - len(x_lbl_end)
    chart_lines.append("           " + x_lbl_start + " " * padding + x_lbl_end)
    chart_lines.append("           \033[92m● Target\033[0m   \033[96m▲ Predicted\033[0m   \033[93m▣ Overlap\033[0m")
    
    return "\n".join(chart_lines)


# =====================================================================
# 7. Core Evolutionary Run Loop
# =====================================================================

def run_gp(target_sequence, start_index=0, max_generations=150, pop_size=600, 
           parsimony_coeff=0.0005, error_metric='mae', is_float=False):
    """Executes the Genetic Programming evolution loop to solve a sequence."""
    indices = [float(start_index + i) for i in range(len(target_sequence))]
    
    # Operator pool (includes trigonometric and rounding functions)
    operators = ['+', '-', '*', '/', '%', '**', 'sin', 'cos', 'round', 'floor', 'ceil']
    
    # Constants configuration based on sequence type
    # For float targets, search inside a continuous range. Otherwise use integers.
    if is_float:
        # Determine appropriate constant bounds based on target sequence bounds
        min_seq = min(target_sequence)
        max_seq = max(target_sequence)
        constants_range = (min_seq - 5.0, max_seq + 5.0, True)
    else:
        constants_range = (-10, 10, False)
        
    variables = ['n']
    
    # 1. Initialize population
    population = init_population(pop_size, max_depth=4, operators=operators, 
                                 constants_range=constants_range, variables=variables)
    
    best_overall_ind = None
    best_overall_fitness = 1e15
    
    print("\n\033[1;36mInitializing Evolution System...\033[0m")
    print(f"Population size: {pop_size} | Parsimony Pressure: {parsimony_coeff} | Target size: {len(target_sequence)}")
    print(f"Index mode: n starts at {start_index} | Floats: {is_float}")
    print("-" * 75)
    
    # 2. Main Generation Loop
    for gen in range(1, max_generations + 1):
        # Calculate fitness for all individuals
        fitnesses = [calculate_fitness(ind, indices, target_sequence, error_metric, parsimony_coeff) for ind in population]
        
        # Get the generation's best
        best_gen_idx = min(range(pop_size), key=lambda idx: fitnesses[idx])
        best_gen_ind = population[best_gen_idx]
        best_gen_fitness = fitnesses[best_gen_idx]
        
        # Track overall champion
        # Evaluate raw mathematical error of champion (excluding parsimony size penalty)
        raw_error = calculate_fitness(best_gen_ind, indices, target_sequence, error_metric, parsimony_coeff=0.0)
        
        if best_gen_fitness < best_overall_fitness:
            best_overall_fitness = best_gen_fitness
            best_overall_ind = best_gen_ind.clone()
            
        # Display progression in real-time
        if gen == 1 or gen % 10 == 0 or gen == max_generations or raw_error < 1e-4:
            simplified = fully_simplify(best_gen_ind)
            expr_str = simplified.to_formatted_string()
            # Truncate string if too long for display
            if len(expr_str) > 45:
                expr_str = expr_str[:42] + "..."
            print(f"Gen {gen:3d} | Best Fitness: {best_gen_fitness:10.4f} | Raw Error: {raw_error:10.5f} | Best Expr: {expr_str}")
            
        # Convergence criteria (excellent match)
        if raw_error < 1e-6:
            print(f"\n\033[1;32m★ Exact match solved early at Generation {gen}! ★\033[0m")
            break
            
        # 3. Form the next generation
        next_population = []
        
        # Elitism: carry over the top 2% of individuals untouched
        sorted_indices = sorted(range(pop_size), key=lambda idx: fitnesses[idx])
        num_elites = max(2, int(pop_size * 0.02))
        for idx in sorted_indices[:num_elites]:
            next_population.append(population[idx].clone())
            
        # Breed remaining offspring
        while len(next_population) < pop_size:
            # 90% Crossover rate, 10% Mutation rate
            if random.random() < 0.90:
                p1 = tournament_selection(population, fitnesses)
                p2 = tournament_selection(population, fitnesses)
                off1, off2 = crossover(p1, p2, max_depth=8)
                next_population.append(off1)
                if len(next_population) < pop_size:
                    next_population.append(off2)
            else:
                p = tournament_selection(population, fitnesses)
                mutant = mutate(p, max_depth=8, operators=operators, 
                                constants_range=constants_range, variables=variables)
                next_population.append(mutant)
                
        population = next_population
        
    # Simplify the winner
    champion_simplified = fully_simplify(best_overall_ind)
    champion_error = calculate_fitness(champion_simplified, indices, target_sequence, error_metric, parsimony_coeff=0.0)
    
    return champion_simplified, champion_error, indices


# =====================================================================
# 8. Interactive CLI & Preset Sequences
# =====================================================================

PRESETS = {
    "1": ("Arithmetic (Linear progression)", [3.0, 5.0, 7.0, 9.0, 11.0, 13.0], 0, False),
    "2": ("Quadratic Sequence (Polynomial growth)", [0.0, 1.0, 4.0, 9.0, 16.0, 25.0], 0, False),
    "3": ("Exponential Progression (Base 2)", [1.0, 2.0, 4.0, 8.0, 16.0, 32.0], 0, False),
    "4": ("Real-valued Decaying Geometric Progression", [10.0, 5.0, 2.5, 1.25, 0.625, 0.3125], 0, True),
    "5": ("Golden Ratio Power Sequence", [1.0, 1.618, 2.618, 4.236, 6.854, 11.09], 0, True),
    "6": ("Fractional n/(n+2) Ratio Sequence", [0.0, 0.3333, 0.5, 0.6, 0.6667, 0.7143], 0, True),
    "7": ("Fibonacci (Highly complex recursive sequence)", [1.0, 1.0, 2.0, 3.0, 5.0, 8.0, 13.0, 21.0], 1, False),
    "8": ("Trigonometric Sine Curve (Periodic)", [0.0, 0.8415, 0.9093, 0.1411, -0.7568, -0.9589], 0, True),
}

def print_banner():
    banner = r"""
\033[95m  _  _   __  _____  __ _____  _  __    __  _   ___  ___  _ 
 / _/ \ /  \/__ __\/ _/__ __\/ \/ _\  /__\/ \ / _ \/ __\/ \
| |/ . | () | | |  | \  | |  | || \  / \//| | | __/ /   | |
| |\   | || | | |  | _\ | |  | |\ \  \ _/ | | | |_/ \__  \_/
\_/ \_/\_/\_/ \_/  \_/  \_/  \_/\__/  \/   \_/ \__/\___/  (_)
\033[0m
     \033[1;33m--- Genetic Mathematical Expression Generator ---
                 Standard & Real Math Support\033[0m
    """
    print(banner)


def show_results(champion, error, indices, target_sequence):
    """Prints a beautiful summary of final GP results, prediction table, and ASCII graph."""
    expr_str = champion.to_formatted_string()
    
    print("\n" + "=" * 75)
    print("\033[1;32m★ EVOLUTION COMPLETE ★\033[0m")
    print(f"Final Simplified Expression: \033[1;36m{expr_str}\033[0m")
    print(f"Mean Absolute Error:         \033[1;35m{error:.6f}\033[0m")
    print("=" * 75)
    
    # Calculate predictions
    predictions = [champion.evaluate(n) for n in indices]
    
    # Display table
    print("\n\033[1mPrediction Table:\033[0m")
    print("┌───────┬──────────────┬──────────────┬──────────────┐")
    print("│   n   │    Target    │  Predicted   │    Error     │")
    print("├───────┼──────────────┼──────────────┼──────────────┤")
    for n, t, p in zip(indices, target_sequence, predictions):
        err_str = f"{abs(t-p):.5f}" if not (math.isnan(p) or math.isinf(p)) else "N/A"
        pred_str = f"{p:.5f}" if not (math.isnan(p) or math.isinf(p)) else "INVALID"
        print(f"│ {int(n):5d} │ {t:12.5f} │ {pred_str:>12s} │ {err_str:>12s} │")
    print("└───────┴──────────────┴──────────────┴──────────────┘")
    
    # Draw chart
    print("\n\033[1mVisual Alignment Curve:\033[0m")
    print(draw_ascii_chart(indices, target_sequence, predictions))
    print()


def interactive_cli():
    print_banner()
    print("Select a test sequence or input a custom sequence:")
    for k, (name, seq, start_idx, is_float) in PRESETS.items():
        seq_sample = ", ".join(map(str, seq[:4])) + "..."
        type_lbl = "\033[93mReal\033[0m" if is_float else "\033[92mInt\033[0m"
        print(f"  \033[1;36m{k}\033[0m. {name:<45} (Type: {type_lbl:<5} Sample: {seq_sample})")
    print("  \033[1;36mC\033[0m. Custom sequence entry")
    
    choice = input("\nEnter choice (1-8 or C, default is 1): ").strip() or "1"
    
    target_seq = None
    start_index = 0
    is_float = False
    
    if choice.upper() == 'C':
        print("\nEnter a comma-separated sequence of numbers.")
        print("Example: 1, 4, 9, 16, 25  or  0.5, 1.25, 2.0, 2.75")
        seq_input = input("Sequence: ").strip()
        try:
            target_seq = [float(x.strip()) for x in seq_input.split(',')]
            # Auto-detect if it contains floats (real numbers) or is purely integer-based
            is_float = any(not float(x).is_integer() for x in target_seq)
        except ValueError:
            print("\033[91mInvalid number entries. Exiting.\033[0m")
            sys.exit(1)
            
        start_input = input("Enter starting index n (0 or 1, default is 0): ").strip() or "0"
        try:
            start_index = int(start_input)
        except ValueError:
            print("Invalid starting index. Defaulting to 0.")
            start_index = 0
    else:
        preset_info = PRESETS.get(choice)
        if not preset_info:
            print("Invalid choice, defaulting to preset 1.")
            preset_info = PRESETS["1"]
        _, target_seq, start_index, is_float = preset_info
        
    print(f"\nLoaded Target Sequence: {target_seq}")
    
    # Configuration inputs
    gen_in = input("Max Generations (default: 120): ").strip() or "120"
    pop_in = input("Population Size (default: 600): ").strip() or "600"
    par_in = input("Parsimony Pressure Coefficient (default: 0.0002): ").strip() or "0.0002"
    
    max_gens = int(gen_in) if gen_in.isdigit() else 120
    pop_size = int(pop_in) if pop_in.isdigit() else 600
    par_coeff = float(par_in) if par_in.replace('.', '', 1).isdigit() else 0.0002
    
    champion, error, indices = run_gp(
        target_sequence=target_seq,
        start_index=start_index,
        max_generations=max_gens,
        pop_size=pop_size,
        parsimony_coeff=par_coeff,
        is_float=is_float
    )
    
    show_results(champion, error, indices, target_seq)


# =====================================================================
# 9. Automated Testing Suite (--test)
# =====================================================================

def run_unit_tests():
    """Runs tests to verify the correctness of operators, trees, and logic."""
    print("\033[1;36mRunning Test Suite...\033[0m")
    passed = 0
    failed = 0
    
    def test_assert(condition, desc):
        nonlocal passed, failed
        if condition:
            print(f"  [\033[92mPASS\033[0m] {desc}")
            passed += 1
        else:
            print(f"  [\033[91mFAIL\033[0m] {desc}")
            failed += 1

    # Test 1: Node creation and evaluation
    try:
        n = VariableNode('n')
        c2 = ConstantNode(2)
        expr = BinaryOpNode('+', n, c2)
        test_assert(expr.evaluate(5) == 7.0, "Variable evaluate: n + 2 for n=5 equals 7.0")
    except Exception as e:
        test_assert(False, f"Variable evaluate failed with exception: {e}")
        
    # Test 2: Protected operators
    try:
        # 1. Division by Zero
        div_zero = BinaryOpNode('/', ConstantNode(5), ConstantNode(0))
        test_assert(div_zero.evaluate(0) == 1.0, "Protected Division: 5 / 0 evaluates to 1.0")
        
        # 2. Modulo by Zero
        mod_zero = BinaryOpNode('%', ConstantNode(5), ConstantNode(0))
        test_assert(mod_zero.evaluate(0) == 0.0, "Protected Modulo: 5 % 0 evaluates to 0.0")
        
        # 3. Fractional exponent on negative base
        neg_pow = BinaryOpNode('**', ConstantNode(-4), ConstantNode(0.5))
        test_assert(neg_pow.evaluate(0) == 2.0, "Protected Power: (-4) ** 0.5 evaluates to absolute base power: 2.0")
    except Exception as e:
        test_assert(False, f"Protected operators failed with exception: {e}")

    # Test 3: Algebraic Simplification
    try:
        # Simplification: (n + 0) -> n
        n_plus_zero = BinaryOpNode('+', VariableNode('n'), ConstantNode(0))
        sim = fully_simplify(n_plus_zero)
        test_assert(isinstance(sim, VariableNode), "Simplification: n + 0 simplifies to VariableNode 'n'")
        
        # Simplification: Constant Folding 3 * 4 -> 12
        c3 = ConstantNode(3)
        c4 = ConstantNode(4)
        c_mul = BinaryOpNode('*', c3, c4)
        sim_mul = fully_simplify(c_mul)
        test_assert(isinstance(sim_mul, ConstantNode) and sim_mul.value == 12, "Simplification: Constant Folding 3 * 4 simplifies to 12")
        
        # Complex nested simplification: ((n * 0) + 1) -> 1
        complex_expr = BinaryOpNode('+', BinaryOpNode('*', VariableNode('n'), ConstantNode(0)), ConstantNode(1))
        sim_complex = fully_simplify(complex_expr)
        test_assert(isinstance(sim_complex, ConstantNode) and sim_complex.value == 1, "Simplification: ((n * 0) + 1) simplifies to ConstantNode 1")
    except Exception as e:
        test_assert(False, f"Simplification failed with exception: {e}")

    # Test 4: Format Representation (Precedence minimal parentheses)
    try:
        # (n + 1) * 2 should keep parenthesized left
        add_node = BinaryOpNode('+', VariableNode('n'), ConstantNode(1))
        mul_node = BinaryOpNode('*', add_node, ConstantNode(2))
        test_assert(mul_node.to_formatted_string() == "(n + 1) * 2", "Formatting: correct precedence for (n + 1) * 2")
        
        # 2 * n + 1 should omit parentheses
        mul_node2 = BinaryOpNode('*', ConstantNode(2), VariableNode('n'))
        add_node2 = BinaryOpNode('+', mul_node2, ConstantNode(1))
        test_assert(add_node2.to_formatted_string() == "2 * n + 1", "Formatting: correct precedence and omit parentheses for 2 * n + 1")
    except Exception as e:
        test_assert(False, f"Formatting failed with exception: {e}")

    # Test 5: Crossover and Mutation structural soundness
    try:
        p1 = BinaryOpNode('+', VariableNode('n'), ConstantNode(10))
        p2 = BinaryOpNode('*', VariableNode('n'), ConstantNode(5))
        c1, c2 = crossover(p1, p2, max_depth=5)
        test_assert(c1.depth() <= 5 and c2.depth() <= 5, "Crossover: Structural soundness and depth limit")
    except Exception as e:
        test_assert(False, f"Crossover/Mutation test failed: {e}")
        
    # Test 6: Trigonometric functions (sin, cos)
    try:
        # 1. Unary node evaluation
        sin_node = UnaryOpNode('sin', ConstantNode(0))
        cos_node = UnaryOpNode('cos', ConstantNode(0))
        test_assert(sin_node.evaluate(0) == 0.0, "Trig: sin(0) evaluates to 0.0")
        test_assert(cos_node.evaluate(0) == 1.0, "Trig: cos(0) evaluates to 1.0")
        
        # 2. Formatted stringification
        test_assert(sin_node.to_formatted_string() == "sin(0)", "Trig Formatting: sin(0) formatted string representation is correct")
        
        # 3. Simplification identities sin(0) -> 0, cos(0) -> 1
        test_assert(fully_simplify(sin_node).value == 0, "Trig Simplification: sin(0) simplifies to ConstantNode 0")
        test_assert(fully_simplify(cos_node).value == 1, "Trig Simplification: cos(0) simplifies to ConstantNode 1")
    except Exception as e:
        test_assert(False, f"Trigonometric tests failed with exception: {e}")
        
    # Test 7: Round, Floor, Ceil unary functions
    try:
        # 1. Unary node evaluation
        floor_node = UnaryOpNode('floor', ConstantNode(1.7))
        ceil_node = UnaryOpNode('ceil', ConstantNode(1.2))
        round_node = UnaryOpNode('round', ConstantNode(2.5))
        test_assert(floor_node.evaluate(0) == 1.0, "Floor: floor(1.7) evaluates to 1.0")
        test_assert(ceil_node.evaluate(0) == 2.0, "Ceil: ceil(1.2) evaluates to 2.0")
        test_assert(round_node.evaluate(0) == 3.0 or round_node.evaluate(0) == 2.0, "Round: round(2.5) evaluates correctly to 2.0 or 3.0")
        
        # 2. Formatted stringification
        test_assert(floor_node.to_formatted_string() == "floor(1.7)", "Floor Formatting: floor(1.7) formatted string representation is correct")
        
        # 3. Idempotent simplification floor(floor(n)) -> floor(n)
        nested_floor = UnaryOpNode('floor', UnaryOpNode('floor', VariableNode('n')))
        sim_floor = fully_simplify(nested_floor)
        test_assert(isinstance(sim_floor, UnaryOpNode) and sim_floor.op == 'floor' and isinstance(sim_floor.child, VariableNode), "Floor Simplification: floor(floor(n)) simplifies to floor(n)")
    except Exception as e:
        test_assert(False, f"Round/Floor/Ceil tests failed with exception: {e}")
        
    print(f"\nSuite complete. \033[92m{passed} passed\033[0m, \033[91m{failed} failed\033[0m.")
    sys.exit(0 if failed == 0 else 1)


# =====================================================================
# 10. Main entrypoint
# =====================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genetic Algorithm Mathematical Expression Generator")
    parser.add_argument('--test', action='store_true', help="Run automated test suite to verify implementation correctness")
    args = parser.parse_args()
    
    if args.test:
        run_unit_tests()
    else:
        try:
            interactive_cli()
        except KeyboardInterrupt:
            print("\n\n\033[93mProgram interrupted by user. Goodbye!\033[0m")
            sys.exit(0)
