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

    better_rag = 0
    better_baseline = 0
    tie = 0

    for item in results:
        eval_data = item.get("evaluation", {})
        rag = eval_data.get("rag_score", 0)
        base = eval_data.get("baseline_score", 0)
        complexity = item.get("complexity", "unknown")

        rag_scores.append(rag)
        baseline_scores.append(base)
        complexity_dict[complexity].append((rag, base))

        if rag > base:
            better_rag += 1
        elif rag < base:
            better_baseline += 1
        else:
            tie += 1

    print("Общее количество вопросов:", len(results))
    print("RAG > baseline:", better_rag)
    print("RAG < baseline:", better_baseline)
    print("Tie:", tie)
    print("Средний RAG score:", np.mean(rag_scores))
    print("Средний baseline score:", np.mean(baseline_scores))
    print()

    for level, scores in complexity_dict.items():
        rag_avg = np.mean([r for r, b in scores])
        base_avg = np.mean([b for r, b in scores])
        print(f"Сложность {level}: средний RAG={rag_avg:.3f}, baseline={base_avg:.3f}")

    return rag_scores, baseline_scores, complexity_dict

def plot_histograms(rag_scores, baseline_scores, complexity_dict, out_dir):

    os.makedirs(out_dir, exist_ok=True)

    plt.figure(figsize=(12,5))
    plt.hist([rag_scores, baseline_scores], bins=20, label=["RAG", "Baseline"], alpha=0.7)
    plt.xlabel("Score")
    plt.ylabel("Number of questions")
    plt.title("Распределение оценок по всем вопросам")
    plt.legend()
    plt.savefig(os.path.join(out_dir, "hist_scores_all.png"))
    plt.close()

    for level, scores in complexity_dict.items():
        rag = [r for r, b in scores]
        base = [b for r, b in scores]
        plt.figure(figsize=(8,4))
        plt.hist([rag, base], bins=20, label=["RAG", "Baseline"], alpha=0.7)
        plt.xlabel("Score")
        plt.ylabel("Number of questions")
        plt.title(f"Распределение оценок по сложности: {level}")
        plt.legend()
        plt.savefig(os.path.join(out_dir, f"hist_scores_{level}.png"))
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
    rag_scores, baseline_scores, complexity_dict = analyze_scores(results)

    base_name = os.path.splitext(os.path.basename(file_path))[0]
    out_dir = os.path.join(os.path.dirname(file_path), base_name)
    plot_histograms(rag_scores, baseline_scores, complexity_dict, out_dir)

if __name__ == "__main__":
    main()
