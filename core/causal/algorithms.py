# -*- coding: utf-8 -*-
"""
Causal Discovery Algorithms
Implements PC and GES algorithms for causal graph construction
"""

from dataclasses import dataclass
from itertools import combinations
from math import erfc, log, sqrt
from typing import Dict, List, Set, Tuple

import numpy as np
from loguru import logger

from .graph import CausalEdge, CausalGraph, CausalStrength


@dataclass
class ConditionalIndependenceTest:
    """
    Result of conditional independence test

    Attributes:
        independent: True if variables are independent
        p_value: P-value of the test
        statistic: Test statistic
    """

    independent: bool
    p_value: float
    statistic: float


class PCAlgorithm:
    """
    Peter-Clark (PC) Algorithm for causal discovery

    A constraint-based algorithm that uses conditional independence tests
    to discover causal structure from observational data.
    """

    def __init__(self, alpha: float = 0.05):
        """
        Initialize PC algorithm

        Args:
            alpha: Significance level for independence tests
        """
        self.alpha = alpha

    def discover(self, data: np.ndarray, variable_names: List[str]) -> CausalGraph:
        """
        Discover causal graph from data

        Args:
            data: Observational data (n_samples x n_variables)
            variable_names: List of variable names

        Returns:
            CausalGraph object
        """
        n_variables = int(data.shape[1])
        graph = CausalGraph("pc_discovery")

        # 全连接无向骨架 + 分离集（sepset）登记
        adjacency: Dict[int, Set[int]] = {
            i: set(range(n_variables)) - {i} for i in range(n_variables)
        }
        sepsets: Dict[frozenset, Set[int]] = {}

        # Phase 1：骨架发现——按条件集大小递增做条件独立性检验，独立则删边并登记分离集
        for level in range(0, n_variables):
            pairs: List[Tuple[int, int]] = []
            for i in range(n_variables):
                for j in adjacency[i]:
                    if j < i:
                        continue
                    if len(adjacency[i] - {j}) >= level:
                        pairs.append((i, j))
            if not pairs:
                break

            removals: List[Tuple[int, int, Set[int]]] = []
            for i, j in pairs:
                if j not in adjacency[i]:
                    continue
                neighbors = sorted(adjacency[i] - {j})
                for combo in combinations(neighbors, level):
                    condition = set(combo)
                    if self._test_independence(data, i, j, condition).independent:
                        removals.append((i, j, condition))
                        break

            for i, j, condition in removals:
                if j in adjacency[i]:
                    adjacency[i].discard(j)
                    adjacency[j].discard(i)
                    sepsets[frozenset((i, j))] = condition

        # Phase 2：定向 v-structure（无屏蔽三元组 a - k - b，且 k 不在 sepset(a,b) 中）
        arcs: Set[Tuple[int, int]] = set()
        for k in range(n_variables):
            neighbors = sorted(adjacency[k])
            for a, b in combinations(neighbors, 2):
                if b in adjacency[a]:
                    continue  # a、b 仍相邻 → 有屏蔽，非 v-structure
                sep = sepsets.get(frozenset((a, b)))
                if sep is None or k not in sep:
                    arcs.add((a, k))
                    arcs.add((b, k))

        # 剩余未定向边（排除已由 v-structure 定向的边）
        undirected: Set[frozenset] = set()
        for i in range(n_variables):
            for j in adjacency[i]:
                if i < j and (i, j) not in arcs and (j, i) not in arcs:
                    undirected.add(frozenset((i, j)))

        # Phase 3：Meek 规则 R1–R4 定向可确定的剩余边，其余按拓扑序完成定向（保持无环）
        self._orient_meek(undirected, arcs, n_variables)
        self._orient_remaining(undirected, arcs, n_variables)

        # 构建因果图
        for name in variable_names:
            graph.add_node(name)

        for a, b in sorted(arcs):
            strength, confidence = self._edge_strength(data, a, b)
            graph.add_edge(
                CausalEdge(
                    from_var=variable_names[a],
                    to_var=variable_names[b],
                    strength=strength,
                    confidence=confidence,
                )
            )

        logger.info(
            f"PC algorithm discovered graph with {len(graph.nodes)} nodes, {len(graph.edges)} edges"
        )

        return graph

    @staticmethod
    def _is_directed(arcs: Set[Tuple[int, int]], x: int, y: int) -> bool:
        return (x, y) in arcs

    @staticmethod
    def _is_undirected(undirected: Set[frozenset], x: int, y: int) -> bool:
        return frozenset((x, y)) in undirected

    @classmethod
    def _is_adjacent(cls, arcs, undirected, x: int, y: int) -> bool:
        return (
            cls._is_directed(arcs, x, y)
            or cls._is_directed(arcs, y, x)
            or cls._is_undirected(undirected, x, y)
        )

    def _orient_meek(
        self, undirected: Set[frozenset], arcs: Set[Tuple[int, int]], n: int
    ) -> None:
        """应用 Meek 规则 R1–R4 直至不再有可定向的边。"""
        changed = True
        while changed:
            changed = False
            for edge in list(undirected):
                x, y = tuple(edge)

                # R1：存在 a→b（b∈{x,y}）且 a 与另一边 c 不相邻 ⇒ 定向 b→c
                for b, c in ((x, y), (y, x)):
                    for a in range(n):
                        if a in (b, c):
                            continue
                        if self._is_directed(arcs, a, b) and not self._is_adjacent(
                            arcs, undirected, a, c
                        ):
                            arcs.add((b, c))
                            undirected.discard(edge)
                            changed = True
                            break
                    if changed:
                        break
                if changed:
                    break

                # R2：a→b 且 b→c，且 a - c 无向 ⇒ 定向 a→c
                for a, c in ((x, y), (y, x)):
                    for b in range(n):
                        if b in (a, c):
                            continue
                        if self._is_directed(arcs, a, b) and self._is_directed(arcs, b, c):
                            arcs.add((a, c))
                            undirected.discard(edge)
                            changed = True
                            break
                    if changed:
                        break
                if changed:
                    break

                # R3：a-b 无向，a-c 无向，a-d 无向，c→b、d→b 且 c、d 不相邻 ⇒ 定向 a→b
                for a, b in ((x, y), (y, x)):
                    if not self._is_undirected(undirected, a, b):
                        continue
                    cands = [d for d in range(n) if d not in (a, b)]
                    oriented = False
                    for c, d in combinations(cands, 2):
                        if (
                            self._is_undirected(undirected, a, c)
                            and self._is_undirected(undirected, a, d)
                            and self._is_directed(arcs, c, b)
                            and self._is_directed(arcs, d, b)
                            and not self._is_adjacent(arcs, undirected, c, d)
                        ):
                            arcs.add((a, b))
                            undirected.discard(edge)
                            changed = True
                            oriented = True
                            break
                    if oriented:
                        break
                if changed:
                    break

                # R4：a-b 无向，a-c 无向，c→d→b，且 a - d 无向 ⇒ 定向 a→b
                for a, b in ((x, y), (y, x)):
                    if not self._is_undirected(undirected, a, b):
                        continue
                    oriented = False
                    for c in range(n):
                        if c in (a, b):
                            continue
                        if not self._is_undirected(undirected, a, c):
                            continue
                        for d in range(n):
                            if d in (a, b, c):
                                continue
                            if (
                                self._is_directed(arcs, c, d)
                                and self._is_directed(arcs, d, b)
                                and self._is_undirected(undirected, a, d)
                            ):
                                arcs.add((a, b))
                                undirected.discard(edge)
                                changed = True
                                oriented = True
                                break
                        if oriented:
                            break
                    if oriented:
                        break
                if changed:
                    break

    @staticmethod
    def _topological_order(arcs: Set[Tuple[int, int]], n: int) -> List[int]:
        """对已定向弧做拓扑排序；有环（理论上不应出现）时以节点序号补齐。"""
        indeg = {i: 0 for i in range(n)}
        children: Dict[int, Set[int]] = {i: set() for i in range(n)}
        for a, b in arcs:
            children[a].add(b)
            indeg[b] = indeg.get(b, 0) + 1

        queue = [i for i in range(n) if indeg.get(i, 0) == 0]
        order: List[int] = []
        while queue:
            node = queue.pop(0)
            order.append(node)
            for child in sorted(children[node]):
                indeg[child] -= 1
                if indeg[child] == 0:
                    queue.append(child)

        for i in range(n):
            if i not in order:
                order.append(i)
        return order

    def _orient_remaining(
        self, undirected: Set[frozenset], arcs: Set[Tuple[int, int]], n: int
    ) -> None:
        """将 Meek 规则无法确定的剩余无向边按拓扑序统一定向，保证结果无环。"""
        order = self._topological_order(arcs, n)
        rank = {node: idx for idx, node in enumerate(order)}
        for edge in sorted(undirected, key=lambda e: tuple(sorted(e))):
            a, b = tuple(sorted(edge))
            if rank[a] <= rank[b]:
                arcs.add((a, b))
            else:
                arcs.add((b, a))
        undirected.clear()

    @staticmethod
    def _edge_strength(data: np.ndarray, i: int, j: int):
        """由边际相关系数推导因果强度与置信度。"""
        corr = np.corrcoef(data[:, i], data[:, j])[0, 1]
        if np.isnan(corr):
            corr = 0.0
        magnitude = abs(float(corr))
        if magnitude >= 0.7:
            strength = CausalStrength.STRONG
        elif magnitude >= 0.4:
            strength = CausalStrength.MODERATE
        else:
            strength = CausalStrength.WEAK
        return strength, round(min(0.99, magnitude), 4)

    def _partial_correlation(
        self, data: np.ndarray, var1: int, var2: int, conditioning_set: Set[int]
    ):
        """计算 var1、var2 在给定条件集下的偏相关系数；无法计算时返回 None。"""
        idx = [var1, var2] + sorted(conditioning_set)
        sub = data[:, idx]
        with np.errstate(invalid="ignore", divide="ignore"):
            corr = np.corrcoef(sub, rowvar=False)
        if not np.all(np.isfinite(corr)):
            return None

        if not conditioning_set:
            return float(np.clip(corr[0, 1], -0.999999, 0.999999))

        try:
            inv = np.linalg.pinv(corr)
        except np.linalg.LinAlgError:
            return None
        denom = sqrt(abs(float(inv[0, 0]) * float(inv[1, 1])))
        if denom <= 0:
            return None
        pcorr = -float(inv[0, 1]) / denom
        return float(np.clip(pcorr, -0.999999, 0.999999))

    def _test_independence(
        self, data: np.ndarray, var1: int, var2: int, conditioning_set: Set[int]
    ) -> ConditionalIndependenceTest:
        """
        条件独立性检验：基于偏相关系数的 Fisher z 变换。

        - 条件集为空时退化为 Pearson 相关系数检验。
        - 统计量 ``sqrt(n - |S| - 3) * |z|`` 近似标准正态，双侧 p 值由 ``erfc`` 给出。
        - 样本量不足或偏相关不可计算时，回退为边际相关阈值判定。
        """
        n_samples = int(data.shape[0])
        partial = self._partial_correlation(data, var1, var2, conditioning_set)

        dof = n_samples - len(conditioning_set) - 3
        if partial is None or dof <= 0:
            with np.errstate(invalid="ignore"):
                corr = np.corrcoef(data[:, var1], data[:, var2])[0, 1]
            if not np.isfinite(corr):
                corr = 0.0
            p_value = 2 * (1 - abs(float(corr)))
            return ConditionalIndependenceTest(abs(float(corr)) < 0.3, float(p_value), float(corr))

        # Fisher z 变换
        z = 0.5 * log((1 + partial) / (1 - partial))
        statistic = sqrt(dof) * abs(z)
        p_value = float(erfc(statistic / sqrt(2)))
        independent = p_value > self.alpha
        return ConditionalIndependenceTest(independent, p_value, partial)


class GESAlgorithm:
    """
    Greedy Equivalence Search (GES) Algorithm

    A score-based algorithm that searches for the best DAG
    using a scoring function (e.g., BIC).
    """

    def __init__(self, scoring_metric: str = "bic"):
        """
        Initialize GES algorithm

        Args:
            scoring_metric: Scoring metric ("bic" or "aic")
        """
        self.scoring_metric = scoring_metric

    def discover(self, data: np.ndarray, variable_names: List[str]) -> CausalGraph:
        """
        Discover causal graph from data

        Args:
            data: Observational data (n_samples x n_variables)
            variable_names: List of variable names

        Returns:
            CausalGraph object
        """
        n_variables = data.shape[1]
        graph = CausalGraph("ges_discovery")

        # Simplified: Start with empty graph and greedily add edges
        best_score = float("-inf")
        best_graph = None

        # Greedy forward phase
        for _ in range(n_variables * 2):  # Limit iterations
            improved = False

            for i in range(n_variables):
                for j in range(n_variables):
                    if i != j:
                        # Try adding edge i -> j
                        test_graph = CausalGraph("test")
                        for var in variable_names:
                            test_graph.add_node(var)

                        edge = CausalEdge(
                            from_var=variable_names[i],
                            to_var=variable_names[j],
                            strength=CausalStrength.MODERATE,
                        )
                        test_graph.add_edge(edge)

                        score = self._score_graph(data, test_graph)

                        if score > best_score:
                            best_score = score
                            best_graph = test_graph
                            improved = True

            if not improved:
                break

        if best_graph is None:
            # Fallback: return empty graph
            for var in variable_names:
                graph.add_node(var)
        else:
            graph = best_graph

        logger.info(
            f"GES algorithm discovered graph with {len(graph.nodes)} nodes, {len(graph.edges)} edges"  # noqa: E501
        )

        return graph

    def _score_graph(self, data: np.ndarray, graph: CausalGraph) -> float:
        """
        Score graph using BIC/AIC

        Args:
            data: Data matrix
            graph: Causal graph

        Returns:
            Score value
        """
        # Simplified scoring: penalize complexity
        n_samples = data.shape[0]
        n_edges = len(graph.edges)
        n_params = n_edges * 2  # Simplified parameter count

        # Log-likelihood (simplified): independent Gaussian with empirical variances
        variances = np.var(data, axis=0)
        variances = np.where(variances > 0, variances, 1e-6)
        data.shape[1]
        log_likelihood = float(-0.5 * n_samples * np.sum(np.log(2 * np.pi * variances) + 1))

        score: float
        if self.scoring_metric == "bic":
            # BIC = log_likelihood - (k/2) * log(n)
            score = float(log_likelihood - (n_params / 2) * np.log(n_samples))
        else:
            # AIC = log_likelihood - k
            score = float(log_likelihood - n_params)

        return score
