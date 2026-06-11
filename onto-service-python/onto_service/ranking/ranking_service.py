"""
Learning-to-Rank Service
LambdaMART 学习排序服务
"""

import json
import os
import pickle
from typing import List, Dict, Any, Optional

import numpy as np


class RankingService:
    """
    学习排序服务
    
    核心能力:
    1. LambdaMART 模型训练（基于 LightGBM）
    2. 特征工程：keyword_score, vector_score, structure_score, popularity, recency
    3. 模型持久化与加载
    4. 在线预测排序
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or os.getenv("LTR_MODEL_PATH", "./models/ltr_model.pkl")
        self.model = None
        self.feature_names = [
            "keyword_score",      # 关键词匹配分数
            "vector_score",       # 向量相似度分数
            "structure_score",    # 结构匹配分数
            "type_match_score",   # 类型匹配分数
            "exact_match_score",  # 精确匹配分数
            "popularity",         # 实体流行度（点击次数）
            "recency",            # 最近更新时间
            "path_depth",         # 路径深度
        ]
        self._load_model()

    def _load_model(self):
        """加载已训练的模型"""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, "rb") as f:
                    self.model = pickle.load(f)
                print(f"Loaded LTR model from {self.model_path}")
            except Exception as e:
                print(f"Failed to load model: {e}")
                self.model = None

    def _save_model(self):
        """保存模型到磁盘"""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        with open(self.model_path, "wb") as f:
            pickle.dump(self.model, f)
        print(f"Saved LTR model to {self.model_path}")

    def _extract_features(self, candidate: Dict[str, Any]) -> np.ndarray:
        """从候选文档提取特征向量"""
        features = []
        for name in self.feature_names:
            value = candidate.get(name, 0.0)
            if value is None:
                value = 0.0
            features.append(float(value))
        return np.array(features)

    def train(self, training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        训练 LambdaMART 模型
        
        Args:
            training_data: 训练样本列表，每个样本包含:
                {
                    "query_id": "q1",
                    "candidate": {"keyword_score": 0.8, "vector_score": 0.9, ...},
                    "label": 1  # 1=点击, 0=未点击
                }
        
        Returns:
            {"status": "success", "model_info": {...}}
        """
        try:
            import lightgbm as lgb
        except ImportError:
            return self._train_fallback(training_data)

        if len(training_data) < 10:
            return {"status": "insufficient_data", "message": f"Need at least 10 samples, got {len(training_data)}"}

        # 准备训练数据
        X = []
        y = []
        group = []
        
        current_query = None
        current_group_size = 0
        
        for sample in sorted(training_data, key=lambda x: x["query_id"]):
            features = self._extract_features(sample["candidate"])
            X.append(features)
            y.append(sample.get("label", 0))
            
            if sample["query_id"] != current_query:
                if current_group_size > 0:
                    group.append(current_group_size)
                current_query = sample["query_id"]
                current_group_size = 1
            else:
                current_group_size += 1
        
        if current_group_size > 0:
            group.append(current_group_size)

        X = np.array(X)
        y = np.array(y)

        # 训练 LambdaMART
        train_data = lgb.Dataset(X, label=y, group=group)
        
        params = {
            "objective": "lambdarank",
            "metric": "ndcg",
            "ndcg_eval_at": [5, 10],
            "learning_rate": 0.05,
            "num_leaves": 31,
            "min_data_in_leaf": 20,
            "feature_fraction": 0.8,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "verbose": -1
        }
        
        self.model = lgb.train(
            params,
            train_data,
            num_boost_round=100,
            valid_sets=[train_data],
            callbacks=[lgb.early_stopping(stopping_rounds=10), lgb.log_evaluation(period=0)]
        )
        
        self._save_model()
        
        # 特征重要性
        importance = dict(zip(self.feature_names, self.model.feature_importance().tolist()))
        
        return {
            "status": "success",
            "model_info": {
                "num_features": len(self.feature_names),
                "num_samples": len(training_data),
                "num_queries": len(group),
                "feature_importance": importance,
                "best_iteration": self.model.best_iteration
            }
        }

    def _train_fallback(self, training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """LightGBM 不可用时使用简单线性模型"""
        print("LightGBM not available, using fallback linear model")
        
        # 简单启发式：基于 CTR 调整权重
        from collections import defaultdict
        
        feature_sums = defaultdict(float)
        feature_counts = defaultdict(int)
        
        for sample in training_data:
            label = sample.get("label", 0)
            candidate = sample.get("candidate", {})
            for name in self.feature_names:
                value = candidate.get(name, 0.0) or 0.0
                if label == 1:
                    feature_sums[name] += value
                    feature_counts[name] += 1
        
        weights = {}
        for name in self.feature_names:
            avg = feature_sums[name] / max(feature_counts[name], 1)
            weights[name] = avg
        
        # 归一化
        total = sum(weights.values()) or 1.0
        weights = {k: v / total for k, v in weights.items()}
        
        self.model = {"type": "fallback_linear", "weights": weights}
        self._save_model()
        
        return {
            "status": "success_fallback",
            "model_info": {
                "type": "fallback_linear",
                "weights": weights,
                "num_samples": len(training_data)
            }
        }

    def predict(self, candidates: List[Dict[str, Any]]) -> List[float]:
        """
        预测候选文档的排序分数
        
        Args:
            candidates: 候选文档列表，每个包含特征字段
            
        Returns:
            排序分数列表（与 candidates 一一对应）
        """
        if self.model is None:
            # 无模型时使用默认加权
            return self._default_score(candidates)
        
        if isinstance(self.model, dict) and self.model.get("type") == "fallback_linear":
            return self._fallback_predict(candidates)
        
        # LightGBM 预测
        X = np.array([self._extract_features(c) for c in candidates])
        scores = self.model.predict(X)
        return scores.tolist()

    def _default_score(self, candidates: List[Dict[str, Any]]) -> List[float]:
        """默认加权打分"""
        default_weights = {
            "exact_match_score": 0.3,
            "keyword_score": 0.2,
            "vector_score": 0.2,
            "structure_score": 0.2,
            "type_match_score": 0.1
        }
        scores = []
        for c in candidates:
            score = sum(c.get(k, 0.0) * w for k, w in default_weights.items())
            scores.append(score)
        return scores

    def _fallback_predict(self, candidates: List[Dict[str, Any]]) -> List[float]:
        """Fallback 线性模型预测"""
        weights = self.model["weights"]
        scores = []
        for c in candidates:
            score = sum(c.get(name, 0.0) * weights.get(name, 0.0) for name in self.feature_names)
            scores.append(score)
        return scores

    def get_model_info(self) -> Dict[str, Any]:
        """获取当前模型信息"""
        if self.model is None:
            return {"status": "no_model", "message": "No trained model available"}
        
        if isinstance(self.model, dict):
            return {"status": "fallback", "weights": self.model.get("weights", {})}
        
        return {
            "status": "trained",
            "feature_names": self.feature_names,
            "best_iteration": getattr(self.model, "best_iteration", 0)
        }
