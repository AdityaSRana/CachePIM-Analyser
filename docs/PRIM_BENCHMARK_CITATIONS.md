# PrIM Benchmark Suite: Citations and Integration Notes

Keep this document handy for referencing the PrIM benchmark suite in your research paper, methodology section, slides, and defense.

---

## 1. Primary Citations (BibTeX Format)

### Primary Journal Paper (Comprehensive Architecture & Workload Analysis)
```bibtex
@article{gomez2022benchmarking,
  title={{Benchmarking a New Paradigm: Experimental Analysis and Characterization of a Real Processing-in-Memory System}},
  author={G{\'o}mez-Luna, Juan and El Hajj, Izzat and Fernandez, Ivan and Giannoula, Christina and Oliveira, Geraldo F and Mutlu, Onur},
  journal={IEEE Access},
  volume={10},
  pages={52565--52598},
  year={2022},
  publisher={IEEE},
  doi={10.1109/ACCESS.2022.3174966}
}
```

### Conference Paper (Initial Workload Suitability & Takeaways)
```bibtex
@inproceedings{gomez2021benchmarking,
  title={{Benchmarking Memory-centric Computing Systems: Analysis of Real Processing-in-Memory Hardware}},
  author={G{\'o}mez-Luna, Juan and El Hajj, Izzat and Fernandez, Ivan and Giannoula, Christina and Oliveira, Geraldo F and Mutlu, Onur},
  booktitle={2021 12th International Green and Sustainable Computing Conference (IGSC)},
  pages={1--9},
  year={2021},
  organization={IEEE},
  doi={10.1109/IGSC54293.2021.9651614}
}
```

### arXiv Preprint Reference
```bibtex
@article{gomez2021prim,
  title={{Benchmarking a New Paradigm: An Experimental Analysis of a Real Processing-in-Memory Architecture}},
  author={G{\'o}mez-Luna, Juan and El Hajj, Izzat and Fernandez, Ivan and Giannoula, Christina and Oliveira, Geraldo F and Mutlu, Onur},
  journal={arXiv preprint arXiv:2105.03814},
  year={2021}
}
```

---

## 2. Key Metadata & Links

- **Benchmark Name:** PrIM (Processing-In-Memory Benchmarks)
- **Principal Investigators:** Prof. Onur Mutlu, Dr. Juan Gómez-Luna
- **Institution:** SAFARI Research Group (Carnegie Mellon University & ETH Zürich)
- **Target Hardware Architecture:** UPMEM DRAM Processing Units (DPU-based PIM)
- **Official Open-Source Repository:** [https://github.com/CMU-SAFARI/prim-benchmarks](https://github.com/CMU-SAFARI/prim-benchmarks)
- **arXiv Paper:** [https://arxiv.org/abs/2105.03814](https://arxiv.org/abs/2105.03814)

---

## 3. Workload Classification & CachePIM Mapping

| Benchmark | Domain | CachePIM Kernel | Locality / Access Pattern | Cache Hit Behavior | Offloading Decision |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`VA`** (Vector Addition) | Linear Algebra | `VECTOR_OP` | Sequential Streaming | Low reuse, high spatial hit rate | PIM favorable (bandwidth-bound) |
| **`RED`** (Reduction) | Primitives | `REDUCTION` | Streaming tree | Low reuse, minimal output write | PIM favorable |
| **`SEL`** (Select / Filter) | Databases | `FILTER` | Streaming Predicate | Selective writeback | PIM favorable |
| **`GEMV`** (Matrix-Vector) | Dense Linear Algebra | `VECTOR_OP` | High Temporal Reuse | High reuse on vector ($>85\%$ hit rate) | CPU cache competitive |
| **`HST`** (Histogram) | Analytics | `VECTOR_OP` | Hot-Set Reuse | High reuse on bin counters | CPU cache competitive |
| **`SpMV`** (Sparse MatVec) | Sparse Math | `VECTOR_OP` | Irregular / Indirect | Low reuse ($<25\%$ hit rate) | PIM favorable |
| **`BFS`** (Breadth-First Search) | Graph Traversal | `VECTOR_OP` | Pointer Chasing | Cache thrashing + severe bank skew | PIM favorable |

---

## 4. Suggested Text for Your Research Paper

### Section: Experimental Methodology & Workload Selection
> *"To evaluate offloading decisions across representative memory and compute access patterns, we adopt workload characteristics from the **PrIM benchmark suite** [G{\'o}mez-Luna et al., 2022], the first publicly accessible benchmark suite for real-world Processing-in-Memory architectures. We evaluate seven representative benchmarks spanning streaming primitives (`VA`, `RED`, `SEL`), high-reuse linear algebra (`GEMV`, `HST`), and irregular graph/sparse operations (`BFS`, `SpMV`).*
> 
> *To eliminate purely synthetic workload biases, memory access traces are captured directly from the native C/OpenMP CPU baselines of the PrIM suite using **Valgrind (Lackey)** dynamic binary instrumentation. The resulting 64-bit load and store address sequences are processed by CachePIM's exact LRU Last-Level Cache (LLC) simulation model and analytical PIM cost engine."*
