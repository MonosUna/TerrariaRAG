import os
import sys
import json
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

def load_results(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def analyze_scores(results):
    rag_scores = []
    baseline_scores = []
    complexity_dict = defaultdict(list)

    for item in results:
        eval_data = item.get("evaluation", {})
        rag = eval_data.get("rag_score", 0)
        base = eval_data.get("baseline_score", 0)
        complexity = item.get("complexity", "unknown")

        rag_scores.append(rag)
        baseline_scores.append(base)
        complexity_dict[complexity].append((rag, base))

    # Подсчёт количеств
    counts = {
        "all": len(results),
        "easy": len(complexity_dict.get("easy", [])),
        "medium": len(complexity_dict.get("medium", [])),
        "hard": len(complexity_dict.get("hard", [])),
    }

    # Средние значения
    stats = {"all": (
        np.mean(rag_scores) if rag_scores else 0,
        np.mean(baseline_scores) if baseline_scores else 0
    )}

    for level in ["easy", "medium", "hard"]:
        pairs = complexity_dict.get(level, [])
        if pairs:
            rag = [r for r, _ in pairs]
            base = [b for _, b in pairs]
            stats[level] = (np.mean(rag), np.mean(base))
        else:
            stats[level] = (0, 0)

    return stats, counts

def plot_grouped_bars(stats, counts, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    categories = ["all", "easy", "medium", "hard"]
    rag_means = [stats[c][0] for c in categories]
    base_means = [stats[c][1] for c in categories]

    x = np.arange(len(categories))
    width = 0.35

    plt.figure(figsize=(12, 6))
    plt.bar(x - width/2, rag_means, width, label="RAG")
    plt.bar(x + width/2, base_means, width, label="Baseline")

    plt.xticks(x, [f"{cat}\n(n={counts[cat]})" for cat in categories])
    plt.ylabel("Average Score")
    plt.title("Средние значения RAG vs Baseline по уровням сложности")
    plt.legend()

    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "grouped_barchart.png"))
    plt.close()

def main():
    if len(sys.argv) < 2:
        print("Использование: python3 metrics/vis_metrics.py <path_to_results.json>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"Файл не найден: {file_path}")
        sys.exit(1)

    results = load_results(file_path)

    stats, counts = analyze_scores(results)

    base_name = os.path.splitext(os.path.basename(file_path))[0]
    out_dir = os.path.join(os.path.dirname(file_path), base_name)

    plot_grouped_bars(stats, counts, out_dir)

    print("График сохранён в:", out_dir)
    print("\nКоличество вопросов по уровню сложности:")
    for k, v in counts.items():
        print(f"{k}: {v}")

if __name__ == "__main__":
    main()
