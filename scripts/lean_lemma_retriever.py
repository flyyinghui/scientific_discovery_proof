#!/usr/bin/env python3
"""
lean_lemma_retriever.py — EmbeddingGemma-2 Lean 引理检索器

接入 scientific-discovery-proof 技能 Stage 3 引理召回 (v2.22.0+)。

用途: 给定 Lean 定理名(或自由文本), 召回其依赖 DAG 中可能引用的候选引理/定义。
基座: google/embeddinggemma-2-740m, 在 openai_math Lean 依赖对(377K)上全参微调。
recall@10 = 0.5505 (增强文本口径: 名字词化 + 类型签名120 + docstring60)。

运行依赖(独立 venv, 勿用 Hermes 主 venv):
    ~/models/EmbeddingGemma2_Lean检索模型_v2/venv/bin/python
    torch 2.5.1+cu121 / transformers 5.19.0 / sentence-transformers 6.1.0

用法:
    # 建索引(首次, 编码 18 万声明)
    python lean_lemma_retriever.py --build-index
    # 召回
    python lean_lemma_retriever.py --query resolutionCokernelMap --top-k 10
    # 自由文本召回
    python lean_lemma_retriever.py --text "spectral gap of Laplacian" --top-k 10
"""
import re, json, os, sys, argparse

MODEL_DIR = "~/models/EmbeddingGemma2_Lean检索模型_v2/embeddinggemma-2-lean"
DECLS_PATH = "~/models/EmbeddingGemma2_Lean检索模型_v2/declarations.jsonl"
INDEX_DIR = "~/models/EmbeddingGemma2_Lean检索模型_v2/index"


# ---------------------------------------------------------------- 文本口径

def name_to_text(name: str) -> str:
    """Lean 标识符 → 可读文本 (与训练口径一致)"""
    s = re.sub(r'_+', ' ', name)
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', s)
    return s.strip()


def enrich(name: str, decls: dict, sig_chars: int = 120, doc_chars: int = 60) -> str:
    """增强文本: 名字词化 | 类型签名 | docstring (与训练口径严格一致)"""
    parts = [name_to_text(name)]
    d = decls.get(name)
    if d:
        if d.get("signature"):
            parts.append("type " + d["signature"][:sig_chars])
        if d.get("docstring"):
            parts.append(d["docstring"][:doc_chars])
    return " | ".join(parts)


def load_decls(path: str = DECLS_PATH) -> dict:
    decls = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            decls[d["name"]] = d
    return decls


# ---------------------------------------------------------------- 模型与检索

class LemmaRetriever:
    """把 Lean 声明库编码为索引, 供 Stage 3 召回候选引理"""

    def __init__(self, model, names, decls, normalize: bool = True):
        self.model = model
        self.names = list(names)
        self.decls = decls
        self.normalize = normalize
        self.emb = None

    def build_index(self, batch_size: int = 64, cache_dir: str = INDEX_DIR):
        import numpy as np
        txts = [enrich(n, self.decls) for n in self.names]
        # 分批编码到 CPU（P620 4GB 显存下 18 万声明全量编码会 OOM，须逐批累积）
        n = len(txts)
        emb_batches = []
        for i in range(0, n, batch_size):
            chunk = txts[i:i + batch_size]
            e = self.model.encode(
                chunk, normalize_embeddings=self.normalize,
                batch_size=batch_size, convert_to_numpy=True, show_progress_bar=False,
            )
            emb_batches.append(e)
            if (i // batch_size) % 500 == 0 and i > 0:
                print(f"    [index] 已编码 {i}/{n}", flush=True)
        emb = np.vstack(emb_batches)
        self.emb = __import__("torch").from_numpy(emb)
        # 缓存
        os.makedirs(cache_dir, exist_ok=True)
        np.save(os.path.join(cache_dir, "emb.npy"), emb)
        with open(os.path.join(cache_dir, "names.json"), "w", encoding="utf-8") as f:
            json.dump(self.names, f)
        return self.emb

    def load_index(self, cache_dir: str = INDEX_DIR):
        import numpy as np
        import torch
        emb = np.load(os.path.join(cache_dir, "emb.npy"))
        with open(os.path.join(cache_dir, "names.json"), encoding="utf-8") as f:
            self.names = json.load(f)
        self.emb = torch.from_numpy(emb)
        return self.emb

    def _encode_query(self, text: str):
        return self.model.encode(
            [text], normalize_embeddings=self.normalize, convert_to_tensor=True
        )

    def recall(self, theorem_name: str, top_k: int = 10):
        """给定定理名, 召回候选依赖 (用增强文本口径)"""
        q = self._encode_query(enrich(theorem_name, self.decls))
        return self._topk(q, top_k)

    def recall_by_text(self, query_text: str, top_k: int = 10):
        """自由文本召回"""
        q = self._encode_query(query_text)
        return self._topk(q, top_k)

    def _topk(self, q, top_k: int):
        import torch
        # 统一到 CPU 做矩阵乘法（18万×768 的 matmul CPU 上仅数百毫秒）
        q_cpu = q.cpu() if hasattr(q, "is_cuda") and q.is_cuda else q
        emb = self.emb.cpu() if hasattr(self.emb, "is_cuda") and self.emb.is_cuda else self.emb
        sim = (q_cpu @ emb.T)[0]
        k = min(top_k, len(self.names))
        idx = torch.topk(sim, k=k).indices.tolist()
        return [(self.names[i], float(sim[i])) for i in idx]


def load_model(device: str = "cpu", dtype: str = "float32"):
    """加载模型. P620(Pascal) 不支持 bf16, 默认 float32."""
    from sentence_transformers import SentenceTransformer
    kwargs = {}
    if dtype == "float32":
        import torch
        kwargs["torch_dtype"] = torch.float32
    model = SentenceTransformer(MODEL_DIR, device=device, model_kwargs=kwargs)
    model.max_seq_length = 64
    return model


# ---------------------------------------------------------------- CLI

def main():
    global MODEL_DIR, DECLS_PATH
    ap = argparse.ArgumentParser(description="EmbeddingGemma-2 Lean 引理检索器")
    ap.add_argument("--model-dir", default=MODEL_DIR)
    ap.add_argument("--decls", default=DECLS_PATH)
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    ap.add_argument("--dtype", default="float32", choices=["float32", "bfloat16"])
    ap.add_argument("--build-index", action="store_true", help="编码声明库并缓存")
    ap.add_argument("--query", type=str, help="定理名召回")
    ap.add_argument("--text", type=str, help="自由文本召回")
    ap.add_argument("--top-k", type=int, default=10)
    args = ap.parse_args()

    MODEL_DIR = args.model_dir
    DECLS_PATH = args.decls

    print(f"[load] 加载模型 {MODEL_DIR} (device={args.device}, dtype={args.dtype})", flush=True)
    model = load_model(args.device, args.dtype)
    print("[load] 模型加载完成", flush=True)

    print(f"[load] 加载声明库 {DECLS_PATH}", flush=True)
    decls = load_decls(args.decls)
    names = list(decls.keys())
    print(f"[load] 声明库 {len(names)} 条", flush=True)

    retriever = LemmaRetriever(model, names, decls)

    if args.build_index:
        print("[index] 编码声明库...", flush=True)
        retriever.build_index()
        print(f"[index] 完成, 缓存到 {INDEX_DIR}", flush=True)
        return

    # 尝试加载缓存索引
    import os as _os
    emb_path = _os.path.join(INDEX_DIR, "emb.npy")
    if _os.path.exists(emb_path):
        print("[index] 加载缓存索引...", flush=True)
        retriever.load_index()
    else:
        print("[index] 无缓存, 编码声明库 (约 2 分钟 GPU / 30+ 分钟 CPU)...", flush=True)
        retriever.build_index()

    if args.query:
        print(f"[recall] 定理名: {args.query}", flush=True)
        for name, score in retriever.recall(args.query, args.top_k):
            d = decls.get(name, {})
            kind = d.get("kind", "?")
            print(f"  {score:.4f}  [{kind}] {name}")
    elif args.text:
        print(f"[recall] 文本: {args.text}", flush=True)
        for name, score in retriever.recall_by_text(args.text, args.top_k):
            d = decls.get(name, {})
            kind = d.get("kind", "?")
            print(f"  {score:.4f}  [{kind}] {name}")
    else:
        print("用法: 指定 --query 或 --text")


if __name__ == "__main__":
    main()
